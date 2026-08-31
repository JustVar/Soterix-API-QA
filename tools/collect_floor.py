#!/usr/bin/env python3
"""Fail when this repo collects fewer tests than it used to.

The gate lives in soterix_qa_shared.gates.collect_floor, which carries the
reasoning and the tests. This file is the part that is specific to this
repository: which suites are watched.

Usage:
  python tools/collect_floor.py            # check against the floor
  python tools/collect_floor.py --update   # record the current counts

The floor is config/collect_floor.json, committed. Going up is always fine.
Going down needs a reason in the commit message.
"""
from __future__ import annotations

import sys
from pathlib import Path

from soterix_qa_shared.gates import collect_floor

ROOT = Path(__file__).resolve().parent.parent

# The two API surfaces are watched separately. They are reached through
# different auth contracts, so one can lose its tests while the other keeps
# the combined number looking healthy.
SUITES = {
    'whole repo': [],
    'internal api': ['tests/internal_api'],
    'integration api': ['tests/integration_api'],
}

if __name__ == '__main__':
    sys.exit(collect_floor.main(sys.argv[1:], root=ROOT, suites=SUITES))
