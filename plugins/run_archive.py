"""Compatibility shim. The code lives in soterix-qa-shared.

Import this path as before; it resolves to soterix_qa_shared.reporting.run_archive.
See that repo's docs/RULES.md for why the shim has this exact shape.

Registered in conftest.py (pytest_plugins) since 09/11/2026 so this repo's
runs archive under reports/runs/ like the WebApp repo's: run.html, the
per-run summary.json with per-test durations, the index, and the live
record and estimate that the archive pages show while a run is in
progress. Before this the API runs left only the QA Touch upload behind.
"""
import sys

try:
    from soterix_qa_shared.reporting import run_archive as _mod
except ModuleNotFoundError as exc:
    if (exc.name or "").split(".")[0] != "soterix_qa_shared":
        raise                    # a dependency of the package is missing
    raise ModuleNotFoundError(
        "soterix-qa-shared is not installed. "
        "Run: pip install -e ../soterix-qa-shared"
    ) from None

sys.modules[__name__] = _mod
