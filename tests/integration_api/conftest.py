# conftest.py -- third-party /v-integration-api suite.
#
# Everything this suite needs lives in this directory. Do not add fixtures
# to the root conftest.py, and do not reuse or edit api_clients/. That is
# internal-suite plumbing (see README.md here for why).
import os
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Load .env here, anchored to the repo root, so a run that selects only one
# test in this suite still sees VSAAS_INTEGRATION_KEY. Without this the key
# was only loaded as a side effect of the env_config fixture, and selection
# order decided whether the sweep ran or silently skipped.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


@pytest.fixture(scope="session")
def integration_key():
    """The static x-vsaas-key value. Skips the suite while no key is set.

    An empty value counts as unset: .env.template ships the variable empty,
    and python-dotenv loads empty strings as-is.
    """
    key = os.environ.get("VSAAS_INTEGRATION_KEY")
    if not key:
        pytest.skip("VSAAS_INTEGRATION_KEY is not set. See .env.template")
    return key


@pytest.fixture(scope="session")
def integration_base_url(env_config):
    """Base URL for /v-integration-api. Skips where the surface is absent.

    Only config/env/qa.py carries a URL. Stage and prod carry None because
    the surface 404s there (as of 2026-08-05). Read with .get() so partner
    config variants without the key also skip instead of erroring.
    """
    url = env_config.get("integration_api_base_url")
    if not url:
        pytest.skip("The integration API surface is not deployed in this environment")
    return url


@pytest.fixture(scope="session")
def integration_session(integration_key):
    """A requests.Session carrying the one auth header the surface needs."""
    s = requests.Session()
    s.headers["x-vsaas-key"] = integration_key
    return s


@pytest.fixture(scope="session")
def integration_ids(integration_session, integration_base_url):
    """Real ids for path templates, discovered through the surface itself.

    Walks the sites the key can see and uses the first one that has a
    channel, so tenant data drift (a first site with no cameras) does not
    blank the sweep. A non-200 on discovery FAILS loudly instead of
    skipping: a revoked key must not look like a data gap.
    """
    import time

    r = integration_session.get(f"{integration_base_url}/REST/site", timeout=30)
    if r.status_code != 200:
        pytest.fail(
            f"Discovery failed: GET /REST/site returned {r.status_code}: "
            f"{r.text[:300]}")
    sites = r.json().get("result") or []
    if not sites:
        pytest.skip("The key sees no sites (empty 200). Cannot resolve path ids")

    tried = []
    for site in sites:
        siteid = site["siteId"]
        r = integration_session.get(
            f"{integration_base_url}/REST/site/channel/{siteid}", timeout=30)
        if r.status_code != 200:
            pytest.fail(
                f"Discovery failed: GET /REST/site/channel/{siteid} returned "
                f"{r.status_code}: {r.text[:300]}")
        entries = r.json().get("result") or []
        channels = entries[0].get("channels") if entries else None
        if channels:
            return {
                "siteid": siteid,
                "channelid": channels[0]["id"],
                "starttimestamp": int(time.time() * 1000) - 3600 * 1000,
            }
        tried.append(siteid)

    pytest.skip(f"No channels on any visible site (tried siteIds {tried}). "
                f"Cannot resolve path ids")
