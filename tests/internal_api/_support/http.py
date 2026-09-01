"""
Shared HTTP call wrapper so every test suite (smoke, functional, security,
performance...) logs and times requests the same way instead of
reimplementing elapsed-time tracking per file.
"""
import logging

logger = logging.getLogger(__name__)


def timed_request(session, method: str, url: str, **kwargs):
    """
    Sends one HTTP request through `session`, logs method/url/status/elapsed
    at INFO level, and returns (response, elapsed_ms) so callers can both
    assert on the response and surface timing in reports.
    """
    resp = session.request(method, url, **kwargs)
    elapsed_ms = resp.elapsed.total_seconds() * 1000
    logger.info("%s %s -> %s in %.0f ms", method.upper(), url, resp.status_code, elapsed_ms)
    return resp, elapsed_ms
