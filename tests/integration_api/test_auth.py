"""Auth boundary tests for /v-integration-api.

Steps:
    1. Call a documented endpoint with no key header at all.
    2. Call it again with a made-up key value, then an empty one.
    3. Read the error body of each refusal.

Expected:
    Every call is refused with HTTP 401 and the stable error body
    (status 9581, "Invalid API Key in request headers."). No data leaks.

The tests take the integration_key fixture without sending it: it gates
them to machines that hold a key, so CI and keyless clones skip instead of
sending live traffic to the shared tenant.
"""
import pytest
import requests

pytestmark = [pytest.mark.integration, pytest.mark.api,
              pytest.mark.security, pytest.mark.env_qa]

PROBE = "/REST/site"


def _assert_rejected(r):
    assert r.status_code == 401, f"expected 401, got {r.status_code}"
    try:
        body = r.json()
    except ValueError:
        pytest.fail(f"non-JSON 401 body: {r.text[:300]}")
    assert body.get("status") == 9581, f"unexpected error status: {body}"
    assert body.get("code") == 401
    assert "Invalid API Key" in body.get("message", "")
    assert body.get("result") == [], "a rejected call must not return data"


def test_no_key_is_rejected(integration_base_url, integration_key):
    r = requests.get(integration_base_url + PROBE, timeout=30)
    _assert_rejected(r)


def test_bogus_key_is_rejected(integration_base_url, integration_key):
    r = requests.get(integration_base_url + PROBE,
                     headers={"x-vsaas-key": "not-a-real-key"}, timeout=30)
    _assert_rejected(r)


def test_empty_key_is_rejected(integration_base_url, integration_key):
    r = requests.get(integration_base_url + PROBE,
                     headers={"x-vsaas-key": ""}, timeout=30)
    _assert_rejected(r)
