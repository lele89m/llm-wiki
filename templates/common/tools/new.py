#!/usr/bin/env python3
"""Scaffold a new wiki page from a template.

Usage:
  python tools/new.py <type> "<Title>"

Types:
  concept         wiki/concepts/
  entity          wiki/  (you choose the subdir)
  source-summary  wiki/sources/
  analysis        wiki/analysis/
  decision        wiki/decisions/
  runbook         wiki/incidents/

Examples:
  python tools/new.py concept "Zero Trust Networking"
  python tools/new.py decision "Use Terraform over Pulumi"
  python tools/new.py runbook "Kubernetes node drain"
"""

import sys
import re
from datetime import date
from pathlib import Path

TYPE_TO_DIR = {
    "concept":        "concepts",
    "entity":         ".",           # user picks subdir
    "source-summary": "sources",
    "analysis":       "analysis",
    "decision":       "decisions",
    "runbook":        "incidents",
}

VALID_TYPES = list(TYPE_TO_DIR.keys())


def find_root():
    here = Path(__file__).resolve().parent.parent
    if (here / "wiki").is_dir():
        return here
    raise FileNotFoundError(f"wiki/ not found in {here}")


def slugify(title):
    s = title.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    return s.strip('-')


def load_template(root, page_type):
    tpl_name = page_type if page_type != "source-summary" else "source-summary"
    tpl_path = root / "wiki" / "_templates" / f"{tpl_name}.md"
    if tpl_path.exists():
        return tpl_path.read_text(encoding="utf-8")
    # minimal fallback
    return (
        f"---\ntitle: \"{{title}}\"\ntype: {page_type}\ntags: []\n"
        f"created: {{date}}\nupdated: {{date}}\nsources: 0\nstatus: draft\n---\n\n"
        f"# {{title}}\n\n> One-line description.\n"
    )


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    page_type = sys.argv[1].lower()
    title     = " ".join(sys.argv[2:])

    if page_type not in VALID_TYPES:
        print(f"Error: unknown type '{page_type}'")
        print(f"Valid types: {', '.join(VALID_TYPES)}")
        sys.exit(1)

    try:
        root = find_root()
    except FileNotFoundError as e:
        print(e); sys.exit(1)

    subdir = TYPE_TO_DIR[page_type]
    wiki_dir = root / "wiki"
    target_dir = wiki_dir / subdir if subdir != "." else wiki_dir

    today = date.today().isoformat()
    slug  = slugify(title)
    tpl   = load_template(root, page_type)

    content = tpl.replace("Entity Name",  title) \
                 .replace("Concept Name", title) \
                 .replace("Source Title", title) \
                 .replace("Analysis Title", title) \
                 .replace("Decision Title", title) \
                 .replace("Runbook: Title", f"Runbook: {title}") \
                 .replace("ADR: Decision Title", f"ADR: {title}") \
                 .replace("YYYY-MM-DD", today) \
                 .replace('"Page Title"', f'"{title}"')

    out = target_dir / f"{slug}.md"
    if out.exists():
        print(f"Already exists: {out.relative_to(root)}")
        sys.exit(1)

    out.write_text(content, encoding="utf-8")
    print(f"Created: {out.relative_to(root)}")


if __name__ == "__main__":
    main()
