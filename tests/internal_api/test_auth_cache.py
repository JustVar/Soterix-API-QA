"""The session cache answers only the account that filled it.

AuthHelper keeps the JSESSIONID in .session_cache for 8 hours so a run
does not sign in again. The cache is keyed on the server AND the account.
Keyed on the server alone, a changed QA_USER would reuse the previous
account's session for up to 8 hours, and the wrong account would run the
whole suite without one error. These tests are offline: the login and the
token check are stubbed.
"""
from __future__ import annotations

import json

import pytest

from api_clients.auth_helper import AuthHelper

SERVER = "https://qa.example.test"


@pytest.fixture
def helper(monkeypatch, tmp_path):
    """An AuthHelper whose cache file lives in tmp_path and whose HTTP is stubbed."""
    monkeypatch.chdir(tmp_path)
    logins = []

    def fake_login(self, email, password):
        logins.append(email)
        return f"token-for-{email}"

    monkeypatch.setattr(AuthHelper, "_api_login", fake_login)
    monkeypatch.setattr(AuthHelper, "_validate_token", lambda self, token: True)
    h = AuthHelper(SERVER)
    h.logins = logins
    return h


def test_the_same_account_reuses_the_cached_token(helper):
    first = helper.login("one@example.test", "pw")
    again = AuthHelper(SERVER)
    again.logins = helper.logins
    assert again.login("one@example.test", "pw") == first
    assert helper.logins == ["one@example.test"], "the second call must answer from the cache"


def test_a_second_account_gets_a_fresh_login(helper):
    helper.login("one@example.test", "pw")
    other = AuthHelper(SERVER)
    other.logins = helper.logins
    token = other.login("two@example.test", "pw")
    assert token == "token-for-two@example.test"
    assert helper.logins == ["one@example.test", "two@example.test"], (
        "a different QA_USER must not receive the previous account's session")


def test_a_cache_without_an_email_is_ignored(helper, tmp_path):
    """A cache file from before the key held the account is a miss, not a hit."""
    (tmp_path / ".session_cache").write_text(
        json.dumps({"token": "stale", "base_url": helper.base_url, "timestamp": 10**12}),
        encoding="utf-8")
    assert helper.login("one@example.test", "pw") == "token-for-one@example.test"
    assert helper.logins == ["one@example.test"]
