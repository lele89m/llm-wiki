#!/usr/bin/env python3
"""Wiki changelog — show what pages changed between two dates.

Useful for team standup, review after absence, or audit after an incident.

Usage:
  python tools/diff.py                        # last 7 days
  python tools/diff.py --days 30              # last 30 days
  python tools/diff.py --from 2026-04-20      # from date to today
  python tools/diff.py --from 2026-04-20 --to 2026-04-27
"""

import re
import sys
import argparse
import subprocess
from datetime import date, timedelta
from pathlib import Path


def find_root():
    here = Path(__file__).resolve().parent.parent
    if (here / "wiki").is_dir():
        return here
    raise FileNotFoundError(f"wiki/ not found in {here}")


def git(*args, cwd):
    r = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    return (r.stdout.strip(), None) if r.returncode == 0 else (None, r.stderr.strip())


def changed_files(root, since, until, diff_filter):
    """Return unique wiki .md files matching the git diff filter."""
    cmd = [
        "log",
        f"--diff-filter={diff_filter}",
        "--name-only",
        "--pretty=format:",
        f"--since={since}",
    ]
    if until:
        cmd.append(f"--until={until} 23:59:59")
    cmd += ["--", "wiki/"]

    out, _ = git(*cmd, cwd=root)
    if not out:
        return []

    seen, result = set(), []
    for line in out.splitlines():
        f = line.strip()
        if f and f.endswith(".md") and f not in seen:
            name = Path(f).name
            if not name.startswith("_"):   # skip _templates, _templater, _charts
                seen.add(f)
                result.append(f)
    return result


def log_entries_in_range(root, since, until_str):
    log_file = root / "wiki" / "log.md"
    if not log_file.exists():
        return []
    text = log_file.read_text(encoding="utf-8")
    entries = re.findall(r'^## (\[\d{4}-\d{2}-\d{2}\].+)', text, re.MULTILINE)
    return [
        e for e in entries
        if (m := re.match(r'\[(\d{4}-\d{2}-\d{2})\]', e))
        and since <= m.group(1) <= until_str
    ]


def main():
    ap = argparse.ArgumentParser(description="Wiki changelog between two dates")
    ap.add_argument("--from", dest="since", metavar="YYYY-MM-DD", help="Start date")
    ap.add_argument("--to",   dest="until", metavar="YYYY-MM-DD", help="End date (default: today)")
    ap.add_argument("--days", type=int, default=7, metavar="N",
                    help="Look back N days (default: 7, ignored if --from is given)")
    ap.add_argument("--wiki", metavar="DIR", help="Path to wiki root directory")
    args = ap.parse_args()

    try:
        root = Path(args.wiki).resolve() if args.wiki else find_root()
    except FileNotFoundError as e:
        print(e); sys.exit(1)

    today     = date.today().isoformat()
    since     = args.since or (date.today() - timedelta(days=args.days)).isoformat()
    until     = args.until
    until_str = until or today

    # verify git repo
    out, err = git("rev-parse", "--git-dir", cwd=root)
    if out is None:
        print("Error: not a git repository.")
        print("  Run: git init && git add -A && git commit -m 'initial'")
        sys.exit(1)

    added    = changed_files(root, since, until, "A")
    modified = changed_files(root, since, until, "M")
    deleted  = changed_files(root, since, until, "D")
    entries  = log_entries_in_range(root, since, until_str)

    period = f"{since} → {until_str}"
    print(f"\nWiki changelog  {period}")
    print("─" * 60)

    def section(icon, label, files):
        print(f"\n{icon} {label} ({len(files)}):")
        if files:
            for f in files:
                print(f"   {f}")
        else:
            print("   none")

    section("✚", "Added",    added)
    section("✎", "Modified", modified)
    section("✖", "Deleted",  deleted)

    print(f"\n📋 Operations ({len(entries)}):")
    if entries:
        for e in entries:
            print(f"   {e}")
    else:
        print("   none logged in this period")

    total_pages = len(added) + len(modified) + len(deleted)
    print(f"\n{'─' * 60}")
    print(f"Pages touched: {total_pages}  |  Operations: {len(entries)}\n")


if __name__ == "__main__":
    main()
