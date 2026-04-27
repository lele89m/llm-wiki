#!/usr/bin/env python3
"""Extract text from PDF, HTML, or other files to markdown.

Useful for Ollama and other LLMs that cannot read files natively.
The LLM can call this to get readable text before ingesting a source.

Usage:
  python tools/extract.py raw/sources/report.pdf -o /tmp/report.md
  python tools/extract.py raw/sources/page.html  -o /tmp/page.md
"""

import re
import sys
import argparse
from pathlib import Path


def extract_pdf(path):
    # best: pymupdf4llm (outputs clean markdown)
    try:
        import pymupdf4llm
        return pymupdf4llm.to_markdown(str(path))
    except ImportError:
        pass
    # fallback: pymupdf plain text
    try:
        import fitz
        doc = fitz.open(str(path))
        pages = [page.get_text() for page in doc]
        return "\n\n---\n\n".join(pages)
    except ImportError:
        pass
    print("Error: no PDF library found.")
    print("Install one of:")
    print("  pip install pymupdf4llm    # best: PDF → clean markdown")
    print("  pip install pymupdf        # fallback: PDF → plain text")
    sys.exit(1)


def extract_html(path):
    content = path.read_text(encoding="utf-8", errors="replace")
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        main = soup.find("article") or soup.find("main") or soup.body or soup
        text = main.get_text(separator="\n", strip=True)
    except ImportError:
        # regex fallback — good enough for most articles
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in (".html", ".htm"):
        return extract_html(path)
    if suffix in (".md", ".txt", ".rst", ".text"):
        return path.read_text(encoding="utf-8", errors="replace")
    # unknown — try as text
    print(f"Warning: unsupported format '{suffix}', reading as plain text.", file=sys.stderr)
    return path.read_text(encoding="utf-8", errors="replace")


MAX_FILE_SIZE_MB = 50


def main():
    ap = argparse.ArgumentParser(description="Extract text from PDF/HTML/MD to markdown")
    ap.add_argument("file", help="Input file")
    ap.add_argument("-o", "--output", help="Output file (default: stdout)")
    ap.add_argument("--max-mb", type=int, default=MAX_FILE_SIZE_MB,
                    help=f"Max file size in MB (default: {MAX_FILE_SIZE_MB})")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > args.max_mb:
        print(f"Error: file is {size_mb:.1f} MB, exceeds limit of {args.max_mb} MB.", file=sys.stderr)
        print(f"Use --max-mb to override if intentional.", file=sys.stderr)
        sys.exit(1)

    # Warn if file is not inside expected raw/sources/ directory (path traversal guard)
    try:
        resolved = path.resolve()
        cwd = Path.cwd().resolve()
        resolved.relative_to(cwd)  # raises ValueError if outside cwd
    except ValueError:
        print(f"Warning: file is outside the current working directory: {path}", file=sys.stderr)

    text = extract(path)

    if args.output:
        out = Path(args.output)
        out.write_text(text, encoding="utf-8")
        print(f"Saved {len(text):,} chars → {out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
