"""API Integration key lifecycle (Admin > Integrations > API Integration).

Key management lives on the internal /v-apiserver
(/REST/api/integration/key/*). The keys authenticate the third-party
/v-integration-api surface. This test walks the whole lifecycle with its
own throwaway key, named uniquely per run, and never touches keys it did
not create. A stale-key sweep at setup removes AutoTest keys older than an
hour that a killed run may have stranded.

Steps:
    1. Generate a new API integration key named "AutoTest ..." for the
       enterprise.
    2. Read the key list and find the new key.
    3. Call the integration surface with the new key.
    4. Disable the key, then call the surface with it again.
    5. Re-enable the key and call the surface once more.
    6. Delete the key, then read the list and call the surface again.

Expected:
    Create, disable, enable, and delete each answer 200. The surface
    accepts the key while it is enabled and refuses it with 401 after it
    is disabled or deleted. The list reflects every change.
"""
import time
import uuid
from urllib.parse import urlparse

import pytest
import requests

pytestmark = [pytest.mark.internal, pytest.mark.api, pytest.mark.env_qa]

KEY_PREFIX = "AutoTest lifecycle key"
STALE_MS = 60 * 60 * 1000  # sweep AutoTest keys older than an hour


def _list_keys(session, base, ent):
    r = session.get(f"{base}/REST/api/integration/key/{ent}", timeout=30)
    if r.status_code != 200:
        pytest.fail(f"key list failed: {r.status_code} {r.text[:200]}")
    return r.json().get("result") or []


@pytest.fixture()
def key_admin(api_base_url, api_auth_token, env_config):
    """Session for the internal key-management endpoints, plus cleanup.

    The run's key name is unique (uuid suffix), so concurrent runs never
    delete each other's in-flight keys. Cleanup removes this run's key and
    any AutoTest key old enough to be a stranded leftover, and warns loudly
    when a delete does not answer 200 so a stranded credential is visible.
    """
    if not (env_config.get("allow_write") and env_config.get("allow_delete")):
        pytest.skip("Key lifecycle needs an environment that allows writes and deletes")
    integration_url = env_config.get("integration_api_base_url")
    if not integration_url:
        pytest.skip("The integration API surface is not deployed in this environment")

    s = requests.Session()
    s.headers["Cookie"] = f"JSESSIONID={api_auth_token}"
    key_name = f"{KEY_PREFIX} {uuid.uuid4().hex[:8]} (safe to delete)"
    ctx = {"session": s, "base": api_base_url, "surface": integration_url,
           # The key's host allowlist names the server under test, so a
           # second server needs no edit here.
           "host": urlparse(env_config["base_url"]).hostname,
           "enterprise_id": None, "key_name": key_name}
    yield ctx

    ent = ctx["enterprise_id"]
    if ent is None:
        return
    now_ms = int(time.time() * 1000)
    for k in _list_keys(s, api_base_url, ent):
        name = k.get("name", "")
        mine = name == key_name
        stale = (name.startswith(KEY_PREFIX)
                 and now_ms - k.get("createdAt", now_ms) > STALE_MS)
        if mine or stale:
            r = s.delete(
                f"{api_base_url}/REST/api/integration/key/{k['key']}",
                timeout=30)
            if r.status_code != 200:
                print(f"WARNING: cleanup failed to delete key "
                      f"'{name}' ({r.status_code}). Remove it by hand in "
                      f"Admin > Integrations > API Integration.")


def _surface_status(ctx, key_value):
    r = requests.get(f"{ctx['surface']}/REST/site",
                     headers={"x-vsaas-key": key_value}, timeout=30)
    return r.status_code


def _wait_surface_status(ctx, key_value, expected, attempts=5, delay=2):
    """Poll the surface briefly: key state changes may propagate async."""
    for _ in range(attempts):
        code = _surface_status(ctx, key_value)
        if code == expected:
            return code
        time.sleep(delay)
    return code


def test_key_lifecycle(key_admin, discovered_enterprise_id):
    ctx = key_admin
    ent = discovered_enterprise_id
    ctx["enterprise_id"] = ent
    s, base = ctx["session"], ctx["base"]
    key_name = ctx["key_name"]

    # 1. Create
    body = {"enterpriseId": ent, "name": key_name,
            "host": [ctx["host"]],
            "description": ["Created by the API test suite, deleted at teardown."]}
    r = s.post(f"{base}/REST/api/integration/key/generate", json=body, timeout=30)
    assert r.status_code == 200, f"generate failed: {r.status_code} {r.text[:200]}"
    created = r.json()["result"][0]
    key_value = created["key"]
    assert created["name"] == key_name
    assert created["status"] == 1

    # 2. Listed
    listing = _list_keys(s, base, ent)
    assert any(k["key"] == key_value for k in listing), "new key missing from the list"

    # 3. Enabled key works on the surface
    assert _wait_surface_status(ctx, key_value, 200) == 200, \
        "surface rejected a freshly created, enabled key"

    # 4. Disable blocks the surface
    r = s.get(f"{base}/REST/api/integration/key/{key_value}/status/0", timeout=30)
    assert r.status_code == 200, f"disable failed: {r.status_code} {r.text[:200]}"
    assert _wait_surface_status(ctx, key_value, 401) == 401, \
        "surface still accepts a disabled key"

    # 5. Re-enable restores access
    r = s.get(f"{base}/REST/api/integration/key/{key_value}/status/1", timeout=30)
    assert r.status_code == 200, f"enable failed: {r.status_code} {r.text[:200]}"
    assert _wait_surface_status(ctx, key_value, 200) == 200, \
        "surface rejects a re-enabled key"

    # 6. Delete removes it everywhere
    r = s.delete(f"{base}/REST/api/integration/key/{key_value}", timeout=30)
    assert r.status_code == 200, f"delete failed: {r.status_code} {r.text[:200]}"
    listing = _list_keys(s, base, ent)
    assert not any(k["key"] == key_value for k in listing), "deleted key still listed"
    assert _wait_surface_status(ctx, key_value, 401) == 401, \
        "surface still accepts a deleted key"
