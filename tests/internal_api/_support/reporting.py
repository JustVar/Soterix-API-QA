"""Compatibility shim - the report-block helpers moved to the shared package.

Import this path as before; it resolves to soterix_qa_shared.reporting.htmlblocks.
The docstring rationale (why html extras, not data: URI links) moved with it.
"""
import sys

from soterix_qa_shared.reporting import htmlblocks as _mod

sys.modules[__name__] = _mod
