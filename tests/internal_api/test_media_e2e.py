"""
Media library E2E tests, one scenario per test function, each following
an explicit Action -> Validate pattern:

    Add media -> Validate media -> <feature actions with validate after
    each> -> Delete media -> Validate media

Every test creates its OWN independent media entry (via addMedia) from a
SHARED completed export job (the `exported_job` fixture, module-scoped) -
confirmed via recon that the same completed export can back multiple
independent addMedia calls, so we only pay for one real clip export for
this whole module instead of one per test. The export lifecycle itself is
already covered by test_clip_export_e2e.py; these tests treat a completed
export as a precondition, not something under test here.

WARNING: test_media_share sends a REAL email to config.MEDIA_SHARE_TEST_EMAIL
on every run. That address was explicitly provided for this purpose - don't
repoint it at anyone who hasn't agreed to receive it.

Confirmed request shapes / quirks (several do NOT match a naive reading of
the OpenAPI spec - confirmed via direct recon and/or a captured real
browser request from the product UI):
  - searchMedia/getMediaCount: the UI actually calls searchMediaEnc
    (/REST/media/search/enc), and filter criteria go inside a nested
    "mediaData" object, not top-level VMedia fields. getMediaCount uses
    the same nested shape.
  - deleteMediaById is a SOFT delete: getMediaById still returns 200
    afterward, with "isDeleted" flipped to 1 - there is no hard 404.
  - getMediaCount does NOT exclude soft-deleted media (confirmed: count
    stayed identical before/after a delete), unlike searchMediaEnc, which
    DOES exclude them. Don't assert count decreases after a delete.
  - createLinkMedia/shareMedia: "mediadata" only needs {"mediaId": ...},
    not a full ArchiveDownloadModel.
  - addMediaGroup requires a NON-EMPTY "mediaIds" list at creation time -
    you can't create an empty group and add media after.
  - addMediaToGroup/removeMediaFromGroup take a plural "mediaIds" list,
    not a singular "mediaId".
  - getMediaThumbnail returns JSON with a "content" byte-array field, not
    a raw binary image stream (unlike streamMedia, which IS raw binary).
  - addMedia triggers ASYNC post-processing (copying the file into Media
    storage) whose progress is exposed the SAME way as the clip export job
    itself: getMediaById's nested "mediaData.status" field goes
    INPROGRESS -> COMPLETED. Confirmed via recon this takes anywhere from
    ~4s to 30s+ depending on backend load - NOT a fixed short race. Tests
    that touch stream/thumbnail/search right after creation poll this
    field (_wait_for_media_processed) instead of guessing at a fixed
    retry delay, which was tried first and proved unreliable.
  - deleteMediaById behavior differs by type: regular media clips are a
    SOFT delete (getMediaById still 200s, "isDeleted" flips to 1) but
    media GROUPS are a HARD delete (getMediaById returns 200 with an
    EMPTY result list afterward). _validate_media takes a `hard_delete`
    flag to check the right thing for each.
"""
import time

import pytest

from ._support import config
from ._support.http import timed_request
from ._support.polling import poll_until_terminal
from ._support.reporting import inline_block

pytestmark = [pytest.mark.e2e, pytest.mark.internal, pytest.mark.env_qa, pytest.mark.slow]


@pytest.fixture(autouse=True)
def _require_writes(data_write_gate):
    """Gate every test in this file behind allow_write and allow_delete."""

EXPORT_POLL_INTERVAL_SEC = 6
MEDIA_PROCESSING_TIMEOUT_SEC = 60
MEDIA_PROCESSING_POLL_INTERVAL_SEC = 3


MEDIA_BASE = f"{config.BASE_URL}{config.API_PREFIX_ROOT}/media"
STREAM_BASE = f"{config.BASE_URL}{config.API_PREFIX_ROOT}/stream/media"
MEDIAGROUP_BASE = f"{config.BASE_URL}{config.API_PREFIX_ROOT}/mediagroup"


@pytest.fixture(scope="module")
def exported_job(authed_session, discovery_context, recorded_clip_window):
    """One real completed clip export, shared by every test in this module."""
    site_id = discovery_context["siteid"]
    channel_id = recorded_clip_window["channel_id"]
    start_ts = recorded_clip_window["start_ts"]
    end_ts = min(
        recorded_clip_window["end_ts"],
        start_ts + config.CLIP_EXPORT_DURATION_SECONDS * 1000,
    )
    clip_base = f"{config.BASE_URL}{config.API_PREFIX_SITE}/multi/export/clip"

    export_payload = [{
        "siteId": site_id, "channelId": channel_id,
        "startTimestamp": start_ts, "endTimestamp": end_ts,
        "format": "MP4", "filename": "media-e2e-test-clip",
        "includeAudio": True, "notes": "", "copyToMedia": False, "dasEventId": "",
    }]
    resp, _ = timed_request(authed_session, "POST", f"{clip_base}/generation/start", json=export_payload, timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"startMultiClipExport failed: {resp.status_code} {resp.text[:300]}"
    job = resp.json()["result"][0]

    def _poll():
        nonlocal job
        resp, _ = timed_request(authed_session, "POST", f"{clip_base}/status", json=job, timeout=config.DEFAULT_TIMEOUT)
        assert resp.status_code == 200, f"multiClipExportStatus failed: {resp.status_code} {resp.text[:300]}"
        result = resp.json().get("result") or [{}]
        item = result[0] if isinstance(result, list) and result else result
        job = item if item else job
        return item

    final, _ = poll_until_terminal(
        _poll, terminal_statuses=("COMPLETED", "FAILED"),
        timeout_sec=config.CLIP_EXPORT_TIMEOUT_SECONDS, interval_sec=EXPORT_POLL_INTERVAL_SEC,
        description="media E2E prerequisite export",
    )
    assert final.get("status") == "COMPLETED", f"Prerequisite export never completed: {final}"
    return final


# ---------------------------------------------------------------------------
# Shared Add / Validate / Delete steps - every test starts and ends with
# these, so they're factored out rather than copy-pasted 11 times.
# ---------------------------------------------------------------------------

def _add_media(authed_session, job, extras) -> int:
    """Add media."""
    resp, _ = timed_request(authed_session, "POST", MEDIA_BASE, json=[job], timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"addMedia failed: {resp.status_code} {resp.text[:300]}"
    media_id = resp.json()["result"][0]["id"]
    extras.append(inline_block("Add media", f"mediaId={media_id}"))
    return media_id


def _validate_media(authed_session, media_id, extras, label="Validate media", expect_deleted=False, hard_delete=False):
    """
    Validate media: confirm getMediaById reflects the expected active/
    deleted state. Regular media clips soft-delete (isDeleted flips to 1,
    record still fetchable); media GROUPS hard-delete (result list comes
    back empty) - pass hard_delete=True for those.

    When checking for the ACTIVE state (expect_deleted=False - i.e. right
    after _add_media), a brief empty result is itself a known race: confirmed
    via recon that getMediaById can momentarily 200 with an empty result
    immediately after addMedia's own 200, before the record is fully
    visible. Retry a few times rather than treating that as a hard failure.
    """
    result = []
    for attempt in range(1, 6):
        resp, _ = timed_request(authed_session, "GET", f"{MEDIA_BASE}/{media_id}", timeout=config.DEFAULT_TIMEOUT)
        assert resp.status_code == 200, f"getMediaById failed: {resp.status_code} {resp.text[:300]}"
        result = resp.json().get("result") or []
        if result or expect_deleted:
            break
        if attempt < 5:
            time.sleep(2)

    if expect_deleted and hard_delete:
        assert not result, f"Expected media {media_id} to be hard-deleted (empty result), got: {result}"
        extras.append(inline_block(label, "result=[] (hard-deleted)"))
        return {}

    assert result, f"getMediaById returned an empty result for media {media_id} (expected active) after 5 retries"
    body = result[0]
    assert body.get("mediaId") == media_id, f"getMediaById returned wrong media: {body}"
    is_deleted = body.get("isDeleted", 0)
    if expect_deleted:
        assert is_deleted == 1, f"Expected media {media_id} to be marked deleted, got isDeleted={is_deleted}"
    else:
        assert is_deleted == 0, f"Expected media {media_id} to be active, got isDeleted={is_deleted}"
    extras.append(inline_block(label, str(body)[:800]))
    return body


def _delete_media(authed_session, media_id, extras):
    """Delete media (soft delete - getMediaById still 200s afterward, see module docstring)."""
    resp, _ = timed_request(authed_session, "DELETE", f"{MEDIA_BASE}/{media_id}", timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"deleteMediaById failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Delete media", f"status={resp.status_code}"))


def _wait_for_media_processed(authed_session, media_id, extras):
    """
    addMedia's file copy is async - poll getMediaById's nested
    "mediaData.status" field (INPROGRESS -> COMPLETED, same pattern as the
    clip export job) until it's done. Call this before any test step that
    depends on the actual file/search-index being ready (stream, thumbnail,
    a search performed immediately after creation) - confirmed via recon
    that this takes anywhere from ~4s to 30s+ depending on backend load,
    so a fixed short retry isn't reliable.
    """
    def _poll():
        resp, _ = timed_request(authed_session, "GET", f"{MEDIA_BASE}/{media_id}", timeout=config.DEFAULT_TIMEOUT)
        assert resp.status_code == 200, f"getMediaById failed: {resp.status_code} {resp.text[:300]}"
        return resp.json()["result"][0].get("mediaData", {})

    final, history = poll_until_terminal(
        _poll, terminal_statuses=("COMPLETED", "FAILED"),
        timeout_sec=MEDIA_PROCESSING_TIMEOUT_SEC, interval_sec=MEDIA_PROCESSING_POLL_INTERVAL_SEC,
        description=f"media {media_id} post-processing",
    )
    assert final.get("status") == "COMPLETED", f"Media {media_id} post-processing never completed: {final}"
    extras.append(inline_block("Media processed", f"mediaId={media_id}, {len(history)} poll(s)"))


# ---------------------------------------------------------------------------
# 1. Add media -> Validate media -> Edit media -> Validate media ->
#    Delete media -> Validate media
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_add_edit_delete(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    resp, _ = timed_request(
        authed_session, "POST", f"{MEDIA_BASE}/{media_id}",
        json={"mediaId": media_id, "mediaName": "e2e-renamed-media", "description": "Updated by E2E test"},
        timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"updateMediaPOST failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Edit media", f"status={resp.status_code}"))

    body = _validate_media(authed_session, media_id, extras, label="Validate media (after edit)")
    assert body.get("mediaName") == "e2e-renamed-media", f"mediaName did not persist: {body.get('mediaName')!r}"
    assert body.get("description") == "Updated by E2E test", f"description did not persist: {body.get('description')!r}"

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 2. Add media -> Validate media -> Add tag -> Validate tag -> Delete tag ->
#    Validate tag -> Delete media -> Validate media
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_tag(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    resp, _ = timed_request(
        authed_session, "POST", f"{MEDIA_BASE}/addtag",
        json={"mediaId": media_id, "tagList": ["e2e-test-tag"]}, timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"addMediaTag failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Add tag", "tag=e2e-test-tag"))

    body = _validate_media(authed_session, media_id, extras, label="Validate tag (present)")
    assert "e2e-test-tag" in body.get("tagList", []), f"Tag did not persist: {body.get('tagList')}"

    resp, _ = timed_request(
        authed_session, "DELETE", f"{MEDIA_BASE}/removetag/{media_id}/e2e-test-tag", timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"removeMediaTag failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Delete tag", "tag=e2e-test-tag"))

    body = _validate_media(authed_session, media_id, extras, label="Validate tag (removed)")
    assert "e2e-test-tag" not in body.get("tagList", []), f"Tag was not removed: {body.get('tagList')}"

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 3. Add media -> Validate media -> Add comment -> Validate comment ->
#    Delete media -> Validate media
#    (no removeComment endpoint exists, so this one has no delete-comment step)
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_comment(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    baseline = _validate_media(authed_session, media_id, extras)
    baseline_activity_count = len(baseline.get("mediaActivities", []))

    resp, _ = timed_request(
        authed_session, "POST", f"{MEDIA_BASE}/comment",
        json={"mediaId": media_id, "comments": [{"description": "e2e test comment"}]},
        timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"addMediaComment failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Add comment", "e2e test comment"))

    # Verified effect is a new mediaActivities log entry (never confirmed the
    # "comments" field itself stores the text separately - see module docstring).
    body = _validate_media(authed_session, media_id, extras, label="Validate comment")
    assert len(body.get("mediaActivities", [])) > baseline_activity_count, (
        "Expected addMediaComment to add an activity log entry, count didn't increase"
    )

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 4. Add media -> Validate media -> Enable vault -> Validate vault ->
#    Disable vault -> Validate vault -> Delete media -> Validate media
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_vault(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    resp, _ = timed_request(
        authed_session, "PUT", f"{MEDIA_BASE}/vault/{media_id}",
        json={"mediaId": media_id, "vault": 1}, timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"toggleVault (on) failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Enable vault", "vault=1"))

    body = _validate_media(authed_session, media_id, extras, label="Validate vault (enabled)")
    assert body.get("vault") == 1, f"Vault flag did not reflect as set: {body.get('vault')}"

    resp, _ = timed_request(
        authed_session, "PUT", f"{MEDIA_BASE}/vault/{media_id}",
        json={"mediaId": media_id, "vault": 0}, timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"toggleVault (off) failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Disable vault", "vault=0"))

    body = _validate_media(authed_session, media_id, extras, label="Validate vault (disabled)")
    assert body.get("vault") == 0, f"Vault flag did not reflect as cleared: {body.get('vault')}"

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 5. Add media -> Validate media -> Get thumbnail -> Validate thumbnail ->
#    Delete media -> Validate media
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_thumbnail(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    _wait_for_media_processed(authed_session, media_id, extras)

    resp, _ = timed_request(authed_session, "GET", f"{MEDIA_BASE}/thumbnail/{media_id}", timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"getMediaThumbnail failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Get thumbnail", f"status={resp.status_code}"))

    content = resp.json().get("result", {}).get("content", [])
    assert len(content) > 0, "Thumbnail content array is empty"
    extras.append(inline_block("Validate thumbnail", f"content bytes={len(content)}"))

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 6. Add media -> Validate media -> Stream media -> Validate stream ->
#    Delete media -> Validate media
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_stream(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    _wait_for_media_processed(authed_session, media_id, extras)

    resp, _ = timed_request(authed_session, "GET", f"{STREAM_BASE}/{media_id}", timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"streamMedia failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Stream media", f"status={resp.status_code}"))

    assert "video" in resp.headers.get("Content-Type", ""), f"Expected video content-type, got {resp.headers.get('Content-Type')!r}"
    assert len(resp.content) > 0, "Streamed media content is empty"
    extras.append(inline_block("Validate stream", f"content-type={resp.headers.get('Content-Type')} bytes={len(resp.content)}"))

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 7. Add media -> Validate media -> Search media -> Validate found ->
#    Delete media -> Validate media -> Search media -> Validate not found
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_search(authed_session, exported_job, extras):
    site_id_window = exported_job["startTimestamp"], exported_job["endTimestamp"]
    search_body = {
        "mediaData": {"startTimestamp": site_id_window[0] - 3600_000, "endTimestamp": site_id_window[1] + 3600_000},
        "offset": 0, "limit": 50,
    }

    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)
    _wait_for_media_processed(authed_session, media_id, extras)

    resp, _ = timed_request(authed_session, "POST", f"{MEDIA_BASE}/search/enc", json=search_body, timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"searchMediaEnc failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Search media", f"status={resp.status_code}"))

    found_ids = [m.get("mediaId") for m in (resp.json().get("result") or [])]
    assert media_id in found_ids, f"Created media {media_id} not found in search results: {found_ids}"
    extras.append(inline_block("Validate found", f"mediaId {media_id} present in {len(found_ids)} results"))

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)

    resp, _ = timed_request(authed_session, "POST", f"{MEDIA_BASE}/search/enc", json=search_body, timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"searchMediaEnc (post-delete) failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Search media (again)", f"status={resp.status_code}"))

    found_ids_after = [m.get("mediaId") for m in (resp.json().get("result") or [])]
    assert media_id not in found_ids_after, f"Deleted media {media_id} still present in search results: {found_ids_after}"
    extras.append(inline_block("Validate not found", f"mediaId {media_id} absent from {len(found_ids_after)} results"))


# ---------------------------------------------------------------------------
# 8. Add media -> Validate media -> Get count -> Validate count ->
#    Delete media -> Validate media
#    (getMediaCount does NOT exclude soft-deleted media - confirmed via
#    recon - so this does not re-check count after delete; that would
#    assert something known to be false. See module docstring.)
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_count(authed_session, exported_job, extras):
    search_body = {
        "mediaData": {
            "startTimestamp": exported_job["startTimestamp"] - 3600_000,
            "endTimestamp": exported_job["endTimestamp"] + 3600_000,
        },
        "offset": 0, "limit": 50,
    }

    resp, _ = timed_request(authed_session, "POST", f"{MEDIA_BASE}/count", json=search_body, timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"getMediaCount (baseline) failed: {resp.status_code} {resp.text[:300]}"
    baseline_count = resp.json()["result"][0]

    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    resp, _ = timed_request(authed_session, "POST", f"{MEDIA_BASE}/count", json=search_body, timeout=config.DEFAULT_TIMEOUT)
    assert resp.status_code == 200, f"getMediaCount failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Get count", f"status={resp.status_code}"))

    count = resp.json()["result"][0]
    assert count > baseline_count, f"Expected count to increase after addMedia: baseline={baseline_count}, now={count}"
    extras.append(inline_block("Validate count", f"baseline={baseline_count}, after add={count}"))

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 9. Add media -> Validate media -> Create link -> Validate link ->
#    Delete media -> Validate media
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_createlink(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    resp, _ = timed_request(
        authed_session, "POST", f"{MEDIA_BASE}/createlink",
        json=[{
            "mediadata": {"mediaId": media_id},
            "expiryTimeinDays": 1,
            "redirectUrl": f"{config.BASE_URL}/auth/shareLink?uk=",
        }],
        timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"createLinkMedia failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Create link", f"status={resp.status_code}"))

    link = resp.json()["result"][0]
    assert link.get("path"), f"createLinkMedia did not return a link path: {link}"
    extras.append(inline_block("Validate link", str(link)))

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 10. Add media -> Validate media -> Share media -> Validate share ->
#     Delete media -> Validate media
#     REAL EMAIL SENT to config.MEDIA_SHARE_TEST_EMAIL
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_share(authed_session, exported_job, extras):
    if not config.MEDIA_SHARE_TEST_EMAIL:
        pytest.skip("MEDIA_SHARE_TEST_EMAIL is not set; the share step sends a real email. "
                    "Set it in .env to a recipient who agreed to receive it.")
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    resp, _ = timed_request(
        authed_session, "POST", f"{MEDIA_BASE}/share",
        json=[{
            "mediadata": {"mediaId": media_id},
            "emailIds": [config.MEDIA_SHARE_TEST_EMAIL],
            "password": None,
            "notes": "",
            "expiryTimeinDays": 1,
            "redirectUrl": f"{config.BASE_URL}/auth/shareLink?uk=",
            "webhooks": [],
        }],
        timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"shareMedia failed: {resp.status_code} {resp.text[:300]}"
    extras.append(inline_block("Share media (real email sent)", f"status={resp.status_code}"))

    share_result = resp.json()["result"][0]
    assert share_result.get("email") == config.MEDIA_SHARE_TEST_EMAIL, f"shareMedia response email mismatch: {share_result}"
    extras.append(inline_block("Validate share", str(share_result)))

    _delete_media(authed_session, media_id, extras)
    _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)


# ---------------------------------------------------------------------------
# 11. Add media -> Validate media -> Create group -> Validate group ->
#     Remove from group -> Validate group -> Add to group -> Validate group
#     -> Delete group -> Validate group -> Delete media -> Validate media
# ---------------------------------------------------------------------------
@pytest.mark.e2e
def test_media_group(authed_session, exported_job, extras):
    media_id = _add_media(authed_session, exported_job, extras)
    _validate_media(authed_session, media_id, extras)

    group_id = None
    try:
        resp, _ = timed_request(
            authed_session, "POST", MEDIAGROUP_BASE,
            json={"mediaName": "e2e-test-group", "mediaIds": [media_id], "description": "", "tagList": []},
            timeout=config.DEFAULT_TIMEOUT,
        )
        assert resp.status_code == 200, f"addMediaGroup failed: {resp.status_code} {resp.text[:300]}"
        group_id = resp.json()["result"][0]["mediaId"]
        extras.append(inline_block("Create group", f"groupId={group_id}, mediaIds=[{media_id}]"))

        body = _validate_media(authed_session, group_id, extras, label="Validate group (created)")
        assert media_id in body.get("mediaIds", []), f"New group does not contain media {media_id}: {body.get('mediaIds')}"

        resp, _ = timed_request(
            authed_session, "POST", f"{MEDIAGROUP_BASE}/{group_id}/removemedia",
            json={"mediaIds": [media_id]}, timeout=config.DEFAULT_TIMEOUT,
        )
        assert resp.status_code == 200, f"removeMediaFromGroup failed: {resp.status_code} {resp.text[:300]}"
        extras.append(inline_block("Remove from group", f"mediaId={media_id}"))

        body = _validate_media(authed_session, group_id, extras, label="Validate group (media removed)")
        assert media_id not in body.get("mediaIds", []), f"Media {media_id} still in group after removal: {body.get('mediaIds')}"

        resp, _ = timed_request(
            authed_session, "POST", f"{MEDIAGROUP_BASE}/{group_id}/addmedia",
            json={"mediaIds": [media_id]}, timeout=config.DEFAULT_TIMEOUT,
        )
        assert resp.status_code == 200, f"addMediaToGroup failed: {resp.status_code} {resp.text[:300]}"
        extras.append(inline_block("Add to group", f"mediaId={media_id}"))

        body = _validate_media(authed_session, group_id, extras, label="Validate group (media added back)")
        assert media_id in body.get("mediaIds", []), f"Media {media_id} not back in group: {body.get('mediaIds')}"

        deleted_group_id = group_id
        group_id = None  # mark as handled BEFORE the validate call, so `finally` won't retry a delete regardless of outcome
        _delete_media(authed_session, deleted_group_id, extras)
        _validate_media(
            authed_session, deleted_group_id, extras,
            label="Validate group (after delete)", expect_deleted=True, hard_delete=True,
        )

    finally:
        if group_id is not None:
            resp, _ = timed_request(authed_session, "DELETE", f"{MEDIA_BASE}/{group_id}", timeout=config.DEFAULT_TIMEOUT)
            extras.append(inline_block("Cleanup (delete group)", f"status={resp.status_code}"))

        _delete_media(authed_session, media_id, extras)
        _validate_media(authed_session, media_id, extras, label="Validate media (after delete)", expect_deleted=True)
