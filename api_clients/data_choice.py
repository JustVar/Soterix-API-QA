"""The site and the camera the writing tests use, chosen by name.

config/env/ may leave test_site_name and test_camera_name blank. Then
the run reads the choice from the server at session start:

- the site is the first site by name that the account can see, with
  status REGISTERED and at least 1 camera in its location tree.
- the camera is the first camera by name of that site.

By name, never by the order the server answers in. That order changes
when a camera is added, which would re-point every run without a trace.
A configured name is checked, never replaced. A stale name raises
LookupError with the names the account sees, so a rename is one edit in
config/env/.

The "All Cameras" location (id 1) of location/tree holds every camera of
a site. A camera can sit in other locations too, so the cameras come
from that node when it exists and from the union of the nodes when not.
A channel whose isChannelDeleted is truthy is left out.

Channel records carry the camera's own credentials (username, password).
Only ids and names leave this module.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

ALL_CAMERAS_LOCATION = 1
REGISTERED = "REGISTERED"


def _key(name: str) -> str:
    return name.strip().casefold()


def sites_by_name(sites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The site rows that carry a name and a siteId, sorted by name."""
    rows = [s for s in sites
            if isinstance(s, dict) and str(s.get("name") or "").strip() and s.get("siteId") is not None]
    return sorted(rows, key=lambda s: (_key(str(s["name"])), int(s["siteId"])))


def cameras_by_name(tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """[{id, name}] of a site's live cameras, from its location tree, sorted by name.

    Read from the All Cameras node when the tree has one, else from every
    node. A deleted channel or one without a name is left out. A camera
    in 2 locations appears once.
    """
    nodes = [n for n in tree
             if int((n.get("location") or {}).get("id") or 0) == ALL_CAMERAS_LOCATION] or tree
    cameras: dict[int, str] = {}
    for node in nodes:
        for channel in node.get("channel") or []:
            name = str(channel.get("name") or "").strip()
            if channel.get("isChannelDeleted") or not name or channel.get("id") is None:
                continue
            cameras.setdefault(int(channel["id"]), name)
    return sorted(({"id": i, "name": n} for i, n in cameras.items()),
                  key=lambda c: (_key(c["name"]), c["id"]))


def choose_site(sites: list[dict[str, Any]], cameras_of: Callable[[int], list],
                configured: str | None = None) -> dict[str, Any]:
    """The site row the writing tests use.

    `sites` is what /REST/site/user/{email} answered. `cameras_of(site_id)`
    is what cameras_by_name answers for a site. It is called only while no
    name is configured. A configured name matches case-insensitively.
    """
    rows = sites_by_name(sites)
    names = [str(s["name"]) for s in rows]
    wanted = (configured or "").strip()
    if wanted:
        for row in rows:
            if _key(str(row["name"])) == _key(wanted):
                return row
        raise LookupError(
            f"No site named '{wanted}' for this account. Sites: {names}. "
            f"Fix test_site_name in config/env/, or leave it blank to use "
            f"the first site by name with a camera.")
    for row in rows:
        status = str(row.get("status") or "")
        if status and status != REGISTERED:
            continue
        if cameras_of(int(row["siteId"])):
            return row
    raise LookupError(
        f"No REGISTERED site of this account has a camera. Sites: {names}. "
        f"Set test_site_name in config/env/ to a site with a camera.")


def choose_camera(cameras: list[dict[str, Any]], site_name: str,
                  configured: str | None = None) -> dict[str, Any]:
    """The camera {id, name} the writing tests use on the chosen site.

    `cameras` is what cameras_by_name answered for that site. A configured
    name matches case-insensitively.
    """
    names = [c["name"] for c in cameras]
    wanted = (configured or "").strip()
    if wanted:
        for camera in cameras:
            if _key(camera["name"]) == _key(wanted):
                return camera
        raise LookupError(
            f"No camera named '{wanted}' on site '{site_name}'. Cameras: {names}. "
            f"Fix test_camera_name in config/env/ if the tenant renamed it, or "
            f"leave it blank to use the first camera by name.")
    if not cameras:
        raise LookupError(
            f"Site '{site_name}' has no camera. Set test_site_name in config/env/ "
            f"to a site with a camera.")
    return cameras[0]
