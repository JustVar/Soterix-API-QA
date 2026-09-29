# conftest.py -- internal /v-apiserver suite.
#
# Every fixture that needs internal credentials (QA_USER/QA_PASSWORD) lives
# here, not in the root conftest, so other suites never see it and a broken
# internal import cannot stop their collection.
import html
import logging
import os

import pytest
import requests

import api_clients.auth_helper as auth_helper_mod
import api_clients.base_api_client as base_client_mod
import api_clients.bookmark_api as bookmark_mod
import api_clients.camera_api as camera_mod
import api_clients.dashboard_api as dashboard_mod
import api_clients.discovery_helper as discovery_mod
import api_clients.location_api as location_mod
import api_clients.search_api as search_mod
import api_clients.user_api as user_mod
from api_clients import data_choice, site_helper
from api_clients.tls import ssl_verify
from config.base_config import (
    config as _config,  # noqa: F401 (resolves ENV early, with a clear error)
)
from config.base_config import get_credentials, is_delete_allowed, is_write_allowed

_log = logging.getLogger("env_config")


@pytest.fixture(scope="session")
def login_data():
    """The account the suite signs in as: QA_USER and QA_PASSWORD from .env."""
    creds = get_credentials()
    if not creds["email"] or not creds["password"]:
        raise ValueError(
            "QA_USER and QA_PASSWORD must be set in environment or .env file. "
            "See .env.template")
    _log.info("[CREDENTIALS] Using QA_USER from environment")
    return {"username": creds["email"], "password": creds["password"]}


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
        except Exception:  # noqa: BLE001, S112 - site probe; a failed candidate id is skipped
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
    except Exception:  # noqa: BLE001 - discovery is best effort; fall back to all channels
        snapshot_ids = []
    if snapshot_ids:
        return sorted(snapshot_ids)

    try:
        ids = discovery_helper.get_site_channels(test_site_id)
    except Exception:  # noqa: BLE001 - discovery is best effort; fall back to channel 1
        ids = []
    if ids:
        return sorted(ids)

    return [1]


# --------------------------------------------------------------------------
# Test data fixtures. Tests that write data (locations, bookmarks) resolve
# their site by NAME (test_site_name in config/env/), never by TEST_SITE_ID.
# A number is easy to get wrong: two sites with similar names once carried
# the wrong id in both repos. A blank name means the first site by name
# with a camera, and the first camera by name on it, sorted by name and
# never by the server's order (api_clients/data_choice.py). See
# docs/API_SURFACES.md, "Test data".
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def location_api(api_base_url, api_auth_token):
    return location_mod.LocationAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def bookmark_api(api_base_url, api_auth_token):
    return bookmark_mod.BookmarkAPI(api_base_url, api_auth_token)


@pytest.fixture(scope="session")
def data_site(site_discovery, location_api, login_data, env_config):
    """The site the writing tests use, as /REST/site/user/{email} lists it.

    test_site_name in config/env/ names it. Blank: the first site by name
    whose status is REGISTERED and whose location tree has a camera. A
    configured name is checked, never replaced. The skip lists the sites
    the account sees, so the fix is one edit. The print line says which
    site the run used.
    """
    email = login_data["username"]
    configured = (env_config.get("test_site_name") or "").strip()

    def cameras_of(site_id):
        # A site whose backend is down answers 4xx or 5xx on location/tree.
        # It is not a candidate, and the print line says so.
        try:
            return data_choice.cameras_by_name(location_api.get_location_tree(site_id))
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", "?")
            print(f"[DATA SITE] site {site_id} is not a candidate: location/tree answered {status}")
            return []

    try:
        site = data_choice.choose_site(site_discovery.get_user_sites(email), cameras_of, configured)
    except LookupError as exc:
        pytest.skip(f"{exc} (account {email}, ENV={os.environ.get('ENV', 'qa')})")
    how = ("test_site_name in config/env/" if configured
           else "the first site by name with a camera, test_site_name is blank in config/env/")
    print(f"[DATA SITE] '{site['name']}' (siteId {site['siteId']}): {how}")
    return site


@pytest.fixture(scope="session")
def data_site_id(data_site):
    return int(data_site["siteId"])


@pytest.fixture(scope="session")
def data_channel_id(location_api, data_site, env_config):
    """Channel id of the camera the writing tests use, read from location/tree.

    test_camera_name in config/env/ names it. Blank: the first camera by
    name on the data site. A configured name is checked, never replaced.
    The skip lists the cameras the site has, so a rename by the shared
    tenant is one edit. The print line says which camera the run used.
    """
    configured = (env_config.get("test_camera_name") or "").strip()
    cameras = data_choice.cameras_by_name(location_api.get_location_tree(int(data_site["siteId"])))
    try:
        camera = data_choice.choose_camera(cameras, data_site["name"], configured)
    except LookupError as exc:
        pytest.skip(str(exc))
    how = ("test_camera_name in config/env/" if configured
           else "the first camera by name, test_camera_name is blank in config/env/")
    print(f"[DATA CAMERA] '{camera['name']}' (channel {camera['id']}) on '{data_site['name']}': {how}")
    return camera["id"]


@pytest.fixture(scope="session")
def data_write_gate(env_config):
    """Skip unless the env allows writes AND deletes (config/env/ allow_write, allow_delete).

    A test that creates data must also remove it, so both flags are
    needed. Set both False in config/env/ for a server that must stay
    untouched.
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


# --------------------------------------------------------------------------
# Flow-test fixtures (ported from PR #1). The endpoint sweep and the e2e
# flows expect a plain authed requests.Session, a discovery context of real
# ids, and a real recorded-clip window. All three are built from the shared
# session token and discovery fixtures above, so no second login or config
# layer is needed.
# --------------------------------------------------------------------------

@pytest.fixture(scope="session")
def authed_session(api_auth_token):
    """A requests.Session carrying the JSESSIONID for direct calls.

    The endpoint sweep and e2e tests call the API directly rather than
    through a client wrapper, so they need the raw session. BaseAPIClient
    calls are the ones auto-captured into the failure report; direct calls
    here are surfaced through the tests' own extras blocks instead.
    """
    s = requests.Session()
    s.headers["Cookie"] = f"JSESSIONID={api_auth_token}"
    s.verify = ssl_verify()
    return s


@pytest.fixture(scope="session")
def discovery_context(authed_session, api_base_url, test_site_id,
                      test_enterprise_id, test_channel_ids):
    """Real ids for the sweep's path templates, from the shared fixtures.

    siteid comes from test_site_id, the SAME fixture test_channel_ids reads,
    not from the login's default site. Two sources once disagreed on a live
    run: the default site's backend answered 502 on every endpoint while the
    channels came from another site, so 28 sweep tests failed on a dead site
    and 2 more asked one site about a channel that lives on another. One
    site id source means the ids can never disagree.

    channelid is TEST_CHANNEL_ID from .env when set, the way TEST_SITE_ID
    pins the site, else the first of test_channel_ids.

    userid/profileid are read from the session and roles. A placeholder that
    cannot be resolved leaves its key None, and the sweep skips endpoints
    that need it.
    """
    import time

    explicit = os.environ.get("TEST_CHANNEL_ID")
    ctx = {
        "siteid": test_site_id,
        "enterpriseid": test_enterprise_id,
        "channelid": int(explicit) if explicit else (test_channel_ids[0] if test_channel_ids else None),
        "userid": None,
        "profileid": None,
        "endtimestamp": int(time.time() * 1000),
        "starttimestamp": int(time.time() * 1000) - 7 * 24 * 60 * 60 * 1000,
    }
    ctx["endts"] = ctx["endtimestamp"]
    ctx["startts"] = ctx["starttimestamp"]

    # No row of data/endpoints.py uses {userid} or {profileid} today. The
    # lookups stay so a new row can, without a fixture change. A refused
    # answer, a transport error or an unreadable body leaves the key None
    # and the sweep skips the rows that need it. Any other error raises:
    # the except is narrow on purpose, so a mistake in this block cannot
    # hide for every session the way a bare except once hid one.
    try:
        r = authed_session.get(f"{api_base_url}/REST/central/user/session", timeout=30)
        if r.status_code == 200:
            body = r.json()
            res = body.get("result") if isinstance(body, dict) else None
            if res and isinstance(res[0], dict):
                ctx["userid"] = res[0].get("userId")
    except (requests.RequestException, ValueError, KeyError):
        pass
    if test_enterprise_id is not None:
        try:
            r = authed_session.get(
                f"{api_base_url}/REST/central/role/{test_enterprise_id}", timeout=30)
            if r.status_code == 200:
                body = r.json()
                roles = body.get("result") if isinstance(body, dict) else None
                if roles and isinstance(roles[0], dict):
                    ctx["profileid"] = roles[0].get("profileId")
        except (requests.RequestException, ValueError, KeyError):
            pass
    return ctx


@pytest.fixture(scope="session")
def recorded_clip_window(authed_session, api_base_url, discovery_context):
    """A real recorded clip's (start, end) for the discovered channel.

    Clip-export/media e2e tests need actual footage to export. Skips (not
    fails) when no channel or no recorded clip is available: that is a
    data/environment gap, not a bug these tests are meant to catch. A
    non-200 FAILS, the integration suite's rule: a dead site or a refused
    session must not look like a data gap.
    """
    site_id = discovery_context["siteid"]
    channel_id = discovery_context["channelid"]
    if channel_id is None:
        pytest.skip("No channel discovered on this site. Cannot resolve a recorded clip window")

    url = f"{api_base_url}/REST/site/{site_id}/getcurrentrecordbychannelid"
    r = authed_session.post(url, json=channel_id, timeout=60)
    if r.status_code != 200:
        pytest.fail(
            f"getCurrentRecordByChannelId answered {r.status_code} for channel {channel_id} "
            f"on site {site_id}: {r.text[:300]}")
    result = r.json().get("result") or []
    if not result:
        pytest.skip(f"No recorded clip for channel {channel_id} on site {site_id} (empty 200)")
    record = result[0]
    return {"channel_id": channel_id,
            "start_ts": record["startTimestamp"],
            "end_ts": record["endTimestamp"]}
