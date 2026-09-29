"""
Clip bookmark API contract

The UI suite (Soterix-WebApp-QA, fixture api_bookmark) seeds bookmarks
through these 3 endpoints. A contract change here breaks that setup, so
these tests pin the exact requests and answers.

Catalog rows (see docs/INTERNAL_API_INVENTORY.md):
- POST   /REST/clipbookmark (query parameters plus a multipart `snap` part)
- GET    /REST/clipbookmark/{siteId}
- DELETE /REST/clipbookmark/{bookmarkId}

Writes: every comment starts with "AutoTest ". DELETE is a soft delete,
so each run leaves one soft-deleted row per test that expires with
retentionDays (1 day here). The API has no hard delete.
"""
import struct
import time
import zlib

import pytest

NAME_PREFIX = "AutoTest "


def tiny_png() -> bytes:
    """A valid 1x1 RGB PNG built from its chunks. The `snap` part must be a real image."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1, 8-bit, RGB
    scanline = b"\x00" + b"\x00\x00\x00"  # filter byte + one black pixel
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(scanline)) + chunk(b"IEND", b""))


def _new_comment() -> str:
    return f"{NAME_PREFIX}API Bookmark {time.strftime('%H%M%S')}"


@pytest.fixture
def bookmark_cleanup(bookmark_api, data_site_id):
    """Ids of the bookmarks a test created. Teardown soft-deletes what is still live."""
    ids = []
    yield ids
    leftover = []
    for bookmark_id in ids:
        row = bookmark_api.find_bookmark(bookmark_api.list_bookmarks(data_site_id), bookmark_id)
        if row is None or bookmark_api.is_soft_deleted(row):
            continue  # the test deleted it
        bookmark_api.delete_bookmark(bookmark_id)
        row = bookmark_api.find_bookmark(bookmark_api.list_bookmarks(data_site_id), bookmark_id)
        if row is not None and not bookmark_api.is_soft_deleted(row):
            leftover.append(bookmark_id)
    if leftover:
        pytest.fail(
            f"Bookmarks still live on site {data_site_id} after DELETE: {leftover}. "
            f"Delete them by hand in the bookmarks panel.")


def _create(bookmark_api, site_id, channel_id, cleanup):
    """Create a throwaway bookmark and return (comment, created row)."""
    comment = _new_comment()
    r = bookmark_api.create_bookmark(site_id, channel_id, comment, tiny_png())
    assert r.status_code == 200, f"Bookmark create answered {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("code") == 200, f"Unexpected code: {body.get('code')}, body: {str(body)[:300]}"
    assert body.get("status") == 2005, f"Expected status 2005 (created), got {body.get('status')}"
    created = body["result"][0]
    assert isinstance(created.get("bookmarkId"), int), f"No integer bookmarkId in {created}"
    cleanup.append(created["bookmarkId"])
    return comment, created


@pytest.mark.api
@pytest.mark.smoke
def test_create_bookmark_lists_live(
        data_write_gate, bookmark_api, data_site_id, data_channel_id, bookmark_cleanup):
    """POST /REST/clipbookmark answers 2005 with the row, and the site list holds it with deletedAt -1."""
    comment, created = _create(bookmark_api, data_site_id, data_channel_id, bookmark_cleanup)
    assert created.get("siteId") == data_site_id
    assert created.get("cameraId") == data_channel_id
    assert created.get("comment") == comment
    assert created.get("deletedAt") == -1, f"A new bookmark must hold deletedAt -1: {created}"

    row = bookmark_api.find_bookmark(bookmark_api.list_bookmarks(data_site_id), created["bookmarkId"])
    assert row is not None, f"POST answered bookmark {created['bookmarkId']} but the site list does not show it"
    assert row.get("deletedAt") == -1, f"Listed row is not live: deletedAt={row.get('deletedAt')}"
    assert not bookmark_api.is_soft_deleted(row)


@pytest.mark.api
@pytest.mark.smoke
def test_delete_bookmark_is_a_soft_delete(
        data_write_gate, bookmark_api, data_site_id, data_channel_id, bookmark_cleanup):
    """DELETE /REST/clipbookmark/{id} answers 2006, and the row stays listed with deletedAt set.

    "Gone" means deletedAt above 0, not absence from the list. A cleanup
    that checks the list for absence never sees its delete land.
    """
    _, created = _create(bookmark_api, data_site_id, data_channel_id, bookmark_cleanup)
    bookmark_id = created["bookmarkId"]

    r = bookmark_api.delete_bookmark(bookmark_id)
    assert r.status_code == 200, f"Bookmark delete answered {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert body.get("code") == 200, f"Unexpected code: {body.get('code')}, body: {str(body)[:300]}"
    assert body.get("status") == 2006, f"Expected status 2006 (deleted), got {body.get('status')}"

    row = bookmark_api.find_bookmark(bookmark_api.list_bookmarks(data_site_id), bookmark_id)
    assert row is not None, (
        f"Bookmark {bookmark_id} left the list after DELETE. The delete is no longer soft. "
        f"Update the UI fixture (bookmark_deleted).")
    assert isinstance(row.get("deletedAt"), int) and row["deletedAt"] > 0, (
        f"Expected a deletedAt timestamp after DELETE, got {row.get('deletedAt')}")
    assert bookmark_api.is_soft_deleted(row)
