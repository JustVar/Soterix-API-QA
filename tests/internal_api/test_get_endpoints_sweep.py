"""
Positive smoke tests for every safe, read-only (GET) endpoint we could map
from the Swagger/OpenAPI spec.

Design choice: we ONLY auto-run GET endpoints here. POST/PUT/DELETE endpoints
create, mutate, or delete real objects (users, sites, storage configs,
recordings, licenses...) on the server, so firing all of them blindly
would be unsafe. Those get deliberate tests with controlled data
(docs/CONVENTIONS.md).

An unresolved `{placeholder}` (no channel on the site, say) skips rather
than fails - a data gap, not an API bug. The assertion is deliberately
positive-path: HTTP 200 and a parseable JSON body. To add an endpoint,
add a row to data/endpoints.py.
"""
import time as time_module

import pytest

from ._support import config
from ._support.http import timed_request
from ._support.reporting import format_response_for_report, inline_block
from .data.endpoints import GET_ENDPOINTS, KNOWN_LIMITATIONS

pytestmark = [pytest.mark.internal, pytest.mark.api, pytest.mark.env_qa]


# Server-side states that are transient, not real failures - e.g. the VMS
# rebalancing camera load across media servers. Worth a short retry instead
# of an immediate fail, since the condition typically clears in seconds.
TRANSIENT_MESSAGE_FRAGMENTS = [
    "load balancing is going on",
    "please try again",
    "in progress",
]
TRANSIENT_RETRY_ATTEMPTS = 3
TRANSIENT_RETRY_DELAY_SEC = 5


def _build_request(template: str, ctx: dict):
    """
    Fills {placeholders} in the path template from the discovery context.
    Returns (url_path, skip_reason). skip_reason is None if all params
    resolved; otherwise it's a human-readable reason to pytest.skip() with.
    """
    import re

    placeholders = re.findall(r"\{(\w+)}", template)
    values = {}
    for name in placeholders:
        value = ctx.get(name)
        if value is None:
            return None, f"Could not resolve required param '{{{name}}}' from discovery context"
        values[name] = value
    return template.format(**values), None


@pytest.mark.smoke
@pytest.mark.positive
@pytest.mark.parametrize("name,template", GET_ENDPOINTS, ids=[e[0] for e in GET_ENDPOINTS])
def test_get_endpoint_positive(name, template, authed_session, discovery_context, extras):
    """Generic positive check: endpoint responds 200 with valid JSON."""
    if name in KNOWN_LIMITATIONS:
        pytest.skip(KNOWN_LIMITATIONS[name])

    path, skip_reason = _build_request(template, discovery_context)
    if skip_reason:
        pytest.skip(skip_reason)

    url = f"{config.BASE_URL}/v-apiserver{path}"
    timeout = config.DEFAULT_TIMEOUT

    attempts_log = []
    resp = None
    for attempt in range(1, TRANSIENT_RETRY_ATTEMPTS + 1):
        resp, elapsed_ms = timed_request(authed_session, "GET", url, timeout=timeout)
        attempts_log.append(f"Attempt {attempt}: {resp.status_code} in {elapsed_ms:.0f} ms")

        is_transient = resp.status_code == 400 and any(
            fragment in resp.text.lower() for fragment in TRANSIENT_MESSAGE_FRAGMENTS
        )
        if not is_transient:
            break
        if attempt < TRANSIENT_RETRY_ATTEMPTS:
            print(
                f"{name} -> transient state on attempt {attempt}/{TRANSIENT_RETRY_ATTEMPTS} "
                f"({resp.text[:150]}), retrying in {TRANSIENT_RETRY_DELAY_SEC}s..."
            )
            time_module.sleep(TRANSIENT_RETRY_DELAY_SEC)

    # Surface response time directly in the HTML report row (not just logs),
    # and also print it so it's visible in "Captured stdout" as a fallback.
    summary = "\n".join(attempts_log)
    print(f"{name} -> {summary}")
    extras.append(inline_block("Response time", summary))

    # Attach the full response (URL, status, headers, body) too - captured
    # BEFORE the assertion so it still shows up if the test fails.
    extras.append(inline_block("Response", format_response_for_report(url, resp)))

    assert resp.status_code == 200, (
        f"{name} -> GET {path} returned {resp.status_code}: {resp.text[:300]}"
    )

    # Most endpoints return JSON (ResponseVO / VRCSResponse); a few stream
    # binary content (snaps, downloads) - don't fail those on JSON parsing.
    content_type = resp.headers.get("Content-Type", "")
    if "json" in content_type:
        body = resp.json()
        assert isinstance(body, dict), f"{name} -> expected JSON object, got {type(body)}"
