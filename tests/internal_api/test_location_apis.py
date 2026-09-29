"""
Camera group (location) API contract

The UI suite (Soterix-WebApp-QA, fixture api_camera_group) seeds camera
groups through these 3 endpoints. A contract change here breaks that
setup, so these tests pin the exact requests and answers.

A camera group in Admin > Sites is a location in the API. The group
endpoints (addgroup, grouptree, deletegroup) are a different entity the
Admin UI never shows.

Catalog rows (see docs/INTERNAL_API_INVENTORY.md):
- GET  /REST/site (read-only, the site list the UI fixture checks)
- POST /REST/site/config/{siteId}/location
- GET  /REST/site/{siteId}/location/tree
- GET  /REST/site/{siteId}/deletelocation/{locationId}

Writes: every name starts with "AutoTest ". The cleanup fixture removes
what a test made and fails with the leftover names when it cannot.
"""
import time

import pytest

NAME_PREFIX = "AutoTest "


def _new_name() -> str:
    return f"{NAME_PREFIX}API Location {time.strftime('%H%M%S')}"


@pytest.fixture
def location_cleanup(location_api, data_site_id):
    """Names of the locations a test created. Teardown deletes what still exists."""
    names = []
    yield names
    if not names:
        return
    tree = location_api.get_location_tree(data_site_id)
    leftover = []
    for name in names:
        node = location_api.find_location(tree, name)
        if node is None:
            continue  # the test deleted it
        location_api.delete_location(data_site_id, node["location"]["id"])
        if location_api.find_location(location_api.get_location_tree(data_site_id), name):
            leftover.append(name)
    if leftover:
        pytest.fail(
            f"Locations still on site {data_site_id} after deletelocation: {leftover}. "
            f"Delete them by hand in Admin > Sites.")


def _create(location_api, site_id, channel_id, cleanup):
    """Create a throwaway location and return (name, tree node)."""
    name = _new_name()
    cleanup.append(name)
    r = location_api.create_location(site_id, name, [channel_id])
    assert r.status_code == 200, f"Location create answered {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("code") == 200, f"Unexpected code: {body.get('code')}, body: {str(body)[:300]}"
    assert body.get("status") == 2007, f"Expected status 2007 (applied), got {body.get('status')}"
    node = location_api.find_location(location_api.get_location_tree(site_id), name)
    assert node is not None, f"The create answered OK but location/tree does not list '{name}'"
    return name, node


@pytest.mark.api
@pytest.mark.smoke
def test_site_list_names_the_data_site(user_api, data_site, data_site_id):
    """GET /REST/site lists the data site with an integer siteId and its name.

    Read-only. The UI suite's `api` fixture reads this list to check that
    TEST_SITE_ID is the site test_site_name names.
    """
    r = user_api.get("/REST/site")
    r.raise_for_status()
    body = r.json()
    assert body.get("code") == 200, f"Unexpected code: {body.get('code')}"
    rows = body.get("result") or []
    match = [s for s in rows if s.get("siteId") == data_site_id]
    assert match, f"GET /REST/site does not list siteId {data_site_id}: {[s.get('name') for s in rows]}"
    assert match[0].get("name") == data_site["name"], f"Site {data_site_id} is named {match[0].get('name')!r}"


@pytest.mark.api
@pytest.mark.smoke
def test_create_location_lists_in_tree(
        data_write_gate, location_api, data_site_id, data_channel_id, location_cleanup):
    """POST site/config/{site}/location answers 2007 and location/tree then lists the group.

    The create result echoes the request without an id. The id only comes
    from the tree read, which is what the Admin > Sites Groups dropdown
    reads.
    """
    name = _new_name()
    location_cleanup.append(name)
    r = location_api.create_location(data_site_id, name, [data_channel_id])
    assert r.status_code == 200, f"Location create answered {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("code") == 200, f"Unexpected code: {body.get('code')}, body: {str(body)[:300]}"
    assert body.get("status") == 2007, f"Expected status 2007 (applied), got {body.get('status')}"
    echoed = body["result"][0]
    assert echoed == {"name": name, "siteId": data_site_id, "channelList": [data_channel_id]}, (
        f"The create result no longer echoes the request: {echoed}")
    assert "id" not in echoed, "The create result now carries an id. Update the UI fixture."

    node = location_api.find_location(location_api.get_location_tree(data_site_id), name)
    assert node is not None, f"The create answered OK but location/tree does not list '{name}'"
    assert isinstance(node["location"].get("id"), int), f"Tree node has no integer id: {node['location']}"
    assert [c.get("id") for c in node.get("channel", [])] == [data_channel_id], (
        f"Group '{name}' holds channels {[c.get('id') for c in node.get('channel', [])]}, "
        f"expected [{data_channel_id}]")


@pytest.mark.api
@pytest.mark.smoke
def test_delete_location_removes_it_and_a_second_delete_answers_1006(
        data_write_gate, location_api, data_site_id, data_channel_id, location_cleanup):
    """GET deletelocation/{id} answers [true] and drops the group. A repeat answers 400 / 1006.

    This also pins which envelope field to trust. On success `code` is 200
    and `status` is the API status (2000). On the error `code` is the API
    code (1006) and `status` holds the HTTP status (400). The `message`
    text is not a signal (docs/API_SURFACES.md, "The response envelope").
    """
    name, node = _create(location_api, data_site_id, data_channel_id, location_cleanup)
    location_id = node["location"]["id"]

    r = location_api.delete_location(data_site_id, location_id)
    assert r.status_code == 200, f"Location delete answered {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("code") == 200, f"Unexpected code: {body.get('code')}, body: {str(body)[:300]}"
    assert body.get("result") == [True], f"Expected result [true], got {body.get('result')}"
    assert location_api.find_location(location_api.get_location_tree(data_site_id), name) is None, (
        f"location/tree still lists '{name}' after deletelocation")

    again = location_api.delete_location(data_site_id, location_id)
    assert again.status_code == 400, (
        f"A second delete answered HTTP {again.status_code}, expected 400: {again.text[:300]}")
    body = again.json()
    assert body.get("code") == 1006, f"Expected code 1006 (no record), got {body.get('code')}: {body}"
    assert body.get("status") == 400, f"On an error `status` holds the HTTP status, got {body.get('status')}"
