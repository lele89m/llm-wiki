# Using llm-wiki with Ollama

This guide covers how to use your wiki with a local Ollama model.
There are two approaches depending on what you want:

| Approach | When to use |
|----------|-------------|
| **`tools/chat.py`** | Full agent: model can read files, run tools, write wiki pages |
| **Manual system prompt** | Any Ollama frontend (open-webui, aider, opencode) — read-only |

---

## Prerequisites

1. **Ollama installed and running**
   ```bash
   # macOS
   brew install ollama
   ollama serve          # start in a separate terminal (or it starts automatically)
   ```

2. **A model pulled**
   ```bash
   ollama pull qwen2.5:7b           # default — good balance of speed and quality
   ollama pull qwen2.5-coder:7b     # better for structured output and following schemas
   ollama pull llama3.2:3b          # lighter, faster, weaker on complex tasks
   ```

3. **Python dependencies installed** (done by `setup.sh`, or manually):
   ```bash
   pip install rank-bm25 PyYAML
   ```

---

## Approach 1 — `tools/chat.py` (recommended)

`chat.py` is an interactive agent loop that gives the model full access to your wiki:
- **Read** any file in the wiki repo
- **Run** the wiki tools (`status.py`, `search.py`, `lint.py`, `new.py`, `gaps.py`, `diff.py`)
- **Write** files inside `wiki/` (sandboxed — cannot touch `raw/`, `tools/`, or root files)

The model receives `AGENTS.md` as its system prompt, plus the current wiki state
(status, index, last log entries, open gaps) as initial context at the start of every session.

### Start a session

```bash
cd your-wiki
python3 tools/chat.py                        # uses qwen2.5:7b by default
python3 tools/chat.py --model qwen2.5-coder:7b
python3 tools/chat.py --model llama3.2:3b
python3 tools/chat.py --url http://other-host:11434/api/chat   # remote Ollama
```

### Session commands

| Command | What it does |
|---------|-------------|
| `/status` | Print wiki stats locally (does not send to model) |
| `/history` | Show number of messages in current context |
| `/exit` or `/quit` | End session |

### How the agent works

When you ask something, the model can emit action tags in its response:

```
<read>wiki/index.md</read>
<run>python tools/search.py "kubernetes" --limit 5</run>
<write path="wiki/concepts/kubernetes.md">...content...</write>
```

`chat.py` intercepts these tags, executes the actions, and feeds the results back to
the model — which then continues its response. This loop repeats until the model stops
emitting action tags.

**Safety constraints built into `chat.py`:**
- `<read>` — restricted to paths inside the wiki repo root (no path traversal)
- `<run>` — only `python tools/` commands are allowed; nothing else executes
- `<write>` — restricted to `wiki/` only; `raw/`, `tools/`, `_templates/`, `_templater/` are blocked
- Tags inside code blocks (``` fences) are never executed — only bare tags are acted on

### Context window management

Local models have smaller context windows than cloud APIs. `chat.py` trims conversation
history automatically, keeping the last 20 message pairs by default. You can adjust this:

```bash
python3 tools/chat.py --ctx 10    # keep only last 10 pairs (less memory, less coherence)
python3 tools/chat.py --ctx 30    # keep more history (needs a larger context model)
```

For models with a 4K context (`llama3.2:3b`), use `--ctx 8` or lower.
For models with 32K+ context (`qwen2.5:7b`, `qwen2.5-coder:7b`), the default of 20 is fine.

---

## Approach 2 — Manual system prompt (any frontend)

If you prefer open-webui, aider, or another interface, load `AGENTS.md` as the system
prompt. The model will follow the wiki schema but won't be able to execute tools or
write files automatically — you copy-paste outputs manually.

### Aider

```bash
cd your-wiki
aider --model ollama/qwen2.5:7b --read AGENTS.md
```

### Open WebUI

1. Open **Workspace → System Prompts**
2. Paste the contents of `AGENTS.md`
3. Set the wiki directory as a knowledge source (or paste relevant pages manually)

### opencode / other CLIs

Load `AGENTS.md` as the system prompt. Point the context at your wiki directory
so the tool can read files. Tool execution is not supported without `chat.py`.

---

## Model recommendations

`chat.py` works best with models that follow structured instructions reliably.

| Model | Context | Notes |
|-------|---------|-------|
| `qwen2.5:7b` | 32K | Default. Good instruction following, handles the schema well. |
| `qwen2.5-coder:7b` | 32K | Better at structured output and YAML frontmatter. Recommended. |
| `qwen2.5:14b` | 32K | Stronger reasoning, slower. Worth it for complex ingestions. |
| `llama3.2:3b` | 4K | Fast and light. Struggles with long wiki pages and multi-step tasks. |
| `mistral:7b` | 8K | Decent, but less reliable on the action tag format. |

Smaller models (3b–7b) may occasionally emit action tags inside code fences or
produce malformed YAML frontmatter. If that happens, use a larger model.

---

## Limitations compared to Claude Code

| Feature | `chat.py` + Ollama | Claude Code |
|---------|-------------------|-------------|
| Read files | Yes | Yes |
| Run tools | Yes (`python tools/` only) | Yes (full shell) |
| Write wiki pages | Yes (`wiki/` only) | Yes (any file) |
| Read images/PDFs directly | No — use `extract.py` first | Yes (multimodal) |
| Context window | 4K–32K depending on model | 200K |
| Cost | Free (local) | API usage |

For PDF and HTML sources, always extract to text before the session:

```bash
python3 tools/extract.py raw/sources/report.pdf -o /tmp/report.md
# then in chat.py: ask the model to read /tmp/report.md
```

---

## Troubleshooting

**`Error: cannot reach Ollama at http://localhost:11434`**
Ollama is not running. Start it with `ollama serve`.

**Model produces garbled or incomplete responses**
Reduce `--ctx` to free up context space, or switch to a larger model.

**Model emits action tags inside code blocks and they don't execute**
This is intentional — tags inside ``` fences are ignored for safety.
The model should be instructed to emit bare tags, not examples.

**`[ERROR] Only 'python tools/' commands are allowed`**
The model tried to run a command outside the allowed whitelist. This is a safety
guard. Prompt the model to use only the provided wiki tools.
