# Product Requirements Document — llm-wiki

**Version**: 1.0  
**Date**: 2026-04-27  
**Status**: Active

---

## 1. Problem statement

Knowledge accumulation is broken in most teams and personal workflows.

Documents pile up in Google Drive, Notion, Confluence, Slack threads, email.
People re-derive the same information repeatedly. Institutional knowledge walks out the door
when someone leaves. Wikis get created and immediately start rotting — the maintenance burden
grows faster than the value, so no one maintains them.

Existing LLM document tools (RAG, NotebookLM, ChatGPT file uploads) don't solve this.
They re-derive answers from raw sources on every query. Nothing compounds.
Ask a question that requires synthesizing five documents and the system has to find and
piece together the fragments every time, with no memory of having done it before.

---

## 2. Solution

An LLM-maintained wiki that sits between raw sources and users.

When a source is added, the LLM integrates it into a persistent, interlinked wiki —
updating pages, flagging contradictions, maintaining cross-references.
The synthesis happens once and is kept current. Knowledge compounds.

When users ask questions, the agent answers from the wiki — with citations,
confidence levels, and automatic tracking of what it couldn't answer.

The human's job: curate sources, ask questions, direct the analysis.
The LLM's job: write and maintain everything else.

---

## 3. Target users

### Primary: IT teams at cloud provider companies

Teams that accumulate technical knowledge across infrastructure, services, clients,
incidents, and architecture decisions — and need it organized and queryable.

**Pain points:**
- Runbooks are outdated or nonexistent
- Architecture decisions aren't documented; tribal knowledge dominates
- New hires take months to get context
- Client requirements are scattered across emails and Slack
- Post-mortems get written and never referenced again

### Secondary: Individual knowledge workers

People who read, research, and want their accumulated knowledge organized.
Books, papers, articles, notes — all integrated into a single queryable knowledge base.

---

## 4. Use cases

### UC-1: Internal documentation agent
An AI agent answers employee questions (Slack bot, internal chat) using the wiki
as its knowledge base. Questions it can't answer are logged as gaps and drive
the next documentation sprint.

### UC-2: Onboarding acceleration
New engineers get context by querying the wiki. Architecture decisions have rationale.
Services have ownership and runbooks. The wiki is the onboarding document.

### UC-3: Incident response
On-call engineer asks the agent: "What's the runbook for this alert?"
The agent finds and presents the relevant runbook, flagging if it's expired.

### UC-4: Technical research
Engineer researching a migration (e.g., Terraform → Pulumi) ingests docs, RFCs,
and blog posts. The wiki builds up a structured comparison over time.

### UC-5: Client knowledge base
Account managers ingest client contracts, meeting notes, requirement docs.
The wiki maintains a per-client entity page with current requirements, SLAs, contacts.

### UC-6: Personal research wiki
Individual ingests papers, books, and articles over months.
Builds a comprehensive wiki on a topic — with the LLM doing all cross-referencing.

---

## 5. Functional requirements

### F-1: Source ingestion
- Accept PDF, markdown, HTML, and plain text as source formats
- Extract text from PDF and HTML before LLM processing
- Sources are immutable; LLM never modifies `raw/`
- Sources named with date prefix for chronological ordering

### F-2: Wiki maintenance
- LLM creates and updates pages in `wiki/`
- Every page has YAML frontmatter (type, tags, status, dates, source count)
- Cross-references maintained via `[[WikiLink]]` format (Obsidian-compatible)
- Time-sensitive pages have `valid_until` date; expired pages flagged at lint

### F-3: Query — interactive
- LLM searches wiki, synthesizes answer, cites pages
- Can save useful answers as new analysis pages

### F-4: Query — user-facing (agent mode)
- Conservative: never invent, always cite, always state confidence
- Four confidence levels: HIGH / MEDIUM / LOW / NONE
- Warns users when citing pages past their `valid_until` date
- Unanswered questions logged to `wiki/gaps.md`

### F-5: Gap tracking
- `gaps.md`: append-only log of questions with no HIGH/MEDIUM answer
- Each gap has priority (high/medium/low) and status (open/resolved)
- Lint pass reviews gaps and suggests ingestions to resolve them

### F-6: Health check (lint)
- Detect: orphan pages, broken links, missing frontmatter, expired pages
- Surface: open gaps, expiring-soon pages
- Suggest: sources to ingest, concepts to document

### F-7: CLI tools
- `status.py` — session dashboard
- `search.py` — BM25 full-text search
- `lint.py` — health check
- `gaps.py` — gap viewer
- `new.py` — page scaffold
- `extract.py` — PDF/HTML to markdown

### F-8: Obsidian integration
- Pre-configured vault settings (attachment folder, link format)
- Frontmatter compatible with Dataview plugin
- Output format supports Marp slides

### F-9: Multi-LLM compatibility
- `CLAUDE.md` for Claude Code
- `AGENTS.md` (identical) for OpenAI Codex and others
- CLI tools are pure Python, no LLM dependency
- Schema is plain markdown — readable by any instruction-following LLM

### F-10: Setup and distribution
- Single `setup.sh` script: interactive, creates complete repo, initializes git
- Supports work (IT cloud provider) and personal wiki types
- Works on macOS; no external services required

---

## 6. Non-functional requirements

### NFR-1: Offline capable
All tools and the wiki itself work without internet connectivity.
Designed for use with local LLMs (Ollama) as well as cloud LLMs.

### NFR-2: No infrastructure dependencies
No database, no vector store, no embedding model required.
BM25 search runs in-process. The wiki is a directory of markdown files.

### NFR-3: LLM token efficiency
`wiki/index.md` is the navigation layer — the LLM reads it first, then drills into
specific pages. Avoids loading the entire wiki into context.

### NFR-4: Portable
The generated wiki is a git repo of plain text files.
Works with any git host, any editor, any LLM frontend.

### NFR-5: Incrementally adoptable
Every component is optional. No search engine? The index file is enough.
No Obsidian? Plain markdown editors work. No slides? Skip Marp.

### NFR-6: Security
- Source content treated as untrusted data (prompt injection resistance)
- Sensitive wiki sections reviewed before sharing
- Expiry tracking prevents agents from citing stale information confidently
- File size limits on source extraction

---

## 7. Out of scope (v1)

- **Automatic re-ingestion**: sources are processed on explicit request only
- **Real-time collaboration**: wiki is single-writer (the LLM); human PRs are out of scope
- **Embedding-based search**: BM25 is sufficient at target scale (~100s of pages)
- **Access control**: no per-page permissions; security is at the repo level
- **Multi-wiki cross-references**: personal and work wikis are separate repos
- **Web UI**: Obsidian is the UI; no custom frontend
- **Automatic source discovery**: human curates what goes in `raw/sources/`

---

## 8. Success metrics

| Metric | Target |
|--------|--------|
| Setup time for a new colleague | < 10 minutes |
| Questions answered with HIGH confidence after 20 sources ingested | > 70% |
| Open gaps resolved within 1 lint cycle | > 50% |
| Pages with broken links after lint | 0 |
| Expired pages surfaced before agent cites them | 100% |
| Works offline with Ollama | Yes |

---

## 9. Open questions

1. **MCP server** — should the wiki expose an MCP server so LLMs can use tools natively instead of via shell? High value for Ollama use case.
2. **URL clipper** — should `tools/clip.py` automate downloading a URL to `raw/sources/`? Reduces friction for web sources.
3. **Multi-wiki linking** — should personal and work wikis be able to cross-reference? Adds complexity; deferred.
4. **Diff tool** — `tools/diff.py` showing what changed in the wiki between two dates. Low effort, useful for team awareness.
