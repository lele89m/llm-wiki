#!/usr/bin/env python3
"""BM25 full-text search over wiki pages."""

import re
import sys
import argparse
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    print("Error: rank-bm25 not installed. Run: pip install rank-bm25")
    sys.exit(1)

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
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    meta = {}
    if _HAS_YAML:
        try:
            meta = yaml.safe_load(parts[1]) or {}
        except Exception:
            pass
    return meta, parts[2]


def tokenize(text):
    text = re.sub(r'\[\[([^\]|#]+)[^\]]*\]\]', r'\1', text)  # unwrap [[links]]
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)      # unwrap [text](url)
    text = re.sub(r'[^a-z0-9\s]', ' ', text.lower())
    return [t for t in text.split() if len(t) > 2]


def load_pages(wiki_dir):
    pages = []
    for path in sorted(wiki_dir.rglob("*.md")):
        if path.name.startswith("_") or path.name == "log.md":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(content)
        title = meta.get("title") or path.stem.replace("-", " ").title()
        rel = str(path.relative_to(wiki_dir.parent))
        pages.append({
            "path": path,
            "rel": rel,
            "title": title,
            "meta": meta,
            "body": body,
            "tokens": tokenize(f"{title} {body}"),
        })
    return pages


def snippet(body, terms, width=200):
    lower = body.lower()
    best = len(body)
    for t in terms:
        pos = lower.find(t)
        if 0 <= pos < best:
            best = pos
    start = max(0, best - 60)
    chunk = body[start:start + width].strip()
    chunk = re.sub(r'\s+', ' ', chunk)
    return ("…" if start > 0 else "") + chunk + "…"


def run(query, wiki_dir, limit):
    pages = load_pages(wiki_dir)
    if not pages:
        print("No pages found.")
        return

    terms = tokenize(query)
    bm25 = BM25Okapi([p["tokens"] for p in pages])
    scores = bm25.get_scores(terms)
    ranked = [(s, p) for s, p in sorted(zip(scores, pages), key=lambda x: -x[0]) if s > 0][:limit]

    if not ranked:
        print(f'No results for "{query}"')
        return

    print(f'\nResults for "{query}"\n{"─" * 60}')
    for i, (score, page) in enumerate(ranked, 1):
        status = page["meta"].get("status", "")
        tag = f"  [{status}]" if status and status != "stable" else ""
        print(f"\n{i}. {page['title']}{tag}")
        print(f"   {page['rel']}  (score: {score:.2f})")
        print(f"   {snippet(page['body'], terms)}")
    print()


def main():
    ap = argparse.ArgumentParser(description="Search wiki pages (BM25)")
    ap.add_argument("query", help="Search query")
    ap.add_argument("--limit", "-n", type=int, default=5, metavar="N", help="Max results (default: 5)")
    ap.add_argument("--wiki", metavar="DIR", help="Path to wiki directory")
    args = ap.parse_args()

    wiki_dir = Path(args.wiki) if args.wiki else find_wiki_dir()
    run(args.query, wiki_dir, args.limit)


if __name__ == "__main__":
    main()
