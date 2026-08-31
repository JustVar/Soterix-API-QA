"""Compatibility shim. The code moved to soterix-qa-shared.

Import this path as before; it resolves to soterix_qa_shared.qatouch.reporter.
See that repo's docs/RULES.md for why the shim has this exact shape.
"""
import sys

from tools.qatouch_mapping import reviewed_lookup as _policy

try:
    from soterix_qa_shared.qatouch import reporter as _mod
except ModuleNotFoundError as exc:
    if (exc.name or "").split(".")[0] != "soterix_qa_shared":
        raise                    # a dependency of the package is missing
    raise ModuleNotFoundError(
        "soterix-qa-shared is not installed. "
        "Run: pip install -e ../soterix-qa-shared"
    ) from None

# Which mapping rows may upload is THIS repo's decision, and it gates on
# reviewed. Of its 31 rows, 18 were written deliberately and 13 were guessed
# by word overlap - and every one of the 13 points at a UI behaviour case,
# while all 7 of those cases appear in the live QA Touch runs and 0 of the 5
# correct ones do. Ungated, the only results that would land are the wrong
# ones. Injected BEFORE the alias swap.
_mod.MAPPING_POLICY = _policy

sys.modules[__name__] = _mod
