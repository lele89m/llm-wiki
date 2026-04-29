#!/usr/bin/env python3
"""
Ollama wiki agent — interactive session with full file access.

Usage:
  python tools/chat.py
  python tools/chat.py --model qwen2.5:7b
  python tools/chat.py --model qwen2.5-coder:7b
"""

import json
import re
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from urllib import request as urllib_request, error as urllib_error

# ── config ─────────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "qwen2.5:7b"
OLLAMA_API    = "http://localhost:11434/api/chat"
MAX_FILE_KB   = 400
MAX_HISTORY   = 20

# Auto-detect python binary once at startup
PYTHON = shutil.which("python3") or shutil.which("python") or "python3"

TOOL_INSTRUCTIONS = f"""

---

## Tool access (Ollama session)

You have full access to wiki files and tools via action tags.
**Rules — read carefully:**

1. Action tags MUST be on their own line, NEVER inside code blocks or backticks.
2. Use them only when you actually need to execute something — not as examples.
3. You can chain multiple actions; each is executed in order.
4. After receiving results, incorporate them into your response.

### Read a file
<read>wiki/index.md</read>
<read>wiki/concepts/kubernetes.md</read>

### Run a tool
<run>python tools/status.py</run>
<run>python tools/search.py "query" --limit 5</run>
<run>python tools/lint.py</run>
<run>python tools/gaps.py</run>
<run>python tools/diff.py --days 7</run>

### Write a file (create or overwrite — wiki/ only)
<write path="wiki/concepts/kubernetes.md">
---
title: "Kubernetes"
type: concept
tags: [kubernetes, containers]
created: 2026-04-27
updated: 2026-04-27
sources: 1
status: draft
---

# Kubernetes

> Container orchestration platform.

## What it is
...
</write>

**Write rules:**
- Only write to wiki/ directory. Never write to raw/, tools/, or root files.
- Always read the file first before overwriting it.
- When adding frontmatter to an existing page, read it first, then write the full updated content.
- When updating index.md, read it first, add only the new entries, write it back.
- Python executable on this system: `{PYTHON}`

---

## Answering questions

When the user asks a technical question or describes a problem, **ALWAYS follow this order — no exceptions**:

1. Run `python tools/search.py "<topic>" --limit 5`
2. Read the top 2-3 matching pages with `<read>`
3. Answer using only what the wiki contains, citing pages as `([[page-name]])`
4. If no relevant pages found: say "I have no documentation on this yet" — **do NOT answer from general knowledge**

---

## Handling ambiguous commands

**"ingest"** (no file specified) — do not ask for clarification. Instead:
1. Look at the pending sources list provided in the session context.
2. If there are pending sources, list them and ask which one to ingest (or ingest all if told so).
3. If no pending sources, say so.

**"ingest <file>"** — follow the ingest workflow in the schema:
1. Extract if PDF/HTML: `python tools/extract.py raw/sources/<file> -o /tmp/extracted.md`, then read `/tmp/extracted.md`.
2. Discuss 3-5 key takeaways.
3. Write `wiki/sources/<slug>.md` using the source-summary template.
4. Update or create related concept/entity pages (aim for 3-10 page touches).
5. Read then update `wiki/index.md` (add new entries only, never overwrite existing content).
6. Append to `wiki/log.md`.

**"lint"** — run `python tools/lint.py` and explain each issue with a fix suggestion.

**"gaps"** — run `python tools/gaps.py` and suggest what to ingest or create to close each gap.

**"status"** — run `python tools/status.py` and summarise the wiki state.
"""

# ── colors ──────────────────────────────────────────────────────────────────────

IS_TTY = sys.stdout.isatty()

if IS_TTY:
    BOLD="\033[1m"; DIM="\033[2m"; NC="\033[0m"
    GREEN="\033[0;32m"; BLUE="\033[0;34m"; RED="\033[0;31m"
    CYAN="\033[0;36m"; YELLOW="\033[0;33m"
else:
    BOLD=DIM=NC=GREEN=BLUE=RED=CYAN=YELLOW=""


# ── markdown → ANSI renderer ────────────────────────────────────────────────────

def render_ansi(text):
    """Convert basic markdown to ANSI terminal formatting."""
    lines = []
    in_code = False
    for line in text.splitlines():
        # code fences
        if line.startswith("```"):
            if not in_code:
                lang = line[3:].strip()
                label = f" {lang}" if lang else ""
                lines.append(f"{DIM}┄┄┄{label}{'┄' * max(0, 37 - len(label))}{NC}")
            else:
                lines.append(f"{DIM}{'┄' * 40}{NC}")
            in_code = not in_code
            continue
        if in_code:
            lines.append(f"  {DIM}{line}{NC}")
            continue
        # headings
        if line.startswith("#### "):
            lines.append(f"{BOLD}{line[5:]}{NC}")
        elif line.startswith("### "):
            lines.append(f"\n{BOLD}{line[4:]}{NC}")
        elif line.startswith("## "):
            lines.append(f"\n{BOLD}{CYAN}{line[3:]}{NC}")
        elif line.startswith("# "):
            lines.append(f"\n{BOLD}{CYAN}{line[2:]}{NC}\n{CYAN}{'─' * 50}{NC}")
        elif line.startswith("---") and line.strip("- ") == "":
            lines.append(f"{DIM}{'─' * 50}{NC}")
        else:
            # inline bold **text** and __text__
            line = re.sub(r'\*\*(.+?)\*\*', f'{BOLD}\\1{NC}', line)
            line = re.sub(r'__(.+?)__',     f'{BOLD}\\1{NC}', line)
            # inline italic *text*
            line = re.sub(r'\*(.+?)\*',     f'{DIM}\\1{NC}',  line)
            # inline code `text`
            line = re.sub(r'`([^`]+)`',     f'{YELLOW}\\1{NC}', line)
            # wiki links [[page]]
            line = re.sub(r'\[\[([^\]]+)\]\]', f'{CYAN}[[\\1]]{NC}', line)
            lines.append(line)
    return "\n".join(lines)

# ── helpers ─────────────────────────────────────────────────────────────────────

def find_root():
    here = Path(__file__).resolve().parent.parent
    if (here / "wiki").is_dir():
        return here
    raise FileNotFoundError("wiki/ not found. Run from inside a wiki repo.")


def pending_sources(root):
    """Return list of raw/sources/ files that have no wiki/sources/ summary yet."""
    raw_dir  = root / "raw" / "sources"
    wiki_src = root / "wiki" / "sources"

    if not raw_dir.exists():
        return []

    existing_stems = set()
    if wiki_src.exists():
        for f in wiki_src.glob("*.md"):
            existing_stems.add(f.stem.lower())

    pending = []
    for f in sorted(raw_dir.iterdir()):
        if f.name in (".gitkeep",) or f.name.startswith("."):
            continue
        if f.stem.lower() not in existing_stems:
            pending.append(f.name)
    return pending


def strip_code_fences(text):
    """Remove content inside ``` fences so tags inside examples aren't executed."""
    return re.sub(r'```.*?```', '', text, flags=re.DOTALL)


def safe_read(path_str, root):
    path = (root / path_str.strip()).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return f"[ERROR] Path outside wiki root: {path_str}"
    if not path.exists():
        return f"[ERROR] File not found: {path_str}"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        size_kb = len(text.encode()) / 1024
        if size_kb > MAX_FILE_KB:
            lines = text.splitlines()[:300]
            text = "\n".join(lines) + f"\n\n[Truncated — {size_kb:.0f} KB, showing first 300 lines]"
        return text
    except OSError as e:
        return f"[ERROR] {e}"


def safe_write(path_str, content, root):
    """Write content to a wiki/ file. Restricted to wiki/ only."""
    path = (root / path_str.strip()).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return f"[ERROR] Path outside wiki root: {path_str}"

    # Only allow writes inside wiki/
    wiki_dir = (root / "wiki").resolve()
    try:
        path.relative_to(wiki_dir)
    except ValueError:
        return f"[ERROR] Writes are only allowed inside wiki/. Got: {path_str}"

    # Refuse writes to protected files
    protected = {"_templates", "_templater", "_charts"}
    if any(part in protected for part in path.parts):
        return f"[ERROR] Cannot write to protected directory in path: {path_str}"

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"[OK] Written {len(content)} chars to {path_str}"
    except OSError as e:
        return f"[ERROR] Could not write {path_str}: {e}"


def safe_run(cmd, root):
    """Run a whitelisted tool command. Normalises python/python3."""
    cmd = cmd.strip()
    # normalise python binary
    cmd = re.sub(r'^python3?\s', f"{PYTHON} ", cmd)

    allowed = (f"{PYTHON} tools/",)
    if not any(cmd.startswith(p) for p in allowed):
        return f"[ERROR] Only 'python tools/' commands are allowed. Got: {cmd}"
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=root,
            capture_output=True, text=True, timeout=60,
        )
        out = r.stdout
        if r.returncode != 0 and r.stderr:
            out += f"\n[stderr]\n{r.stderr}"
        return out.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[ERROR] Timed out after 60s."
    except Exception as e:
        return f"[ERROR] {e}"


def process_actions(text, root):
    """
    Find action tags in the model response (outside code fences),
    execute them, return injected result strings.
    """
    # strip code fences so tags inside examples aren't executed
    scannable = strip_code_fences(text)

    reads  = re.findall(r'<read>(.*?)</read>',   scannable, re.DOTALL)
    runs   = re.findall(r'<run>(.*?)</run>',      scannable, re.DOTALL)
    writes = re.findall(
        r'<write\s+path="([^"]+)">(.*?)</write>', scannable, re.DOTALL
    )

    results = []
    seen_reads = set()

    for path in reads:
        path = path.strip()
        if path in seen_reads:
            continue
        seen_reads.add(path)
        print(f"\n  {DIM}📄 reading {path}...{NC}", flush=True)
        results.append(f"[File: {path}]\n{safe_read(path, root)}")

    for cmd in runs:
        cmd = cmd.strip()
        print(f"\n  {DIM}⚙  running: {cmd}{NC}", flush=True)
        results.append(f"[Output: {cmd}]\n{safe_run(cmd, root)}")

    for path, content in writes:
        path, content = path.strip(), content.strip()
        print(f"\n  {DIM}✎  writing {path}...{NC}", flush=True)
        results.append(f"[Write: {path}]\n{safe_write(path, content, root)}")

    return results

# ── ollama api ──────────────────────────────────────────────────────────────────

def ollama_chat(messages, model, api_url, pretty=False):
    payload = json.dumps({"model": model, "messages": messages, "stream": True}).encode()
    req = urllib_request.Request(
        api_url, data=payload, headers={"Content-Type": "application/json"}
    )
    full = ""
    try:
        with urllib_request.urlopen(req, timeout=180) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    if not pretty:
                        print(token, end="", flush=True)
                    full += token
                if chunk.get("done"):
                    break
    except urllib_error.URLError:
        print(f"\n{RED}Error: cannot reach Ollama at {api_url}{NC}")
        print("Run: ollama serve")
        sys.exit(1)

    if pretty:
        print(render_ansi(full))
    else:
        print()
    return full


def trim_history(messages, system_msg, max_pairs):
    non_system = [m for m in messages if m["role"] != "system"]
    if len(non_system) > max_pairs * 2:
        non_system = non_system[-(max_pairs * 2):]
        print(f"  {DIM}(old messages trimmed to keep context small){NC}")
    return [system_msg] + non_system


def agent_turn(messages, model, api_url, root, pretty=False):
    """One full agent turn: respond + resolve all action tags in a loop."""
    response = ollama_chat(messages, model, api_url, pretty=pretty)
    messages.append({"role": "assistant", "content": response})

    action_results = process_actions(response, root)
    while action_results:
        messages.append({"role": "user", "content": "\n\n---\n\n".join(action_results)})
        print(f"\n{BLUE}Agent:{NC} ", end="", flush=True)
        response = ollama_chat(messages, model, api_url, pretty=pretty)
        messages.append({"role": "assistant", "content": response})
        action_results = process_actions(response, root)

    return messages

# ── main ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Ollama wiki agent")
    ap.add_argument("--model", "-m", default=DEFAULT_MODEL)
    ap.add_argument("--url",         default=OLLAMA_API)
    ap.add_argument("--ctx", type=int, default=MAX_HISTORY,
                    help="Max conversation pairs in history")
    ap.add_argument("--pretty", action="store_true",  default=IS_TTY,
                    help="Render markdown as ANSI (default: on in terminal)")
    ap.add_argument("--raw",    action="store_true",  default=False,
                    help="Stream raw markdown, no ANSI rendering")
    args = ap.parse_args()
    pretty = args.pretty and not args.raw

    try:
        root = find_root()
    except FileNotFoundError as e:
        print(e); sys.exit(1)

    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        print("Error: AGENTS.md not found."); sys.exit(1)

    system_msg = {
        "role": "system",
        "content": agents_md.read_text(encoding="utf-8") + TOOL_INSTRUCTIONS,
    }

    print(f"\n{BOLD}Wiki agent{NC}  {DIM}{root.name}{NC}")
    mode = "pretty" if pretty else "raw"
    print(f"{DIM}Model: {args.model}   Python: {PYTHON}   Output: {mode}{NC}")
    print(f"{DIM}Loading context...{NC}\n")

    # initial context: status + index + recent log + open gaps
    ctx_parts = []
    ctx_parts.append(f"[python tools/status.py]\n{safe_run('python tools/status.py', root)}")

    for path in ("wiki/index.md", "wiki/log.md", "wiki/gaps.md"):
        p = root / path
        if p.exists():
            text = p.read_text(encoding="utf-8")
            if path == "wiki/log.md":
                text = "\n".join(text.splitlines()[-20:])  # last 20 lines only
            if path == "wiki/gaps.md" and "status: open" not in text:
                continue
            ctx_parts.append(f"[{path}]\n{text}")

    # pending sources: files in raw/sources/ without a wiki/sources/ summary
    pending = pending_sources(root)
    if pending:
        lines = "\n".join(f"  - {f}" for f in pending)
        ctx_parts.append(
            f"[Pending sources — in raw/sources/ but not yet ingested]\n{lines}"
        )
    else:
        ctx_parts.append("[Pending sources]\nAll sources have been ingested.")

    first_user = (
        "Session started. Current wiki state:\n\n"
        + "\n\n---\n\n".join(ctx_parts)
        + "\n\n---\n\n"
        "Confirm you have read the schema and the current state. "
        "Wait for my instructions."
    )

    messages = [system_msg, {"role": "user", "content": first_user}]

    print(f"{BOLD}{'─' * 60}{NC}")
    print(f"{BLUE}Agent:{NC} ", end="", flush=True)
    messages = agent_turn(messages, args.model, args.url, root, pretty=pretty)

    print(f"\n{DIM}Commands: /exit  /status  /history{NC}")

    while True:
        print(f"\n{BOLD}{'─' * 60}{NC}")
        try:
            user_input = input(f"{GREEN}You:{NC} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Session ended.{NC}"); break

        if not user_input:
            continue

        if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
            print(f"{DIM}Session ended.{NC}"); break

        if user_input.lower() == "/status":
            out = safe_run("python tools/status.py", root)
            print(out)
            continue  # don't send to model, just show locally

        if user_input.lower() == "/history":
            print(f"Messages in history: {len(messages) - 1}")
            continue

        messages = trim_history(messages, system_msg, args.ctx)
        messages.append({"role": "user", "content": user_input})
        print(f"\n{BLUE}Agent:{NC} ", end="", flush=True)
        messages = agent_turn(messages, args.model, args.url, root, pretty=pretty)


if __name__ == "__main__":
    main()
