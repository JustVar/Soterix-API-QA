# conftest.py -- Soterix-API-QA (shared by every suite)
#
# Keep this file small. Pytest imports it for EVERY run, including runs of
# suites that share nothing with the internal /v-apiserver tests, so anything
# imported here can break every suite at collection time. Suite plumbing
# lives with each suite:
#
#   tests/internal_api/conftest.py            internal /v-apiserver fixtures
#   tests/integration_api/conftest.py  /v-integration-api fixtures
#
# Add a fixture here only when every suite needs it.
import pytest

# QA Touch result reporting. Dormant unless armed with
# --qatouch-upload --qatouch-run <RUN_KEY> (or QATOUCH_UPLOAD/QATOUCH_RUN_KEY).
# pytest requires pytest_plugins to be declared in the rootdir conftest.
pytest_plugins = ['plugins.qatouch_reporter']


@pytest.fixture(scope="session")
def env_config():
    """Resolved environment configuration dict (from ENV).

    The import is deferred so a config error (for example an unknown ENV
    value) fails only the tests that use the config, not collection of
    every suite in the repo.
    """
    from config.base_config import config
    return config


@pytest.fixture(scope="session")
def base_url(env_config):
    """Site root from the active env config."""
    return env_config.get("base_url", "")
