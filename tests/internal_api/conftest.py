# conftest.py -- internal /v-apiserver suite.
#
# Every fixture that needs internal credentials (QA_USER/QA_PASSWORD or a
# BOX account) lives here, not in the root conftest, so other suites never
# see it and a broken internal import cannot stop their collection.
import html
import logging
import os

import pytest

import api_clients.auth_helper as auth_helper_mod
import api_clients.base_api_client as base_client_mod
import api_clients.bookmark_api as bookmark_mod
import api_clients.camera_api as camera_mod
import api_clients.dashboard_api as dashboard_mod
import api_clients.discovery_helper as discovery_mod
import api_clients.location_api as location_mod
import api_clients.search_api as search_mod
import api_clients.user_api as user_mod
from api_clients import site_helper
from config.base_config import (
    config as _config,  # noqa: F401 (resolves ENV early, with a clear error)
)
from config.base_config import is_delete_allowed, is_write_allowed

_log = logging.getLogger("env_config")


@pytest.fixture(scope="session")
def login_data():
    """Active account credentials.

    Two sources, checked in this order:
    1. If the BOX env var is set, use that box's account from config/env/
       (for example BOX=india on ENV=qa). The box names the password variable
       to read from .env.
    2. Otherwise read QA_USER and QA_PASSWORD from .env. This is the default.
    """
    box = os.environ.get("BOX")
    if box:
        from config.base_config import get_credentials
        creds = get_credentials()
        if not creds.get("email") or not creds.get("password"):
            raise ValueError(
                f"BOX='{box}' is set but its credentials are incomplete. The "
                f"box's password variable is empty or missing in .env. See the "
                f"password_env key for this box in config/env/.")
        _log.info(f"[CREDENTIALS] Using box '{box}' account from env config")
        return {"username": creds["email"], "password": creds["password"]}

    user = os.environ.get("QA_USER")
    password = os.environ.get("QA_PASSWORD")
    if not user or not password:
        raise ValueError(
            "QA_USER and QA_PASSWORD must be set in environment or .env file. "
            "See .env.template")
    _log.info("[CREDENTIALS] Using QA_USER from environment")
    return {"username": user, "password": password}


@pytest.fixture(scope="session")
def api_base_url(env_config):
    # Prefer explicit api_base_url (includes /v-apiserver) if provided by env config
    return env_config.get('api_base_url', env_config.get('base_url'))


@pytest.fixture(scope="session")
def api_auth_helper(api_base_url):
    """Provide a single `AuthHelper` instance for the entire test session."""
    return auth_helper_mod.AuthHelper(api_base_url)


@pytest.fixture(scope="session")
def api_auth_token(api_auth_helper, login_data):
    """Session-scoped JSESSIONID.

    Deliberately does not catch failures: AuthHelper raises with a message
    saying whether the account, the password, or the host is wrong.
    """
    return api_auth_helper.login(login_data['username'], login_data['password'])


@pytest.fixture(scope="session")
def dashboard_api(api_base_url, api_auth_token):
    return dashboard_mod.DashboardAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def camera_api(api_base_url, api_auth_token):
    return camera_mod.CameraAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def user_api(api_base_url, api_auth_token):
    return user_mod.UserAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def search_api(api_base_url, api_auth_token):
    return search_mod.SearchAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def enterprise_helper(api_base_url, api_auth_token):
    """Session-scoped EnterpriseHelper for dynamic enterpriseId lookup."""
    from api_clients.enterprise_helper import EnterpriseHelper
    return EnterpriseHelper(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def site_discovery(api_base_url, api_auth_token):
    """Session-scoped SiteDiscovery for auto-discovering user sites."""
    from api_clients.site_discovery import SiteDiscovery
    return SiteDiscovery(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def discovered_site(site_discovery, login_data):
    """Auto-discovered default site for the logged-in user."""
    user_email = login_data.get("username")
    site = site_discovery.get_default_site(user_email)
    if not site:
        pytest.skip(f"No sites found for user {user_email}")
    return site


@pytest.fixture(scope="session")
def discovered_site_id(discovered_site):
    """Auto-discovered site ID."""
    return discovered_site.get("siteId")


@pytest.fixture(scope="session")
def discovered_enterprise_id(discovered_site):
    """Auto-discovered enterprise ID from the user's default site."""
    return discovered_site.get("enterpriseId")


@pytest.fixture(scope="session")
def test_enterprise_id(enterprise_helper, test_site_id):
    """Dynamically fetched enterpriseId for the test site."""
    return enterprise_helper.get_enterprise_id(test_site_id)


@pytest.fixture(scope="session")
def test_site_id(user_api, camera_api, login_data):
    """Discover a site id the logged-in user can access.

    Order: TEST_SITE_ID env var -> assigned sites via the API -> probe a small
    range of site ids and accept the first that answers.
    """
    explicit = os.environ.get("TEST_SITE_ID")
    if explicit:
        return int(explicit)

    sites = site_helper.get_available_sites(user_api)
    if sites:
        first = sites[0]
        for k in ("siteId", "site_id", "id"):
            if isinstance(first, dict) and k in first:
                return first.get(k)

    for candidate in range(1, 51):
        try:
            tree = camera_api.get_camera_tree(candidate)
            if tree:
                return candidate
        except Exception:
            continue
    raise RuntimeError("Unable to discover a test site id for the current user")


@pytest.fixture(scope="session")
def discovery_helper(api_base_url, api_auth_token):
    """Session-scoped DiscoveryHelper wrapping a simple BaseAPI client."""
    from api_clients.base_api_client import BaseAPIClient
    client = BaseAPIClient(api_base_url, api_auth_token)
    return discovery_mod.DiscoveryHelper(client)


@pytest.fixture(scope="session")
def test_channel_ids(discovery_helper, test_site_id):
    """Channel ids for the selected test site, preferring snapshot-capable ones."""
    try:
        snapshot_ids = discovery_helper.get_snapshot_capable_channels(test_site_id)
    except Exception:
        snapshot_ids = []
    if snapshot_ids:
        return sorted(snapshot_ids)

    try:
        ids = discovery_helper.get_site_channels(test_site_id)
    except Exception:
        ids = []
    if ids:
        return sorted(ids)

    return [1]


# --------------------------------------------------------------------------
# Test data fixtures. Tests that write data (locations, bookmarks) resolve
# their site by NAME, never by TEST_SITE_ID. A number is easy to get wrong:
# on QA, TEST_SITE_ID=17 is "Example Corporate Office" while the UI
# suite works on "Newtown Action Area" (siteId 16). See docs/API_SURFACES.md,
# "Test data".
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def location_api(api_base_url, api_auth_token):
    return location_mod.LocationAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def bookmark_api(api_base_url, api_auth_token):
    return bookmark_mod.BookmarkAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def data_site(site_discovery, login_data, env_config):
    """The site that test_site_name in config/env/ names, resolved by name.

    Skips when the config has no name or the account has no site by that
    name. The skip message lists the sites the account can see.
    """
    name = env_config.get("test_site_name")
    if not name:
        pytest.skip(
            f"test_site_name is not set in config/env/ for ENV={os.environ.get('ENV', 'qa')}")
    email = login_data["username"]
    site = site_discovery.get_site_by_name(email, name)
    if not site:
        names = [s.get("name") for s in site_discovery.get_user_sites(email)]
        pytest.skip(
            f"No site named '{name}' for {email}. Sites: {names}. "
            f"Fix test_site_name in config/env/.")
    return site


@pytest.fixture(scope="session")
def data_site_id(data_site):
    return int(data_site["siteId"])


@pytest.fixture(scope="session")
def data_channel_id(location_api, data_site_id, env_config):
    """Channel id of test_camera_name on the data site, read from location/tree.

    Raises LookupError with the camera names seen when the tenant renamed
    the camera. The fix is test_camera_name in config/env/.
    """
    camera = env_config.get("test_camera_name")
    if not camera:
        pytest.skip(
            f"test_camera_name is not set in config/env/ for ENV={os.environ.get('ENV', 'qa')}")
    return location_api.channel_id_by_name(location_api.get_location_tree(data_site_id), camera)


@pytest.fixture(scope="session")
def data_write_gate(env_config):
    """Skip unless the env allows writes AND deletes (config/env/ allow_write, allow_delete).

    A test that creates data must also remove it, so both flags are
    needed. QA allows both, stage allows no deletes, prod allows neither.
    """
    write, delete = is_write_allowed(), is_delete_allowed()
    if not (write and delete):
        pytest.skip(
            f"ENV={os.environ.get('ENV', 'qa')} has allow_write={write} "
            f"allow_delete={delete}. Tests that create data need both. See config/env/.")


# --------------------------------------------------------------------------
# HTTP exchanges in the failure report. BaseAPIClient logs every call it
# makes (api_clients/base_api_client.py). When a test fails in its call
# phase, the calls made since the test's setup started go into the report as
# an "HTTP exchanges" block and into the terminal output as a section.
# Calls made with `requests` directly are not logged.
# --------------------------------------------------------------------------

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Clear the exchange log so a failure shows only this test's calls."""
    base_client_mod.clear_exchanges()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    exchanges = base_client_mod.recent_exchanges()
    if not exchanges:
        return
    text = base_client_mod.format_exchanges(exchanges)
    report.sections.append(("HTTP exchanges", text))
    try:
        from pytest_html import extras
    except ImportError:
        return
    block = (
        "<details open><summary>HTTP exchanges</summary>"
        f"<pre>{html.escape(text)}</pre></details>"
    )
    report.extras = getattr(report, "extras", []) + [extras.html(block)]
