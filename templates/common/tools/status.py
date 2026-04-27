#!/usr/bin/env python3
"""Wiki dashboard — run at the start of a session to orient yourself."""

import re
import sys
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def find_root():
    here = Path(__file__).resolve().parent.parent
    if (here / "wiki").is_dir():
        return here
    raise FileNotFoundError(f"wiki/ not found in {here}")


def count_pages(wiki_dir):
    return len([p for p in wiki_dir.rglob("*.md")
                if not p.name.startswith("_")
                and p.name not in ("index.md", "log.md", "overview.md")])


def count_sources(wiki_dir):
    sources_dir = wiki_dir / "sources"
    if not sources_dir.is_dir():
        return 0
    return len(list(sources_dir.glob("*.md")))


def last_log_entries(wiki_dir, n=5):
    log = wiki_dir / "log.md"
    if not log.exists():
        return []
    text = log.read_text(encoding="utf-8")
    return re.findall(r'^## (\[.+)', text, re.MULTILINE)[-n:]


def last_updated(wiki_dir):
    dates = []
    for p in wiki_dir.rglob("*.md"):
        if p.name.startswith("_"):
            continue
        text = p.read_text(encoding="utf-8")
        m = re.search(r'^updated:\s*(.+)', text, re.MULTILINE)
        if m:
            dates.append(m.group(1).strip())
    return max(dates) if dates else "—"


def count_raw(root):
    sources = root / "raw" / "sources"
    if not sources.is_dir():
        return 0
    return len([f for f in sources.iterdir()
                if f.is_file() and not f.name.startswith(".")])


def main():
    try:
        root = find_root()
    except FileNotFoundError as e:
        print(e); sys.exit(1)

    wiki_dir = root / "wiki"

    pages   = count_pages(wiki_dir)
    sources = count_sources(wiki_dir)
    raw     = count_raw(root)
    updated = last_updated(wiki_dir)
    entries = last_log_entries(wiki_dir)

    print(f"\nWiki status — {root.name}")
    print("─" * 50)
    print(f"  Pages:          {pages}")
    print(f"  Sources (wiki): {sources}")
    print(f"  Raw files:      {raw}")
    print(f"  Last updated:   {updated}")

    if entries:
        print(f"\nLast {len(entries)} operations:")
        for e in entries:
            print(f"  {e}")
    else:
        print("\n  No operations logged yet.")

    print()


if __name__ == "__main__":
    main()
