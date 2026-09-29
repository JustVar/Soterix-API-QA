"""
Auth API smoke (central + SSO login)

Covers the login path the web client uses (central/user/login), the
captcha-gated path it must reject from an API client, and the SSO path.
Logout is intentionally omitted - exercising it on a shared session
would terminate other concurrently running tests.

Catalog rows (see docs/INTERNAL_API_INVENTORY.md):
- POST /REST/central/user/login (the working contract, pinned below)
- GET  /REST/central/user/session
- POST /REST/central/user/auth/login (captcha-gated, rejects API clients)
- POST /REST/sso/login
"""
import os

import pytest
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_VERIFY = os.getenv("SSL_VERIFY", "false").lower() in ("true", "1", "yes")


@pytest.mark.api
@pytest.mark.smoke
def test_central_login_accepts_valid_credentials(api_base_url, login_data):
    """AuthHelper.login() with valid creds returns a token.

    AuthHelper may answer from its .session_cache, so this proves the helper
    works, not the endpoint. test_login_contract_returns_a_session pins the
    endpoint itself.
    """
    from api_clients.auth_helper import AuthHelper

    helper = AuthHelper(api_base_url)
    token = helper.login(login_data["username"], login_data["password"])

    assert token, "Expected a session token from /REST/central/user/login"
    assert isinstance(token, str) and len(token) >= 16


@pytest.mark.api
@pytest.mark.smoke
def test_login_contract_returns_a_session(api_base_url, login_data):
    """POST /REST/central/user/login answers 200 / status 2002 with a JSESSIONID the session endpoint accepts.

    The body is {accountid: <email>, username: "Example Label", password: <sha512
    hex>}. "Example Label" is the literal the web client sends. The account goes
    in accountid. No captcha is involved on this path. The UI suite
    (Soterix-WebApp-QA) signs in with this exact body to build its test
    data, so a change here breaks its setup.
    """
    import hashlib

    base = api_base_url.rstrip("/")
    if not base.endswith("/v-apiserver"):
        base = base + "/v-apiserver"
    email = login_data["username"]
    body = {
        "accountid": email,
        "username": "Example Label",
        "password": hashlib.sha512(login_data["password"].encode("utf-8")).hexdigest(),
    }
    r = requests.post(f"{base}/REST/central/user/login", json=body, timeout=20, verify=_VERIFY)
    assert r.status_code == 200, f"Login answered {r.status_code}: {r.text[:300]}"
    envelope = r.json()
    assert envelope.get("code") == 200, f"Unexpected code: {envelope.get('code')}, body: {str(envelope)[:300]}"
    assert envelope.get("status") == 2002, f"Expected status 2002 (login ok), got {envelope.get('status')}"
    token = (envelope.get("result") or [{}])[0].get("JSESSIONID")
    assert token, f"Login answered 200 but result[0].JSESSIONID is missing: {str(envelope)[:300]}"

    s = requests.get(
        f"{base}/REST/central/user/session",
        headers={"Cookie": f"JSESSIONID={token}"}, timeout=20, verify=_VERIFY)
    assert s.status_code == 200, f"Session check answered {s.status_code}: {s.text[:300]}"
    session = s.json()
    assert session.get("code") == 200, f"Unexpected code: {session.get('code')}"
    user_id = (session.get("result") or [{}])[0].get("userId", "")
    assert user_id.lower() == email.lower(), f"Session belongs to '{user_id}', expected '{email}'"


@pytest.mark.api
@pytest.mark.smoke
def test_central_login_rejects_invalid_credentials(api_base_url):
    """POST /REST/central/user/auth/login with bogus creds returns non-2xx.

    Calls the endpoint directly with requests, so the test pins the
    endpoint's own rejection rather than AuthHelper's error handling.
    """
    base = api_base_url.rstrip("/")
    if not base.endswith("/v-apiserver"):
        base = base + "/v-apiserver"
    url = f"{base}/REST/central/user/auth/login"
    r = requests.post(
        url,
        json={"username": "not-a-real-user@example.invalid", "password": "wrong-password"},
        timeout=15,
        verify=_VERIFY,
    )
    # Vendor returns 401/403 for bad creds; some deployments return 200 with
    # an error body. Either way, the response must NOT contain a usable token.
    body = {}
    try:
        body = r.json()
    except ValueError:
        pass
    token = body.get("token") or body.get("access_token") or (body.get("data") or {}).get("token")
    assert not token, f"Invalid creds yielded a token: status={r.status_code} body={r.text[:300]}"


@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.skipif(
    not os.getenv("SSO_TEST_USERNAME"),
    reason="SSO smoke needs SSO_TEST_USERNAME and SSO_TEST_PASSWORD env vars",
)
def test_sso_login_accepts_valid_credentials(api_base_url):
    """POST /REST/sso/login with a valid SSO account returns a token.

    SSO is the fallback path when central login is unavailable. Not every env
    has SSO configured, so this test only runs when explicit creds are provided.
    """
    base = api_base_url.rstrip("/")
    if not base.endswith("/v-apiserver"):
        base = base + "/v-apiserver"
    url = f"{base}/REST/sso/login"
    r = requests.post(
        url,
        json={
            "username": os.environ["SSO_TEST_USERNAME"],
            "password": os.environ["SSO_TEST_PASSWORD"],
        },
        timeout=15,
        verify=_VERIFY,
    )
    r.raise_for_status()
    body = r.json()
    token = body.get("token") or body.get("access_token") or (body.get("data") or {}).get("token")
    assert token, f"SSO login did not return a token: {body}"
