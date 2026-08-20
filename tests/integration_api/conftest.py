# conftest.py -- third-party /v-integration-api suite.
#
# Everything this suite needs lives in this directory. Do not add fixtures
# to the root conftest.py, and do not reuse or edit api_clients/ - that is
# internal-suite plumbing (see README.md here for why).
import os

import pytest
import requests


@pytest.fixture(scope="session")
def integration_key():
    """The static x-vsaas-key value. Skips the suite while no key is issued.

    An empty value counts as unset: .env.template ships the variable empty,
    and python-dotenv loads empty strings as-is.
    """
    key = os.environ.get("VSAAS_INTEGRATION_KEY")
    if not key:
        pytest.skip("VSAAS_INTEGRATION_KEY is not set; see .env.template")
    return key


@pytest.fixture(scope="session")
def integration_base_url(env_config):
    """Base URL for /v-integration-api. Skips where the surface is absent.

    Only config/env/qa.py carries a URL; stage and prod carry None because
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
