"""
QA-API-EVT-01 - Events page API smoke (event search)
Spec: qa/Automation_QA.xlsx > Test Mapping > row "QA-API-EVT-01"
Section: I. API
Owner: JV
Deployment: After FT

/REST/site/search/event is the RESULT-RETRIEVAL half of a two-step flow, not a
filter query (verified against the OpenAPI spec and live QA on 2026-08-08):

  1. POST /REST/site/search        submits a search, returns result[0].jobId
  2. POST /REST/site/search/event  pages that job's events with
                                   {jobId, offset, limit}

An earlier version of this test posted siteId/startTime/ruleType filters
directly to step 2 and always got 400 "verify request parameter data type" -
none of those fields exist in its contract (VSearchEventRequest).

Catalog rows:
- POST /REST/site/search (job submission, via SearchAPI)
- POST /REST/site/search/event (job result paging)
"""
import time

import pytest


@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.qa_doc("QA-API-EVT-01")
def test_event_search_returns_results_or_empty(
        search_api, user_api, test_site_id, test_channel_ids):
    """Submit a search job, then page its events; empty eventList is a pass.

    Step 1 mirrors the Search page (person search over the last hour). Step 2
    is what the Events review flow calls to pull the job's events.
    """
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (60 * 60 * 1000)

    submission = search_api.search_person(
        test_site_id, test_channel_ids, start_ts, end_ts)
    result = submission.get("result")
    assert isinstance(result, list) and result, (
        f"Search submission returned no result entry: {str(submission)[:300]}")
    job_id = result[0].get("jobId")
    assert job_id, f"Search submission has no jobId: {str(result[0])[:300]}"

    r = user_api.post(
        "/REST/site/search/event",
        json={"jobId": job_id, "offset": 0, "limit": 25})
    r.raise_for_status()
    body = r.json()
    assert body.get("code") in (200, 2000), (
        f"Unexpected code: {body.get('code')}, body: {str(body)[:400]}")
    assert "result" in body, "Response missing 'result'"
    assert isinstance(body["result"], list), (
        f"Unexpected result type: {type(body['result'])}")
    if body["result"]:
        event_list = body["result"][0].get("eventList")
        assert isinstance(event_list, list), (
            f"result[0].eventList missing or not a list: {str(body['result'][0])[:300]}")
        for event in event_list[:5]:
            assert event.get("jobId") == job_id, (
                "Event belongs to a different job: "
                f"{event.get('jobId')} != {job_id}")


@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.qa_doc("QA-API-EVT-01")
def test_event_search_validates_required_filters(user_api):
    """POST /REST/site/search/event with empty body must NOT return success+data.

    The contract requires a jobId; a missing one must not fall through to some
    default job or the full enterprise event stream.
    """
    r = user_api.post("/REST/site/search/event", json={})
    # The endpoint may legitimately reject with 4xx, or return code != 200 in
    # the body. Either is fine; what we don't want is a 200 with a populated
    # result list (which would mean the jobId requirement isn't enforced).
    if r.status_code == 200:
        body = r.json()
        result = body.get("result")
        if isinstance(result, list):
            assert result == [], (
                "Empty-filter event search returned populated result list; "
                "jobId enforcement may be broken")
