"""
E2E test for the clip export lifecycle: start -> poll status until a
terminal state -> download -> verify real binary content.

This exercises the SAME endpoint the product UI actually calls -
POST /REST/site/multi/export/clip/generation/start - not the single-clip
legacy endpoint (/REST/site/export/clip/start). That legacy endpoint was
tried first and reliably failed with "Connection Error with Edge Server"
across 5 separate attempts on 2 environments/3 channels (see memory /
git history for that investigation) - it turned out to simply be the
wrong API surface, not a platform defect. Confirmed via a captured
browser payload that the UI uses the multi-clip endpoint even for a
single clip, which completes correctly in ~16s with a real downloadable
file.

Contract details confirmed via recon (not obvious from the OpenAPI spec
alone - worth keeping here so nobody "fixes" this back to the wrong shape):
  - startMultiClipExport requires the request body to be a JSON ARRAY of
    ArchiveDownloadModel, even for a single clip. A bare object 400s with
    "Required http POST request payload is not found!".
  - format must be uppercase ("MP4") - matches what the UI sends.
  - multiClipExportStatus/stopMultiClipExport take a single (non-array)
    ArchiveDownloadModel - the job object echoed back from start/status.
  - Once COMPLETED, GET /REST/site/multi/export/clip?id={id} (or
    ?downloadKey={key}) returns the real binary video/mp4 content.
"""
import pytest

from ._support import config
from ._support.http import timed_request
from ._support.polling import poll_until_terminal
from ._support.reporting import inline_block

pytestmark = [pytest.mark.e2e, pytest.mark.internal, pytest.mark.env_qa, pytest.mark.slow]


@pytest.fixture(autouse=True)
def _require_writes(data_write_gate):
    """Gate every test in this file behind allow_write and allow_delete."""

EXPORT_POLL_INTERVAL_SEC = 8


@pytest.mark.e2e
def test_clip_export_lifecycle(authed_session, discovery_context, recorded_clip_window, extras):
    """
    Exports a confirmed-real recorded clip end-to-end via the multi-clip
    export flow: start -> poll until COMPLETED -> download -> assert real
    binary video content was returned.
    """
    site_id = discovery_context["siteid"]
    channel_id = recorded_clip_window["channel_id"]
    start_ts = recorded_clip_window["start_ts"]
    # Cap the requested duration (config.CLIP_EXPORT_DURATION_SECONDS, default
    # 60s) instead of exporting the full recorded window - clamped to
    # whatever footage actually exists, so a shorter real clip still works.
    end_ts = min(
        recorded_clip_window["end_ts"],
        start_ts + config.CLIP_EXPORT_DURATION_SECONDS * 1000,
    )

    base_url = f"{config.BASE_URL}{config.API_PREFIX_SITE}/multi/export/clip"

    # --- start (array-wrapped, matching what the UI sends) ---
    start_payload = [{
        "siteId": site_id,
        "channelId": channel_id,
        "startTimestamp": start_ts,
        "endTimestamp": end_ts,
        "format": "MP4",
        "filename": "e2e-test-clip",
        "includeAudio": True,
        "notes": "",
        "copyToMedia": True,
        "dasEventId": "",
    }]
    resp, _ = timed_request(
        authed_session, "POST", f"{base_url}/generation/start",
        json=start_payload, timeout=config.DEFAULT_TIMEOUT,
    )
    assert resp.status_code == 200, f"startMultiClipExport failed: {resp.status_code} {resp.text[:300]}"

    body = resp.json()
    assert body.get("returnValue") == "SUCCESS", f"startMultiClipExport did not return SUCCESS: {body}"
    job = body["result"][0]
    assert job["status"] == "INPROGRESS", f"Expected freshly-started export to be INPROGRESS, got {job['status']!r}"
    export_id = job["id"]
    extras.append(inline_block("Export started", f"id={export_id}\n{start_payload}"))

    try:
        # --- poll until terminal (COMPLETED/FAILED) ---
        def _poll():
            nonlocal job
            resp, _ = timed_request(
                authed_session, "POST", f"{base_url}/status",
                json=job, timeout=config.DEFAULT_TIMEOUT,
            )
            assert resp.status_code == 200, f"multiClipExportStatus failed: {resp.status_code} {resp.text[:300]}"
            result = resp.json().get("result") or [{}]
            item = result[0] if isinstance(result, list) and result else result
            job = item if item else job
            return item

        final, history = poll_until_terminal(
            _poll,
            terminal_statuses=("COMPLETED", "FAILED"),
            timeout_sec=config.CLIP_EXPORT_TIMEOUT_SECONDS,
            interval_sec=EXPORT_POLL_INTERVAL_SEC,
            description=f"multi-clip export id={export_id}",
        )

        history_summary = "\n".join(
            f"t={elapsed:5.0f}s status={item.get('status')} percentage={item.get('percentage')} "
            f"fileSize={item.get('fileSize')} message={item.get('message')!r}"
            for elapsed, item in history
        )
        extras.append(inline_block("Export status history", history_summary))

        if final.get("status") == "FAILED":
            pytest.fail(
                f"Multi-clip export id={export_id} explicitly reported FAILED "
                f"(percentage={final.get('percentage')}, message={final.get('message')!r}).\n{history_summary}"
            )
        assert final.get("status") == "COMPLETED", (
            f"Multi-clip export id={export_id} never reached a terminal state within "
            f"{config.CLIP_EXPORT_TIMEOUT_SECONDS}s (still {final.get('status')!r}).\n{history_summary}"
        )
        assert final.get("fileSize") not in (None, "0 MB"), (
            f"Export reported COMPLETED but file size is still 0 - export id={export_id}: {final}"
        )

        # --- download and verify real binary content ---
        download_resp, _ = timed_request(
            authed_session, "GET", base_url,
            params={"id": export_id}, timeout=config.DEFAULT_TIMEOUT,
        )
        assert download_resp.status_code == 200, (
            f"Downloading completed export id={export_id} failed: "
            f"{download_resp.status_code} {download_resp.text[:300]}"
        )
        content_type = download_resp.headers.get("Content-Type", "")
        assert "video" in content_type, f"Expected a video content-type, got {content_type!r}"
        assert len(download_resp.content) > 0, "Downloaded export file is empty"
        extras.append(inline_block(
            "Download",
            f"status={download_resp.status_code} content-type={content_type} "
            f"bytes={len(download_resp.content)}",
        ))

    finally:
        # Only worth cancelling a job that's still stuck INPROGRESS - a
        # COMPLETED (or already-FAILED) job has nothing left to stop.
        if job.get("status") not in ("COMPLETED", "FAILED"):
            stop_resp, _ = timed_request(
                authed_session, "POST", f"{base_url}/stop",
                json=job, timeout=config.DEFAULT_TIMEOUT,
            )
            extras.append(inline_block(
                "Cleanup (stopMultiClipExport)",
                f"status={stop_resp.status_code}\n{stop_resp.text[:500]}",
            ))
