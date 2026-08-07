# conftest.py -- Soterix-API-QA
#
# API-only fixtures. There is deliberately no Playwright anywhere in this repo:
# authentication is plain HTTP (see docs/API_SURFACES.md for the contract), so
# a full run needs no browser, no captcha, and no UI login.
import logging
import os

import pytest

from config.base_config import config  # dict resolved from ENV

import api_clients.auth_helper as auth_helper_mod
import api_clients.camera_api as camera_mod
import api_clients.dashboard_api as dashboard_mod
import api_clients.discovery_helper as discovery_mod
import api_clients.search_api as search_mod
import api_clients.site_helper as site_helper
import api_clients.user_api as user_mod

# QA Touch result reporting. Dormant unless armed with
# --qatouch-upload --qatouch-run <RUN_KEY> (or QATOUCH_UPLOAD/QATOUCH_RUN_KEY).
pytest_plugins = ['plugins.qatouch_reporter']

LOG_FILE = os.path.join("logs", "env_config.log")
os.makedirs("logs", exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")


@pytest.fixture(scope="session")
def env_config():
    """Resolved environment configuration dict (from ENV)."""
    logging.info(f"[ENV CONFIG] Loaded config for: {os.environ.get('ENV')}")
    return config


@pytest.fixture(scope="session")
def base_url(env_config):
    """Site root from the active env config."""
    return env_config.get("base_url", "")


@pytest.fixture(scope="session")
def login_data():
    """Active account credentials from QA_USER / QA_PASSWORD (see .env.template)."""
    user = os.environ.get("QA_USER")
    password = os.environ.get("QA_PASSWORD")
    if not user or not password:
        raise ValueError(
            "QA_USER and QA_PASSWORD must be set in environment or .env file. "
            "See .env.template")
    logging.info("[CREDENTIALS] Using QA_USER from environment")
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
