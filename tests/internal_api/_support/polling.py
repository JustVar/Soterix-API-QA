"""
Generic poll-until-terminal-state helper for the VMS's async job endpoints
(clip export, archive download, multi-clip export...) which all follow the
same start -> repeatedly check status -> COMPLETED/FAILED shape.
"""
import logging
import time

logger = logging.getLogger(__name__)


def poll_until_terminal(poll_fn, terminal_statuses, timeout_sec, interval_sec, description=""):
    """
    Calls `poll_fn()` repeatedly (each call should perform one status check
    and return the parsed status item dict) until its "status" field is one
    of `terminal_statuses`, or `timeout_sec` elapses.

    Returns (final_item, history) where history is a list of
    (elapsed_sec, item) tuples for every poll - used to build a detailed
    failure message when a job never reaches a terminal state.
    """
    t0 = time.time()
    history = []
    item = None
    while time.time() - t0 < timeout_sec:
        item = poll_fn()
        elapsed = time.time() - t0
        history.append((elapsed, item))
        logger.info(
            "%s poll at t=%.0fs: status=%s percentage=%s",
            description, elapsed, item.get("status"), item.get("percentage"),
        )
        if item.get("status") in terminal_statuses:
            return item, history
        time.sleep(interval_sec)
    return item, history
