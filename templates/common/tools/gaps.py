#!/usr/bin/env python3
"""Show open knowledge gaps — questions the agent couldn't answer.

Usage:
  python tools/gaps.py             # show all open gaps
  python tools/gaps.py --all       # include resolved gaps
  python tools/gaps.py --priority high
"""

import re
import sys
import argparse
from pathlib import Path


def find_root():
    here = Path(__file__).resolve().parent.parent
    if (here / "wiki").is_dir():
        return here
    raise FileNotFoundError(f"wiki/ not found in {here}")


def parse_gaps(text):
    pattern = re.compile(
        r'^## \[(\d{4}-\d{2}-\d{2})\] "([^"]+)" \| priority: (\w+) \| status: (\w+)',
        re.MULTILINE,
    )
    gaps = []
    for m in pattern.finditer(text):
        gaps.append({
            "date":     m.group(1),
            "question": m.group(2),
            "priority": m.group(3),
            "status":   m.group(4),
        })
    return gaps


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def main():
    ap = argparse.ArgumentParser(description="Show knowledge gaps")
    ap.add_argument("--all",      action="store_true", help="Include resolved gaps")
    ap.add_argument("--priority", choices=["high", "medium", "low"], help="Filter by priority")
    args = ap.parse_args()

    try:
        root = find_root()
    except FileNotFoundError as e:
        print(e); sys.exit(1)

    gaps_file = root / "wiki" / "gaps.md"
    if not gaps_file.exists():
        print("No gaps.md found.")
        sys.exit(0)

    gaps = parse_gaps(gaps_file.read_text(encoding="utf-8"))

    if not args.all:
        gaps = [g for g in gaps if g["status"] == "open"]
    if args.priority:
        gaps = [g for g in gaps if g["priority"] == args.priority]

    gaps.sort(key=lambda g: (PRIORITY_ORDER.get(g["priority"], 9), g["date"]))

    open_count = sum(1 for g in gaps if g["status"] == "open")

    print(f"\nKnowledge gaps — {root.name}")
    print(f"Open: {open_count}  Showing: {len(gaps)}")
    print("─" * 60)

    if not gaps:
        print("  No gaps.")
    else:
        for g in gaps:
            icon = "⬤" if g["status"] == "open" else "✓"
            pri  = {"high": "HIGH", "medium": "MED ", "low": "LOW "}.get(g["priority"], g["priority"])
            print(f"\n  {icon} [{g['date']}] {pri}  {g['question']}")

    print()


if __name__ == "__main__":
    main()
