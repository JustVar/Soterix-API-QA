"""Compatibility shim. The code lives in soterix-qa-shared.

Import this path as before; it resolves to soterix_qa_shared.reporting.run_archive.
See that repo's docs/RULES.md for why the shim has this exact shape.

Registered in conftest.py (pytest_plugins) so every run of this repo keeps
its evidence under reports/runs/<run>/: run.html, summary.json with
per-test durations, the index, and the live record the archive pages show
while a run is in progress. RUN_ARCHIVE=off turns it off.
"""
import sys

try:
    from soterix_qa_shared.reporting import run_archive as _mod
except ModuleNotFoundError as exc:
    if (exc.name or "").split(".")[0] != "soterix_qa_shared":
        raise                    # a dependency of the package is missing
    raise ModuleNotFoundError(
        "soterix-qa-shared is not installed. "
        "Run: python -m pip install -r requirements.txt"
    ) from None

sys.modules[__name__] = _mod
