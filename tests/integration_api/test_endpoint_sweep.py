"""Sweep of every documented /v-integration-api endpoint.

Steps:
    1. Sign nothing in: attach the static x-vsaas-key header.
    2. Call each GET endpoint from the catalogue with real discovered ids.
    3. Check the response against the contract observed for that endpoint.

Expected:
    Every endpoint answers 200 with its documented shape: data endpoints
    return a result list, portal endpoints return their pointer message,
    and stream-start endpoints return a session with a stream URL.
"""
import pytest

from .data.endpoints import GET_ENDPOINTS

pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.env_qa]


def _json_or_fail(name, r):
    try:
        return r.json()
    except ValueError:
        pytest.fail(f"{name}: non-JSON {r.status_code} body: {r.text[:300]}")


@pytest.mark.parametrize(
    "name,template,kind", GET_ENDPOINTS, ids=[e[0] for e in GET_ENDPOINTS])
def test_get_endpoint(name, template, kind, integration_session,
                      integration_base_url, integration_ids):
    path = template.format(**integration_ids)
    r = integration_session.get(integration_base_url + path, timeout=60)

    if kind == "no_data":
        # Only the auth layer is checkable without a real id: the surface
        # answers 400 "check your request parameters" for a guessed id.
        # 401 means auth broke. 404 means the endpoint disappeared.
        assert r.status_code in (200, 400), (
            f"{name}: GET {path} returned {r.status_code}: {r.text[:300]}")
        return

    assert r.status_code == 200, (
        f"{name}: GET {path} returned {r.status_code}: {r.text[:300]}")
    body = _json_or_fail(name, r)
    result = body.get("result")
    message = body.get("message", "")

    if kind == "pointer":
        # Pointer responses carry no code/result envelope: just a message
        # and the portal URL.
        assert "link" in message.lower(), (
            f"{name}: expected the portal-pointer message, got: {message}")
        assert body.get("streamingServerUrl", "").startswith("https://"), (
            f"{name}: pointer response lacks streamingServerUrl: {body}")
        return

    assert body.get("code") == 200, f"{name}: body code {body.get('code')}"
    if kind == "data":
        assert isinstance(result, list), (
            f"{name}: expected a result list, got {type(result).__name__}")
        assert result, f"{name}: result list is empty"
    elif kind == "data_any":
        # Valid to be empty for some camera models / tenant states.
        assert isinstance(result, list), (
            f"{name}: expected a result list, got {type(result).__name__}")
    elif kind == "session":
        assert isinstance(result, list), f"{name}: expected a result list"
        assert "updated" in message.lower(), (
            f"{name}: expected the session-updated message, got: {message}")
    elif kind == "stream_start":
        assert isinstance(result, list) and result, (
            f"{name}: expected a session object in result "
            f"(channel {integration_ids['channelid']}: for startarchive a "
            f"channel with no recorded footage is a data gap, not an API bug)")
        url = result[0].get("streamurl")
        assert isinstance(url, str) and url, (
            f"{name}: session object lacks a usable streamurl: {result[0]}")
    else:  # pragma: no cover - catalogue typo guard
        pytest.fail(f"Unknown kind '{kind}' for {name}")
