#!/usr/bin/env python3
"""List the internal API paths the code calls, and check them against the inventory.

    python tools/api_usage.py                 # endpoint -> files that call it
    python tools/api_usage.py --check         # drift vs docs/INTERNAL_API_INVENTORY.md

Paths are read from string literals in api_clients/ and tests/ (anything
starting with /REST/). Format placeholders ({siteId}, {id}, f-string names)
are normalised to {} so the same endpoint matches across files.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN = ("api_clients", "tests")
INVENTORY = ROOT / "docs" / "INTERNAL_API_INVENTORY.md"
PATH_RE = re.compile(r"/REST/[A-Za-z0-9_{}/.:-]+")


def normalise(path: str) -> str:
    """One shape per endpoint: placeholders and literal ids both become {},
    and a sentence-ending dot from a docstring is not part of the path."""
    path = path.rstrip("/.,;:)")
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return re.sub(r"/\d+(?=/|$)", "/{}", path)


def scan() -> dict[str, set[str]]:
    used: dict[str, set[str]] = {}
    for top in SCAN:
        for f in (ROOT / top).rglob("*.py"):
            rel = f.relative_to(ROOT).as_posix()
            for m in PATH_RE.findall(f.read_text(encoding="utf-8", errors="replace")):
                if "..." in m:
                    continue  # prose, not a path
                used.setdefault(normalise(m), set()).add(rel)
    return used


def inventory_paths() -> set[str]:
    if not INVENTORY.exists():
        return set()
    return {normalise(m) for m in PATH_RE.findall(INVENTORY.read_text(encoding="utf-8"))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="report drift against the inventory")
    args = ap.parse_args()
    used = scan()
    if not args.check:
        for path in sorted(used):
            print(f"{path}\n    " + "\n    ".join(sorted(used[path])))
        print(f"\n{len(used)} endpoints referenced in code")
        return 0
    inv = inventory_paths()
    missing = sorted(p for p in used if p not in inv)
    unused = sorted(p for p in inv if p not in used)
    print(f"in code, not in inventory ({len(missing)}):")
    for p in missing:
        print(f"  {p}  <- {', '.join(sorted(used[p]))}")
    print(f"in inventory, not called by code ({len(unused)}):")
    for p in unused:
        print(f"  {p}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
