"""Which mapping rows may write a status to QA Touch.

A mapping row says "this test verifies that case". Some rows were written
deliberately and some were guessed by word overlap, and only the first kind
may upload: a status written through a guess lands on a case no test
verified, and nobody looking at QA Touch can tell the difference.

Measured on this repo's 31 rows when the gate was added:

  * 18 rows, `auto_matched: false`, map 5 cases whose titles begin "API -
    Integration". Those cases were written FOR these tests. Every one is
    correct. They carry `reviewed: true` and are the rows the file holds.
  * 13 rows, `auto_matched: true`, mapped 7 cases that were all UI
    behaviour ("Verify tooltip on site status", "Verify online camera
    count updates correctly in Maps widget"). Not one described an API
    call. Every one was wrong, including the row scored 1.0: a word-overlap
    score means nothing. Those rows are deleted from the file.

And the reason a gate is not optional here: of the 7 wrongly-matched cases,
all 7 appeared in the live QA Touch runs, while 0 of the 5 correct ones
did. Ungated, the ONLY results that would land were the wrong ones. A new
row uploads only after a person sets `reviewed: true` on it.

The reporter reads this through the shim in plugins/qatouch_reporter.py.
The UI repo has the same gate, in a module of the same name.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = ROOT / 'config' / 'qatouch_case_mapping.json'


def load_raw(path: Path = MAPPING_PATH) -> dict:
    """The mapping file, or an empty one when it is not there."""
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def reviewed_lookup(path: Path = MAPPING_PATH) -> tuple[dict[str, str], dict[str, int]]:
    """nodeid -> case_key for REVIEWED rows only, plus counts for reporting.

    counts: {'total', 'reviewed', 'unreviewed'}. Print them wherever this is
    used, so a skipped row is never silent.

    A missing `reviewed` key reads as NOT reviewed. That is the safe
    direction: a row nobody has confirmed does not get to write a status.
    """
    mappings = load_raw(path).get('mappings', {})
    reviewed = {n: e['case_key'] for n, e in mappings.items()
                if e.get('reviewed') is True and e.get('case_key')}
    return reviewed, {
        'total': len(mappings),
        'reviewed': len(reviewed),
        'unreviewed': len(mappings) - len(reviewed),
    }
