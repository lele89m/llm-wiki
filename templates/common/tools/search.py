#!/usr/bin/env python3
"""BM25 full-text search over wiki pages."""

import re
import sys
import argparse
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
    _HAS_BM25 = True
except ImportError:
    _HAS_BM25 = False

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

    if _HAS_BM25:
        bm25   = BM25Okapi([p["tokens"] for p in pages])
        scores = bm25.get_scores(terms)
        ranked = [
            (s, p) for s, p in sorted(zip(scores, pages), key=lambda x: -x[0])
            if s > 0
        ][:limit]
        engine = "BM25"
    else:
        # Fallback: count how many query terms appear in each page
        def keyword_score(page):
            combined = " ".join(page["tokens"])
            return sum(combined.count(t) for t in terms)

        scored = [(keyword_score(p), p) for p in pages]
        ranked = [(s, p) for s, p in sorted(scored, key=lambda x: -x[0]) if s > 0][:limit]
        engine = "keyword (install rank-bm25 for better results)"

    if not ranked:
        print(f'No results for "{query}"')
        return

    print(f'\nResults for "{query}"  [{engine}]\n{"─" * 60}')
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
