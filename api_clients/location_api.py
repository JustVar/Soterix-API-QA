"""Camera group (location) API client.

A "camera group" in Admin > Sites is a location in the API. The API also
has groups (addgroup, grouptree, deletegroup), but the Admin UI never
reads them. Verified on QA 2026-08-24, see docs/INTERNAL_API_INVENTORY.md.
"""
from __future__ import annotations

from typing import Any

import requests

from .base_api_client import BaseAPIClient


class LocationAPI(BaseAPIClient):
    def create_location(self, site_id: int, name: str, channel_ids: list[int]) -> requests.Response:
        """POST /REST/site/config/{siteId}/location.

        A success answers code 200 and status 2007 "Successfully Applied!".
        The result echoes the request without an id. Read the tree to get
        the id (find_location).
        """
        payload = {"name": name, "siteId": site_id, "channelList": list(channel_ids)}
        return self.post(f"/REST/site/config/{site_id}/location", json=payload)

    def get_location_tree(self, site_id: int) -> list[dict[str, Any]]:
        """GET /REST/site/{siteId}/location/tree, the envelope's result.

        Each node is {"location": {"id", "name"}, "channel": [VChannel, ...]}.
        This is what Admin > Sites reads for its Groups dropdown. A camera
        can sit in several locations.
        """
        r = self.get(f"/REST/site/{site_id}/location/tree")
        r.raise_for_status()
        return r.json().get("result") or []

    def delete_location(self, site_id: int, location_id: int) -> requests.Response:
        """GET /REST/site/{siteId}/deletelocation/{locationId}.

        A success answers result [true]. A second delete of the same id
        answers HTTP 400 with code 1006 "Database: no record found!".
        """
        return self.get(f"/REST/site/{site_id}/deletelocation/{location_id}")

    @staticmethod
    def find_location(tree: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
        """The tree node whose location is called `name`, or None.

        With 2 nodes of the same name (a stale leftover) the one with the
        highest id wins.
        """
        matches = [n for n in tree if (n.get("location") or {}).get("name") == name]
        if not matches:
            return None
        return max(matches, key=lambda n: n["location"]["id"])
