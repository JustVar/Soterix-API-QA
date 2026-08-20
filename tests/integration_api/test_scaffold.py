# Replace this file with real tests once VSAAS_INTEGRATION_KEY is issued.
# It exists so the suite always collects at least one test: an empty
# directory makes `pytest tests/integration_api` exit 5 (no tests ran),
# which reads as failure to CI and to people.
import pytest

pytestmark = pytest.mark.integration


def test_scaffold_fixtures_resolve(integration_base_url, integration_session):
    """Prove the suite's fixtures wire up; skips until a key is issued."""
    assert integration_base_url.endswith("/v-integration-api")
    assert "x-vsaas-key" in integration_session.headers
