#!/usr/bin/env python3
"""Wiki health check: orphans, broken links, missing frontmatter."""

import re
import sys
import argparse
from datetime import date
from pathlib import Path
from collections import defaultdict

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def find_wiki_dir():
    here = Path(__file__).resolve().parent
    candidate = here.parent / "wiki"
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError(f"wiki/ not found relative to {here}")


def parse_frontmatter(content):
    if not content.startswith("---"):
        return {}, content
    # Match closing --- only on its own line to avoid splitting on --- inside values
    # (e.g. filenames like "My-File---With-Dashes.html")
    m = re.search(r'(?m)^---\s*$', content[3:])
    if not m:
        return {}, content
    fm_text = content[3:3 + m.start()]
    body    = content[3 + m.end():]
    meta = {}
    if _HAS_YAML:
        try:
            meta = yaml.safe_load(fm_text) or {}
        except Exception:
            pass
    return meta, body


def wikilinks(text):
    return re.findall(r'\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]', text)


def mdlinks(text):
    return re.findall(r'\[(?:[^\]]+)\]\(([^)]+\.md[^)]*)\)', text)


def load_pages(wiki_dir):
    pages = {}
    for path in sorted(wiki_dir.rglob("*.md")):
        rel = path.relative_to(wiki_dir)
        key = str(rel.with_suffix("")).lower().replace("\\", "/")
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(content)
        outlinks = wikilinks(body) + [l.removesuffix(".md") for l in mdlinks(body)]
        pages[key] = {
            "path": path,
            "rel": str(rel),
            "meta": meta,
            "body": body,
            "outlinks": outlinks,
        }
    return pages


def resolve(link, source_key, all_keys):
    norm = link.lower().strip().replace(" ", "-").replace("\\", "/")
    if norm in all_keys:
        return norm
    # try relative to source directory
    src_dir = "/".join(source_key.split("/")[:-1])
    cand = f"{src_dir}/{norm}" if src_dir else norm
    if cand in all_keys:
        return cand
    # suffix match
    for k in all_keys:
        if k == norm or k.endswith(f"/{norm}"):
            return k
    return None


EXEMPT = {"index", "log", "overview", "gaps"}

# Link targets that are intentional placeholders in templates/index scaffolds.
_PLACEHOLDER_SEGMENTS = {"slug", "page-slug", "filename", "source-name", "category"}
_PLACEHOLDER_PATHS = {"sources/slug", "category/page-slug", "raw/sources/filename"}


def _is_placeholder(link):
    norm = link.strip().lower().rstrip("/")
    if norm in _PLACEHOLDER_PATHS:
        return True
    last = norm.split("/")[-1]
    return last in _PLACEHOLDER_SEGMENTS


def lint(wiki_dir):
    pages = load_pages(wiki_dir)
    all_keys = set(pages.keys())
    inbound = defaultdict(set)

    for key, page in pages.items():
        for lnk in page["outlinks"]:
            res = resolve(lnk, key, all_keys)
            if res:
                inbound[res].add(key)

    issues = 0

    def section(label, items, fmt):
        nonlocal issues
        if not items:
            return
        issues += len(items)
        print(f"\n{label} ({len(items)}):")
        for item in items:
            print(f"  {fmt(item)}")

    print(f"\nWiki Health Check — {wiki_dir}")
    print(f"Pages: {len(pages)}")
    print("─" * 60)

    no_meta = [
        p for k, p in pages.items()
        if not p["meta"]
        and not k.startswith("_")
        and k.split("/")[-1] not in EXEMPT
    ]
    section("⚠️  Missing frontmatter", no_meta, lambda p: p["rel"])

    broken = []
    for key, page in pages.items():
        # skip template directories — links inside are intentional placeholders
        if key.startswith("_templates/") or key.startswith("_templater/"):
            continue
        for lnk in page["outlinks"]:
            if _is_placeholder(lnk):
                continue
            if not resolve(lnk, key, all_keys):
                broken.append((page["rel"], lnk))
    section("🔗 Broken links", broken, lambda x: f"{x[0]} → [[{x[1]}]]")

    orphans = [
        p for k, p in pages.items()
        if k not in inbound
        and not any(k == s or k.endswith(f"/{s}") for s in EXEMPT)
        and not k.startswith("_")
    ]
    section("🏝️  Orphan pages (no inbound links)", orphans, lambda p: p["rel"])

    no_out = [
        p for k, p in pages.items()
        if not page["outlinks"]
        and not k.startswith("_")
        and k not in EXEMPT
    ]
    section("📭 No outbound links", no_out, lambda p: p["rel"])

    stale = [p for k, p in pages.items() if p["meta"].get("status") == "stale"]
    section("⏰ Stale pages", stale, lambda p: p["rel"])

    no_type = [p for k, p in pages.items() if p["meta"] and not p["meta"].get("type") and not k.startswith("_")]
    section("🏷️  Missing type in frontmatter", no_type, lambda p: p["rel"])

    # valid_until check
    today = date.today().isoformat()
    expired = []
    expiring_soon = []
    for k, p in pages.items():
        vu = str(p["meta"].get("valid_until", "") or "").strip()
        if not vu or k.startswith("_"):
            continue
        if vu < today:
            expired.append((p["rel"], vu))
        elif vu <= today[:8] + "31":  # within ~1 month (rough check)
            # proper check: compare YYYY-MM-DD strings lexicographically
            from datetime import datetime, timedelta
            try:
                exp_date = datetime.strptime(vu, "%Y-%m-%d").date()
                if exp_date <= date.today() + timedelta(days=30):
                    expiring_soon.append((p["rel"], vu))
            except ValueError:
                pass
    section("🚨 Expired pages (valid_until in the past)", expired,
            lambda x: f"{x[0]}  [expired: {x[1]}]")
    section("⏳ Expiring soon (within 30 days)", expiring_soon,
            lambda x: f"{x[0]}  [valid until: {x[1]}]")

    # open gaps summary
    gaps_file = wiki_dir / "gaps.md"
    if gaps_file.exists():
        open_gaps = len(re.findall(r'status: open', gaps_file.read_text(encoding="utf-8")))
        if open_gaps:
            print(f"\n📋 Open knowledge gaps: {open_gaps}  (run: python tools/gaps.py)")

    print(f"\n{'─' * 60}")
    if issues == 0:
        print("✓ Wiki is healthy!")
    else:
        print(f"Total issues: {issues}")
    print()

    return issues


def main():
    ap = argparse.ArgumentParser(description="Wiki health check")
    ap.add_argument("--wiki", metavar="DIR", help="Path to wiki directory")
    args = ap.parse_args()

    wiki_dir = Path(args.wiki) if args.wiki else find_wiki_dir()
    issues = lint(wiki_dir)
    sys.exit(0 if issues == 0 else 1)


if __name__ == "__main__":
    main()
