"""
Auth API smoke (central + SSO login)

Covers the login path the web client uses (central/user/login), its
refusal of an unknown account, and the SSO path.
Logout is intentionally omitted - exercising it on a shared session
would terminate other concurrently running tests.

Catalog rows (see docs/INTERNAL_API_INVENTORY.md):
- POST /REST/central/user/login (the working contract, pinned below)
- GET  /REST/central/user/session
- POST /REST/sso/login
"""
import os

import pytest
import requests
import urllib3

from api_clients.tls import ssl_verify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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

    The body is {accountid: <email>, username: <LOGIN_USERNAME_LABEL>,
    password: <sha512 hex>}. The label is the fixed value the web client
    sends for every account. The account goes in accountid. No captcha is
    involved on this path. The UI suite
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
        "username": os.environ.get("LOGIN_USERNAME_LABEL", ""),
        "password": hashlib.sha512(login_data["password"].encode("utf-8")).hexdigest(),
    }
    r = requests.post(f"{base}/REST/central/user/login", json=body, timeout=20, verify=ssl_verify())
    assert r.status_code == 200, f"Login answered {r.status_code}: {r.text[:300]}"
    envelope = r.json()
    assert envelope.get("code") == 200, f"Unexpected code: {envelope.get('code')}, body: {str(envelope)[:300]}"
    assert envelope.get("status") == 2002, f"Expected status 2002 (login ok), got {envelope.get('status')}"
    token = (envelope.get("result") or [{}])[0].get("JSESSIONID")
    assert token, f"Login answered 200 but result[0].JSESSIONID is missing: {str(envelope)[:300]}"

    s = requests.get(
        f"{base}/REST/central/user/session",
        headers={"Cookie": f"JSESSIONID={token}"}, timeout=20, verify=ssl_verify())
    assert s.status_code == 200, f"Session check answered {s.status_code}: {s.text[:300]}"
    session = s.json()
    assert session.get("code") == 200, f"Unexpected code: {session.get('code')}"
    user_id = (session.get("result") or [{}])[0].get("userId", "")
    assert user_id.lower() == email.lower(), f"Session belongs to '{user_id}', expected '{email}'"


@pytest.mark.api
@pytest.mark.smoke
def test_central_login_rejects_invalid_credentials(api_base_url):
    """POST /REST/central/user/login for an unknown account answers 404 and opens no session.

    This is the login the web client and AuthHelper use, so the refusal is
    the one a stale QA_USER meets. The inventory records 404 "There is no
    user with the userid!" for an unknown account (verified 2026-08-24).
    The test calls the endpoint directly with requests, so it pins the
    server's refusal rather than AuthHelper's handling of it. An unknown
    account is used on purpose: wrong passwords against the shared QA
    account could lock it.
    """
    import hashlib

    label = os.environ.get("LOGIN_USERNAME_LABEL", "")
    if not label:
        pytest.skip("LOGIN_USERNAME_LABEL is blank in .env, so the server would refuse the label, not the account")
    base = api_base_url.rstrip("/")
    if not base.endswith("/v-apiserver"):
        base = base + "/v-apiserver"
    body = {
        "accountid": "not-a-real-user@example.invalid",
        "username": label,
        "password": hashlib.sha512(b"wrong-password").hexdigest(),
    }
    r = requests.post(f"{base}/REST/central/user/login", json=body, timeout=15, verify=ssl_verify())
    assert r.status_code == 404, f"Expected 404 for an unknown account, got {r.status_code}: {r.text[:300]}"
    try:
        result = r.json().get("result") or []
    except ValueError:
        result = []
    tokens = [row.get("JSESSIONID") for row in result if isinstance(row, dict) and row.get("JSESSIONID")]
    assert not tokens, f"An unknown account got a session in the body: {r.text[:300]}"
    assert not r.cookies.get("JSESSIONID"), "An unknown account got a session cookie"


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
        verify=ssl_verify(),
    )
    r.raise_for_status()
    body = r.json()
    token = body.get("token") or body.get("access_token") or (body.get("data") or {}).get("token")
    assert token, f"SSO login did not return a token: {body}"
