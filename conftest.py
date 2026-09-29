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
# The run archive keeps every run under reports/runs/ (run.html, summary.json
# with per-test durations, the index) and carries the live in-progress record;
# RUN_ARCHIVE=off is its kill switch. pytest requires pytest_plugins to be
# declared in the rootdir conftest.
pytest_plugins = ['plugins.qatouch_reporter', 'plugins.run_archive']


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


# ---------------------------------------------------------------------------
# Report title: name the product under test, not just the repo.
# The QA Touch project key selects the product (QATOUCH_PROJECT_ID in .env;
# NexaiQ-Core when unset). The key-to-product table is the shared package's:
# every Soterix QA repo reports into the same QA Touch projects.
# ---------------------------------------------------------------------------

def pytest_html_report_title(report):
    import os

    # Imported here, not at the top: a missing package then fails with the
    # shim's message (plugins/qatouch_reporter.py, "Run: python -m pip
    # install -r requirements.txt") instead of a bare ModuleNotFoundError.
    from soterix_qa_shared.reporting.products import DEFAULT_KEY, PRODUCTS
    key = os.environ.get("QATOUCH_PROJECT_ID") or DEFAULT_KEY
    product = PRODUCTS.get(key, f"project {key}")
    env = os.environ.get("ENV", "qa")
    report.title = f"{product} - API tests ({env})"
