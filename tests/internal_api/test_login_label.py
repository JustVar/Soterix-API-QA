"""The login reads its fixed username label from .env, never from code.

The web app sends one fixed label in the `username` field of every login.
It is a server setting, so it lives in .env as LOGIN_USERNAME_LABEL. A
blank label must stop the login before any request, with a message that
names the setting, because the server would answer a blank label with the
same 400 as a stale password and send the reader to the wrong fix. These
tests are offline: the HTTP call is stubbed.
"""
from __future__ import annotations

import pytest

from api_clients import auth_helper
from api_clients.auth_helper import AuthHelper

SERVER = "https://qa.example.test"


class _Answer:
    """A 200 login answer that carries a session id."""

    status_code = 200
    text = ""

    def __init__(self):
        """Give each answer its own empty cookie jar."""
        self.cookies = {}

    def json(self):
        """Return the envelope the login endpoint sends on success."""
        return {"status": 2002, "code": 200, "result": [{"JSESSIONID": "s" * 32}]}


def test_a_blank_label_stops_the_login_before_any_request(monkeypatch):
    """A blank LOGIN_USERNAME_LABEL raises a message that names it, and no request is sent."""
    monkeypatch.setenv("LOGIN_USERNAME_LABEL", "")
    sent = []
    monkeypatch.setattr(auth_helper.requests, "post", lambda *a, **k: sent.append(k))

    with pytest.raises(RuntimeError, match="LOGIN_USERNAME_LABEL"):
        AuthHelper(SERVER)._api_login("qa@example.test", "pw")
    assert sent == []


def test_the_label_is_read_from_env_at_call_time(monkeypatch):
    """The request carries the label set in the environment when the login runs."""
    monkeypatch.setenv("LOGIN_USERNAME_LABEL", "Example Label")
    sent = []

    def fake_post(url, json=None, **kwargs):
        sent.append(json)
        return _Answer()

    monkeypatch.setattr(auth_helper.requests, "post", fake_post)

    AuthHelper(SERVER)._api_login("qa@example.test", "pw")
    assert sent[0]["username"] == "Example Label"
    assert sent[0]["accountid"] == "qa@example.test"
    assert sent[0]["password"] != "pw"
