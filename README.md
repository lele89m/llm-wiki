# llm-wiki

A template for building AI-maintained knowledge bases.
Drop documents in, ask questions. The LLM writes and maintains all wiki pages.
Works with Claude Code, Ollama, OpenAI Codex, and any instruction-following LLM.

---

## The idea

Most LLM + document systems re-derive knowledge from scratch on every query (RAG).
This is different: the LLM **builds a persistent wiki** from your sources and keeps it current.

When you add a source, the LLM reads it, extracts what matters, and integrates it into the
existing wiki — updating entity pages, flagging contradictions, maintaining cross-references.
The wiki compounds over time. Answers are fast because the synthesis already happened.

When used as an agent backend, the wiki is the knowledge base the agent answers from —
with source citations, confidence levels, and automatic gap tracking for unanswered questions.

---

## Quickstart

```bash
git clone <this-repo> llm-wiki
cd llm-wiki
bash setup.sh
```

Creates a fully configured wiki repo — work or personal — then open it with your LLM.

**With Claude Code:**
```bash
cd your-wiki && claude
# Tell it: "Read CLAUDE.md and run python3 tools/status.py"
```

**With Ollama (opencode, open-webui, aider):**
```bash
# Open your-wiki/ as context. Load CLAUDE.md as the system prompt.
```

---

## What gets created

```
your-wiki/
├── CLAUDE.md          # LLM schema: workflows, conventions, confidence protocol
├── AGENTS.md          # Same schema for OpenAI Codex / other agents
├── wiki/
│   ├── index.md       # Master page catalog — LLM reads this to navigate
│   ├── log.md         # Append-only operation log
│   ├── overview.md    # High-level synthesis
│   ├── gaps.md        # Questions the agent couldn't answer (auto-maintained)
│   └── _templates/    # Page scaffolds (entity, concept, decision, runbook...)
├── raw/
│   ├── assets/        # Images — set as Obsidian attachment folder
│   └── sources/       # Your source documents (PDF, MD, HTML) — immutable
└── tools/
    ├── status.py      # Session dashboard — run at start of every session
    ├── search.py      # BM25 full-text search over wiki pages
    ├── lint.py        # Health check: orphans, broken links, expiry dates
    ├── gaps.py        # Show unanswered user questions by priority
    ├── new.py         # Scaffold a new page from template
    └── extract.py     # Convert PDF/HTML to markdown for ingestion
```

---

## LLM compatibility

| LLM / Tool | How to use |
|------------|------------|
| **Claude Code** | `cd your-wiki && claude` — reads `CLAUDE.md` automatically |
| **Ollama** | Load `CLAUDE.md` as system prompt in your frontend |
| **OpenAI Codex** | Uses `AGENTS.md` (identical content) |
| **Aider** | `aider --read CLAUDE.md` inside the wiki directory |
| **Open WebUI** | Add wiki directory as knowledge, paste `CLAUDE.md` as system prompt |

The schema files are plain markdown — any capable LLM can follow them.

---

## Wiki types

### Work — IT cloud provider

Pre-configured categories and domain context for cloud infrastructure companies:

| Category | Contents |
|----------|----------|
| `architecture/` | Cloud patterns, system design, multi-cloud |
| `services/` | Internal services and APIs |
| `technologies/` | Kubernetes, Terraform, Prometheus, etc. |
| `infrastructure/` | IaC, networking, compute, storage, security |
| `clients/` | Client profiles and requirements |
| `projects/` | Ongoing and past projects |
| `incidents/` | Post-mortems and runbooks |
| `team/` | People, roles, processes |
| `vendors/` | Third-party providers, SLAs |
| `decisions/` | Architecture Decision Records (ADRs) |
| `concepts/` | Domain concepts and definitions |

### Personal

Categories: goals, health, psychology, reading, projects, people, learnings, journal.

---

## Agent mode — answering user questions

The wiki is designed to be the knowledge base for an AI agent that answers user questions.

The schema defines two query modes:

- **Interactive** — human exploring the wiki, can save new analysis pages
- **User-facing** — conservative mode for end users: cite sources, assess confidence, log gaps

**Confidence protocol:**

| Level | Condition | Agent behavior |
|-------|-----------|----------------|
| HIGH | 2+ pages cover the topic | Answer with citations |
| MEDIUM | Partial coverage | Answer + flag incomplete coverage |
| LOW | Tangential info only | Answer cautiously, flag uncertainty |
| NONE | No relevant pages | Refuse to guess, log to `gaps.md` |

Unanswered questions accumulate in `wiki/gaps.md` and drive future ingestion priorities.

---

## Source ingestion

Drop any file in `raw/sources/` — the name can be anything:

```
raw/sources/architecture-overview.md
raw/sources/report.pdf
raw/sources/meeting-notes.html
```

A date prefix is optional but recommended for chronological sorting:

```
raw/sources/2026-04-27-architecture-overview.md
```

Tell the LLM: `"Ingest raw/sources/architecture-overview.md"`

The LLM extracts key information, writes a source summary, updates related wiki pages,
and appends to the log. A single source typically touches 5–15 wiki pages.

**Extract PDF/HTML before ingesting** (needed for Ollama and non-multimodal LLMs):
```bash
python3 tools/extract.py raw/sources/report.pdf -o /tmp/report.md
```

---

## Tools reference

```bash
# Start of session
python3 tools/status.py

# Search before creating pages (avoid duplicates)
python3 tools/search.py "kubernetes networking" --limit 5

# Scaffold a new page
python3 tools/new.py concept "Zero Trust Networking"
python3 tools/new.py runbook "Drain a Kubernetes node"

# Health check
python3 tools/lint.py

# Review gaps (unanswered user questions)
python3 tools/gaps.py
python3 tools/gaps.py --priority high

# Extract source file to text
python3 tools/extract.py raw/sources/report.pdf -o /tmp/report.md
```

---

## Obsidian integration

Open `your-wiki/` as a vault. Settings are pre-configured in `.obsidian/app.json`:
- Attachments → `raw/assets/`
- New notes → `wiki/`
- Links → `[[WikiLink]]` format

**Recommended plugins:**
- **Dataview** — live queries over page frontmatter (tables, lists, counts)
- **Marp Slides** — render slide decks from wiki pages
- **Obsidian Web Clipper** (browser extension) — clip web articles as markdown to `raw/sources/`

---

## Python dependencies

```bash
pip3 install -r requirements.txt

# PDF support (install one):
pip3 install pymupdf4llm    # best: clean markdown output
pip3 install pymupdf        # fallback: plain text

# Better HTML extraction (optional):
pip3 install beautifulsoup4
```

---

## Security

- **Never commit secrets** — credentials, tokens, or API keys must not appear in `raw/sources/`
- **Prompt injection** — source files may contain adversarial content; the LLM schema instructs the agent to treat source content as data, not instructions
- **Sensitive data** — `wiki/clients/` and `wiki/team/` may contain confidential information; review before pushing to shared repositories
- **Expiry tracking** — set `valid_until` in frontmatter for time-sensitive pages (SLAs, runbooks, pricing); `lint.py` flags expired and soon-expiring pages

---

## Customizing for your domain

The template ships with IT cloud provider and personal wiki types.
For other domains (legal, medical, research, startup...) see **[CUSTOMIZATION.md](CUSTOMIZATION.md)** —
step-by-step guide with four complete examples showing what to change in `CLAUDE.md`.

---

## Sharing with colleagues

This repo is the template. Each colleague runs `bash setup.sh` to create their own wiki.
To share a **work wiki** with the team, push the generated `work-wiki/` repo to an internal
git host. Each person clones it and opens it in their LLM tool of choice.

The wiki is just a git repo of markdown files — branching, PRs, and history work as expected.
