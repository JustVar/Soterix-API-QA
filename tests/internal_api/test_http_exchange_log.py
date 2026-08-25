"""Unit tests for the BaseAPIClient exchange log (api_clients/base_api_client.py).

No network: requests.request is replaced with a fake. The tests cover
masking, truncation, the 20-exchange cap, and the per-test clearing that
this suite's conftest does at setup. They need no credentials.
"""
import hashlib

import pytest
import requests

from api_clients import base_api_client as bac

BASE = "https://api.example.invalid"
SHA512 = hashlib.sha512(b"hunter2").hexdigest()
SESSION_ID = "0123456789ABCDEF0123456789ABCDEF"


def _fake_requests(monkeypatch, status=200, body="{}", content_type="application/json", error=None):
    """Replace requests.request with a stub that answers with one fixed response."""
    calls = []

    def fake(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if error is not None:
            raise error
        response = requests.Response()
        response.status_code = status
        response._content = body.encode("utf-8")
        response.headers["Content-Type"] = content_type
        response.url = requests.Request(method, url, params=kwargs.get("params")).prepare().url
        return response

    monkeypatch.setattr(bac.requests, "request", fake)
    return calls


# ---------------------------------------------------------------------------
# Masking
# ---------------------------------------------------------------------------

def test_login_password_and_session_id_are_masked(monkeypatch):
    login_response = f'{{"status": 2002, "code": 200, "result": [{{"JSESSIONID": "{SESSION_ID}"}}]}}'
    _fake_requests(monkeypatch, body=login_response)
    client = bac.BaseAPIClient(BASE)

    client.post("/REST/central/user/login",
                json={"accountid": "qa@example.invalid", "username": "Example Label", "password": SHA512})

    record = client.exchanges[-1]
    assert SHA512 not in record["request_body"]
    assert '"password": "***"' in record["request_body"]
    assert '"accountid": "qa@example.invalid"' in record["request_body"]
    assert SESSION_ID not in record["response_body"]
    assert '"JSESSIONID": "***"' in record["response_body"]


def test_session_id_in_query_and_cookie_text_is_masked(monkeypatch):
    _fake_requests(monkeypatch, body=f"cookie: JSESSIONID={SESSION_ID}; Path=/")
    client = bac.BaseAPIClient(BASE, token=SESSION_ID)

    client.get("/REST/x", params={"JSESSIONID": SESSION_ID, "siteId": 16})

    record = client.exchanges[-1]
    assert SESSION_ID not in record["url"]
    assert "JSESSIONID=***" in record["url"]
    assert "siteId=16" in record["url"]
    assert record["response_body"] == "cookie: JSESSIONID=***; Path=/"


def test_bare_sha512_digest_is_masked_without_a_key():
    assert bac.mask_text(f"digest {SHA512} end") == "digest *** end"


def test_secret_keys_are_masked_in_nested_bodies(monkeypatch):
    _fake_requests(monkeypatch)
    client = bac.BaseAPIClient(BASE)

    client.put("/REST/user", json={"user": {"newPassword": "plain", "name": "Ann"}, "token": "t"})

    body = client.exchanges[-1]["request_body"]
    assert "plain" not in body
    assert '"newPassword": "***"' in body
    assert '"token": "***"' in body
    assert '"name": "Ann"' in body


# ---------------------------------------------------------------------------
# Truncation and record shape
# ---------------------------------------------------------------------------

def test_long_bodies_are_truncated_to_the_limit(monkeypatch):
    _fake_requests(monkeypatch, body="r" * 5000)
    client = bac.BaseAPIClient(BASE)

    client.post("/REST/big", json={"payload": "q" * 5000})

    record = client.exchanges[-1]
    assert record["response_body"] == "r" * bac.BODY_LIMIT + "... [5000 chars total]"
    assert record["request_body"].startswith('{"payload": "' + "q" * 100)
    assert record["request_body"].endswith("... [5015 chars total]")
    assert len(record["request_body"]) < bac.BODY_LIMIT + 40


def test_record_carries_method_url_status_and_elapsed(monkeypatch):
    _fake_requests(monkeypatch, status=404, body='{"code": 404}')
    client = bac.BaseAPIClient(BASE)

    client.delete("/REST/site/16/bookmark/9")

    record = client.exchanges[-1]
    assert record["method"] == "DELETE"
    assert record["url"] == f"{BASE}/v-apiserver/REST/site/16/bookmark/9"
    assert record["status"] == 404
    assert isinstance(record["elapsed_ms"], int) and record["elapsed_ms"] >= 0
    assert record["request_body"] == ""
    assert record["response_body"] == '{"code": 404}'
    assert record["error"] is None


def test_binary_responses_are_summarised_not_dumped(monkeypatch):
    _fake_requests(monkeypatch, body="\xff\xd8" + "x" * 3000, content_type="image/jpeg")
    client = bac.BaseAPIClient(BASE)

    client.get("/REST/site/16/channel/97/snap")

    assert client.exchanges[-1]["response_body"].startswith("<image/jpeg, ")


def test_transport_errors_are_recorded_and_re_raised(monkeypatch):
    _fake_requests(monkeypatch, error=requests.ConnectionError("refused"))
    client = bac.BaseAPIClient(BASE)

    with pytest.raises(requests.ConnectionError):
        client.get("/REST/down")

    record = client.exchanges[-1]
    assert record["status"] is None
    assert record["error"] == "ConnectionError: refused"
    assert "no response (ConnectionError: refused)" in bac.format_exchanges([record])


def test_format_exchanges_renders_numbered_lines(monkeypatch):
    _fake_requests(monkeypatch, body='{"ok": true}')
    client = bac.BaseAPIClient(BASE)
    client.post("/REST/a", json={"k": 1})
    client.get("/REST/b")

    lines = bac.format_exchanges(bac.recent_exchanges()).splitlines()

    assert lines[0].startswith(f"1. POST {BASE}/v-apiserver/REST/a -> 200 (")
    assert lines[1] == '   request: {"k": 1}'
    assert lines[2] == '   response: {"ok": true}'
    assert lines[3].startswith(f"2. GET {BASE}/v-apiserver/REST/b -> 200 (")


# ---------------------------------------------------------------------------
# Cap and aggregation
# ---------------------------------------------------------------------------

def test_each_client_keeps_only_the_last_20_exchanges(monkeypatch):
    _fake_requests(monkeypatch)
    client = bac.BaseAPIClient(BASE)

    for n in range(25):
        client.get(f"/REST/call/{n}")

    assert bac.EXCHANGE_LIMIT == 20
    assert len(client.exchanges) == 20
    assert client.exchanges[0]["url"].endswith("/REST/call/5")
    assert client.exchanges[-1]["url"].endswith("/REST/call/24")


def test_recent_exchanges_merges_clients_in_call_order_and_caps_at_20(monkeypatch):
    _fake_requests(monkeypatch)
    first = bac.BaseAPIClient(BASE)
    second = bac.BaseAPIClient(BASE)

    for n in range(15):
        first.get(f"/REST/first/{n}")
        second.get(f"/REST/second/{n}")

    merged = bac.recent_exchanges()
    assert len(merged) == 20
    seqs = [e["seq"] for e in merged]
    assert seqs == sorted(seqs)
    assert merged[-1]["url"].endswith("/REST/second/14")
    assert merged[-2]["url"].endswith("/REST/first/14")


# ---------------------------------------------------------------------------
# Clearing. The last two tests run in file order: the first leaves
# exchanges behind, the second proves the setup hook removed them.
# ---------------------------------------------------------------------------

def test_clear_exchanges_empties_every_client(monkeypatch):
    _fake_requests(monkeypatch)
    first, second = bac.BaseAPIClient(BASE), bac.BaseAPIClient(BASE)
    first.get("/REST/a")
    second.get("/REST/b")
    assert len(bac.recent_exchanges()) == 2

    bac.clear_exchanges()

    assert bac.recent_exchanges() == []
    assert len(first.exchanges) == 0 and len(second.exchanges) == 0


_leftover = {}


def test_leaves_exchanges_behind_for_the_next_test(monkeypatch):
    _fake_requests(monkeypatch)
    _leftover["client"] = bac.BaseAPIClient(BASE)
    _leftover["client"].get("/REST/leftover")
    assert len(bac.recent_exchanges()) == 1


def test_setup_hook_cleared_the_previous_tests_exchanges():
    assert "client" in _leftover, "runs after test_leaves_exchanges_behind_for_the_next_test"
    assert bac.recent_exchanges() == []
    assert len(_leftover["client"].exchanges) == 0
