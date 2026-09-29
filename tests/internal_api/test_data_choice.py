"""The site and the camera the writing tests use when config/env/ names none.

Pins for api_clients/data_choice.py. The rule that matters most: the
choice is by NAME order, never by the order the server answers in, and a
configured name is checked, never replaced. Offline: a made-up site list
and a made-up location tree, no server.
"""
from __future__ import annotations

import pytest

from api_clients import data_choice as d

# The server's order. By name, Anchor Depot comes first but has no camera,
# Beacon Office is the first with one, and Old Yard is not registered.
SITES = [
    {"siteId": 99, "name": "Old Yard", "status": "SUSPENDED"},
    {"siteId": 153, "name": "Anchor Depot", "status": "REGISTERED"},
    {"siteId": 16, "name": "Harbor Gate", "status": "REGISTERED"},
    {"siteId": 17, "name": "Beacon Office", "status": "REGISTERED"},
    {"siteId": None, "name": "no id"},
    {"siteId": 5, "name": ""},
]
TREE_17 = [
    {"location": {"id": 2, "name": "TestGroup1"}, "channel": []},
    {"location": {"id": 1, "name": "All Cameras"},
     "channel": [{"id": 108, "name": "Lobby cam", "username": "u", "password": "p"},
                 {"id": 100, "name": " 01 Yard cam "},
                 {"id": 101, "name": "gate-2"},
                 {"id": 102, "name": "Gone", "isChannelDeleted": 1},
                 {"id": 103, "name": ""}]},
]
TREE_NO_ALL = [
    {"location": {"id": 7, "name": "Left"}, "channel": [{"id": 1, "name": "Z cam"}]},
    {"location": {"id": 8, "name": "Right"},
     "channel": [{"id": 2, "name": "a cam"}, {"id": 1, "name": "Z cam"}]},
]
# What cameras_by_name answers per site.
CAMERAS = {153: [], 99: [{"id": 9, "name": "x"}], 16: [{"id": 1, "name": "a cam"}],
           17: [{"id": 108, "name": "Lobby cam"}]}


def test_sites_are_sorted_by_name_and_need_a_name_and_an_id():
    rows = d.sites_by_name(SITES)
    assert [r["name"] for r in rows] == ["Anchor Depot", "Beacon Office", "Harbor Gate", "Old Yard"]
    assert rows[0]["siteId"] == 153


def test_cameras_come_from_all_cameras_sorted_without_deleted_or_blank_ones():
    """Sorted case-insensitively and stripped. The server's order changes when
    a camera is added, and a name with spaces round it is the same camera."""
    assert d.cameras_by_name(TREE_17) == [
        {"id": 100, "name": "01 Yard cam"},
        {"id": 101, "name": "gate-2"},
        {"id": 108, "name": "Lobby cam"}]


def test_a_tree_without_all_cameras_gives_the_union_of_its_locations_once():
    assert d.cameras_by_name(TREE_NO_ALL) == [{"id": 2, "name": "a cam"}, {"id": 1, "name": "Z cam"}]


def test_only_ids_and_names_leave_the_module():
    """Channel records carry the camera's own credentials."""
    for camera in d.cameras_by_name(TREE_17):
        assert set(camera) == {"id", "name"}


def test_the_blank_config_uses_the_first_registered_site_by_name_that_has_a_camera():
    """By name: Anchor Depot has no camera, so Beacon Office. By the server's
    order it would have been Harbor Gate."""
    site = d.choose_site(SITES, CAMERAS.__getitem__)
    assert (site["siteId"], site["name"]) == (17, "Beacon Office")


def test_the_server_order_does_not_change_the_choice():
    assert d.choose_site(list(reversed(SITES)), CAMERAS.__getitem__)["siteId"] == 17
    reversed_tree = [dict(node, channel=list(reversed(node.get("channel") or [])))
                     for node in reversed(TREE_17)]
    assert d.choose_camera(d.cameras_by_name(reversed_tree), "Site A")["id"] == 100


def test_a_configured_site_is_checked_never_replaced():
    def never(site_id):
        raise AssertionError("a configured name must not read any tree")

    assert d.choose_site(SITES, never, configured=" beacon office ")["siteId"] == 17
    with pytest.raises(LookupError) as err:
        d.choose_site(SITES, never, configured="Beacon Offic")
    assert "Harbor Gate" in str(err.value), "the names the account sees, so the fix is one edit"
    assert "test_site_name" in str(err.value)


def test_no_site_with_a_camera_is_a_lookup_error_that_lists_the_sites():
    with pytest.raises(LookupError) as err:
        d.choose_site(SITES, lambda site_id: [])
    assert "Anchor Depot" in str(err.value)
    assert "test_site_name" in str(err.value)


def test_the_blank_config_uses_the_first_camera_by_name():
    assert d.choose_camera(d.cameras_by_name(TREE_17), "Site A") == {"id": 100, "name": "01 Yard cam"}


def test_a_configured_camera_is_checked_never_replaced():
    cameras = d.cameras_by_name(TREE_17)
    assert d.choose_camera(cameras, "Site A", configured=" lobby cam ")["id"] == 108
    with pytest.raises(LookupError) as err:
        d.choose_camera(cameras, "Site A", configured="Lobby cam2")
    assert "gate-2" in str(err.value)
    assert "test_camera_name" in str(err.value)
    with pytest.raises(LookupError):
        d.choose_camera(cameras, "Site A", configured="Gone")  # a deleted channel is not a camera
    with pytest.raises(LookupError) as err:
        d.choose_camera([], "Site A")
    assert "Site A" in str(err.value)
