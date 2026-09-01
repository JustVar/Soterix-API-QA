"""
HTML-report helpers shared across test suites so every suite's pytest-html
report renders response bodies/timings the same collapsible way.
"""
import html
import json

import pytest_html


def inline_block(label: str, content: str, open_by_default: bool = False):
    """
    Builds a collapsible <details> block for pytest-html's 'html' extra
    format, which renders INLINE directly in the report row.

    Deliberately NOT using pytest_html.extras.text()/.json() here: with
    --self-contained-html those render as a link to a data: URI, and modern
    Chrome/Edge silently block top-level navigation to data: URLs from
    file:// pages - the link shows up but clicking it does nothing. The
    'html' format type is handled differently by pytest-html's own frontend
    JS and gets inserted inline, so it always works regardless of browser
    data: URL policy.
    """
    escaped = html.escape(content)
    open_attr = " open" if open_by_default else ""
    return pytest_html.extras.html(
        f"<details{open_attr} style='margin:4px 0;'>"
        f"<summary style='cursor:pointer;font-weight:600;'>{html.escape(label)}</summary>"
        f"<pre style='white-space:pre-wrap;word-break:break-word;"
        f"background:#f5f5f5;padding:8px;border-radius:4px;font-size:12px;'>{escaped}</pre>"
        f"</details>"
    )


def format_response_for_report(url: str, resp) -> str:
    """
    Builds a readable block for the report: request URL, status, headers of
    interest, and the response body - pretty-printed JSON where possible,
    truncated so huge or binary bodies don't bloat the HTML file.
    """
    MAX_BODY_CHARS = 5000
    content_type = resp.headers.get("Content-Type", "")

    lines = [
        f"URL: {url}",
        f"Status: {resp.status_code}",
        f"Content-Type: {content_type or '(none)'}",
        f"Content-Length: {resp.headers.get('Content-Length', len(resp.content))}",
        "",
    ]

    if "json" in content_type:
        try:
            pretty = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except ValueError:
            pretty = resp.text
        body = pretty
    elif "text" in content_type or content_type == "":
        body = resp.text
    else:
        body = f"[binary content, {len(resp.content)} bytes - not displayed]"

    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + f"\n... [truncated, {len(body)} total chars]"

    lines.append(body)
    return "\n".join(lines)


def truncate_large_strings(obj, max_len: int = 200):
    """
    Recursively truncates long string values (e.g. base64 profile pictures)
    so dumping a full response into the HTML report doesn't balloon its
    size or leak large binary blobs into a text report.
    """
    if isinstance(obj, dict):
        return {k: truncate_large_strings(v, max_len) for k, v in obj.items()}
    if isinstance(obj, list):
        return [truncate_large_strings(v, max_len) for v in obj]
    if isinstance(obj, str) and len(obj) > max_len:
        return obj[:max_len] + f"... [truncated, {len(obj)} total chars]"
    return obj
