"""Clip bookmark API client.

A bookmark DELETE is a soft delete: the row stays in the site list with
`deletedAt` set. Verified on QA 2026-08-24, see docs/INTERNAL_API_INVENTORY.md.
"""
from __future__ import annotations

import time
from typing import Any

import requests

from .base_api_client import BaseAPIClient


class BookmarkAPI(BaseAPIClient):
    def create_bookmark(
        self, site_id: int, camera_id: int, comment: str, snap: bytes,
        timestamp_ms: int | None = None, retention_days: int = 1,
        snap_name: str = "snap.png", snap_type: str = "image/png",
    ) -> requests.Response:
        """POST /REST/clipbookmark with query parameters and a multipart `snap` part.

        The `snap` file part is required. A success answers code 200 and
        status 2005 "Successfully created!" with result[0].bookmarkId.
        """
        params = {
            "timestamp": timestamp_ms or int(time.time() * 1000),
            "siteId": site_id,
            "cameraId": camera_id,
            "retentionDays": retention_days,
            "comment": comment,
        }
        return self.post(
            "/REST/clipbookmark", params=params,
            files={"snap": (snap_name, snap, snap_type)})

    def list_bookmarks(self, site_id: int) -> list[dict[str, Any]]:
        """GET /REST/clipbookmark/{siteId}, the envelope's result.

        Soft-deleted rows are included. A live row holds deletedAt -1.
        """
        r = self.get(f"/REST/clipbookmark/{site_id}")
        r.raise_for_status()
        return r.json().get("result") or []

    def delete_bookmark(self, bookmark_id: int) -> requests.Response:
        """DELETE /REST/clipbookmark/{bookmarkId}.

        Answers status 2006 "Successfully deleted!". The row stays in the
        list with deletedAt set to a timestamp (soft delete).
        """
        return self.delete(f"/REST/clipbookmark/{bookmark_id}")

    @staticmethod
    def find_bookmark(rows: list[dict[str, Any]], bookmark_id: int) -> dict[str, Any] | None:
        for row in rows:
            if row.get("bookmarkId") == bookmark_id:
                return row
        return None

    @staticmethod
    def is_soft_deleted(row: dict[str, Any]) -> bool:
        """True when deletedAt holds a timestamp.

        -1 means live. A plain truthiness check reads -1 as deleted.
        """
        return (row.get("deletedAt") or 0) > 0
