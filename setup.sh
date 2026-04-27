#!/usr/bin/env bash
# LLM Wiki — setup script
# Creates a new work or personal wiki repo from the template.
# Usage: bash setup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON="$SCRIPT_DIR/templates/common"

# ── colors ───────────────────────────────────────────────────────────────────
R='\033[0;31m'; G='\033[0;32m'; Y='\033[1;33m'; B='\033[0;34m'
BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

ok()   { echo -e "  ${G}✓${NC} $*"; }
warn() { echo -e "  ${Y}⚠${NC}  $*"; }
err()  { echo -e "  ${R}✗${NC} $*"; }
hdr()  { echo -e "\n${BOLD}$*${NC}"; }

# ── banner ───────────────────────────────────────────────────────────────────
banner() {
cat <<'EOF'

  ██╗     ██╗     ███╗   ███╗    ██╗    ██╗██╗██╗  ██╗██╗
  ██║     ██║     ████╗ ████║    ██║    ██║██║██║ ██╔╝██║
  ██║     ██║     ██╔████╔██║    ██║ █╗ ██║██║█████╔╝ ██║
  ██║     ██║     ██║╚██╔╝██║    ██║███╗██║██║██╔═██╗ ██║
  ███████╗███████╗██║ ╚═╝ ██║    ╚███╔███╔╝██║██║  ██╗██║
  ╚══════╝╚══════╝╚═╝     ╚═╝     ╚══╝╚══╝ ╚═╝╚═╝  ╚═╝╚═╝

EOF
  echo -e "  ${B}LLM-powered personal knowledge base${NC}"
  echo -e "  ${DIM}Works with Claude Code, Ollama, OpenAI Codex, and more${NC}"
  echo
}

# ── dependency check ─────────────────────────────────────────────────────────
check_deps() {
  hdr "Checking dependencies..."
  local failed=0

  if command -v python3 &>/dev/null; then
    local minor
    minor=$(python3 -c 'import sys; print(sys.version_info.minor)')
    local major
    major=$(python3 -c 'import sys; print(sys.version_info.major)')
    if [[ "$major" -ge 3 && "$minor" -ge 8 ]]; then
      ok "Python $(python3 --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
    else
      err "Python 3.8+ required (found $(python3 --version))"
      failed=1
    fi
  else
    err "python3 not found — install from https://python.org"
    failed=1
  fi

  if command -v git &>/dev/null; then
    ok "git $(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
  else
    err "git not found"
    failed=1
  fi

  if [[ $failed -eq 1 ]]; then
    echo -e "\n${R}Install missing dependencies and re-run setup.${NC}"
    exit 1
  fi
}

# ── pick wiki type ────────────────────────────────────────────────────────────
ask_type() {
  hdr "Wiki type:"
  echo "  1) Work     — technical and company knowledge base"
  echo "  2) Personal — personal notes, research, self-knowledge"
  echo
  while true; do
    read -rp "  Choose [1/2]: " choice
    case "$choice" in
      1) WIKI_TYPE="work";     break ;;
      2) WIKI_TYPE="personal"; break ;;
      *) warn "Please enter 1 or 2." ;;
    esac
  done
}

# ── pick target directory ─────────────────────────────────────────────────────
ask_target() {
  local default="${WIKI_TYPE}-wiki"
  echo
  read -rp "  Target directory [${default}]: " raw_target
  local target="${raw_target:-$default}"

  # make absolute
  if [[ "$target" != /* ]]; then
    TARGET_DIR="$(pwd)/$target"
  else
    TARGET_DIR="$target"
  fi

  if [[ -d "$TARGET_DIR" ]] && [[ -n "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]]; then
    warn "Directory exists and is not empty: $TARGET_DIR"
    read -rp "  Continue anyway? [y/N]: " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
  fi
}

# ── create directory tree ─────────────────────────────────────────────────────
create_dirs() {
  hdr "Creating wiki structure..."
  mkdir -p "$TARGET_DIR"/{tools,"raw/assets","raw/sources","wiki/_templates","wiki/_charts"}

  if [[ "$WIKI_TYPE" == "work" ]]; then
    mkdir -p "$TARGET_DIR/wiki"/{architecture,services,technologies,infrastructure,clients,projects,incidents,team,vendors,decisions,concepts,sources,analysis}
  else
    mkdir -p "$TARGET_DIR/wiki"/{goals,health,psychology,reading,projects,people,learnings,journal,sources,analysis}
  fi

  # keep empty dirs in git
  touch "$TARGET_DIR/raw/assets/.gitkeep"
  touch "$TARGET_DIR/raw/sources/.gitkeep"
  touch "$TARGET_DIR/wiki/_charts/.gitkeep"

  ok "directories"
}

# ── copy template files ───────────────────────────────────────────────────────
copy_files() {
  local type_tpl="$SCRIPT_DIR/templates/$WIKI_TYPE"

  # LLM schema files
  cp "$type_tpl/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
  cp "$type_tpl/CLAUDE.md" "$TARGET_DIR/AGENTS.md"   # alias for Codex / other agents
  ok "CLAUDE.md + AGENTS.md"

  # wiki skeleton
  cp "$COMMON/wiki/index.md"    "$TARGET_DIR/wiki/index.md"
  cp "$COMMON/wiki/log.md"      "$TARGET_DIR/wiki/log.md"
  cp "$COMMON/wiki/overview.md" "$TARGET_DIR/wiki/overview.md"
  cp "$COMMON/wiki/gaps.md"     "$TARGET_DIR/wiki/gaps.md"
  cp "$COMMON/wiki/_templates/"* "$TARGET_DIR/wiki/_templates/"
  ok "wiki pages"

  # tools
  cp "$COMMON/tools/search.py"  "$TARGET_DIR/tools/search.py"
  cp "$COMMON/tools/lint.py"    "$TARGET_DIR/tools/lint.py"
  cp "$COMMON/tools/extract.py" "$TARGET_DIR/tools/extract.py"
  cp "$COMMON/tools/status.py"  "$TARGET_DIR/tools/status.py"
  cp "$COMMON/tools/new.py"     "$TARGET_DIR/tools/new.py"
  cp "$COMMON/tools/gaps.py"    "$TARGET_DIR/tools/gaps.py"
  cp "$COMMON/tools/diff.py"    "$TARGET_DIR/tools/diff.py"
  cp "$COMMON/tools/chat.py"    "$TARGET_DIR/tools/chat.py"
  chmod +x "$TARGET_DIR/tools/"*.py
  ok "tools (search, lint, extract, status, new, gaps, diff, chat)"

  # requirements
  cp "$COMMON/requirements.txt" "$TARGET_DIR/requirements.txt"

  # obsidian config + templater plugin
  mkdir -p "$TARGET_DIR/.obsidian/plugins/templater-obsidian"
  cp "$COMMON/obsidian/app.json" "$TARGET_DIR/.obsidian/app.json"
  cp "$COMMON/obsidian/plugins/templater-obsidian/data.json" \
     "$TARGET_DIR/.obsidian/plugins/templater-obsidian/data.json"
  ok "Obsidian config + Templater plugin config"

  # templater page templates
  cp -r "$COMMON/wiki/_templater/." "$TARGET_DIR/wiki/_templater/"
  ok "Templater page templates (wiki/_templater/)"

  # gitignore
  cat > "$TARGET_DIR/.gitignore" <<'GITIGNORE'
.DS_Store
__pycache__/
*.pyc
*.pyo
.env
venv/
.venv/
*.egg-info/
/dist/
GITIGNORE
  ok ".gitignore"
}

# ── git init ──────────────────────────────────────────────────────────────────
init_git() {
  git -C "$TARGET_DIR" init -q
  git -C "$TARGET_DIR" add -A
  git -C "$TARGET_DIR" commit -q -m "chore: initial wiki setup (llm-wiki template)"
  ok "git repository initialised"
}

# ── python deps ───────────────────────────────────────────────────────────────
install_deps() {
  echo
  read -rp "  Install Python dependencies now? [Y/n]: " confirm
  [[ "$confirm" =~ ^[Nn]$ ]] && { warn "Skipped — run later: pip install -r requirements.txt"; return; }

  echo
  # try uv first (fast, handles managed envs), then pip --user, then plain pip
  if command -v uv &>/dev/null; then
    uv pip install -q -r "$TARGET_DIR/requirements.txt" 2>/dev/null \
      && { ok "Python dependencies (via uv)"; return; }
  fi

  if python3 -m pip install -q --user -r "$TARGET_DIR/requirements.txt" 2>/dev/null; then
    ok "Python dependencies (--user)"
  elif python3 -m pip install -q -r "$TARGET_DIR/requirements.txt" 2>/dev/null; then
    ok "Python dependencies"
  else
    warn "Auto-install failed (externally managed env)."
    warn "Run manually inside a venv:"
    warn "  python3 -m venv ${TARGET_DIR}/.venv"
    warn "  source ${TARGET_DIR}/.venv/bin/activate"
    warn "  pip install -r ${TARGET_DIR}/requirements.txt"
  fi
}

# ── next steps ────────────────────────────────────────────────────────────────
print_next_steps() {
  local short_target="${TARGET_DIR/#$HOME/~}"

  echo
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${G}${BOLD}  Wiki created: ${short_target}${NC}"
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  echo
  hdr "Obsidian setup"
  echo "  1. Open Obsidian → 'Open folder as vault' → ${B}${short_target}${NC}"
  echo "  2. Settings are pre-configured (.obsidian/app.json)."
  echo "     Verify: Files & links → Attachment folder = raw/assets"
  echo "  3. Install community plugins:"
  echo "     • ${BOLD}Templater${NC}  — page templates with auto date/title (config pre-loaded)"
  echo "       After install: Settings → Templater → Template folder = wiki/_templater"
  echo "       Then: Cmd+P → 'Templater: Insert Template' to create a new page"
  echo "     • ${BOLD}Dataview${NC}   — query frontmatter as live tables"
  echo "     • ${BOLD}Marp Slides${NC} — render slide decks from markdown"
  echo "     • ${BOLD}Obsidian Web Clipper${NC} (browser ext) — clip articles as markdown"

  echo
  hdr "Start the wiki with your LLM"
  echo
  echo -e "  ${B}Claude Code:${NC}"
  echo -e "    cd ${short_target} && claude"
  echo
  echo -e "  ${B}Ollama — built-in agent wrapper:${NC}"
  echo -e "    cd ${short_target}"
  echo -e "    python tools/chat.py --model qwen2.5:7b"
  echo -e "    ${DIM}# Loads AGENTS.md + wiki state. Model can read files and run tools.${NC}"
  echo
  echo -e "  ${B}Ollama — other frontends:${NC}"
  echo -e "    aider --model ollama/qwen2.5:7b --read AGENTS.md"
  echo
  echo -e "  ${B}First things to say to the agent:${NC}"
  echo -e '    "Ingest raw/sources/<filename>"'
  echo -e '    "What do we know about <topic>?"'
  echo -e '    "Run a lint check on the wiki."'

  echo
  echo -e "  ${DIM}Tools:${NC}"
  echo -e "  ${DIM}  python tools/status.py                          # dashboard${NC}"
  echo -e "  ${DIM}  python tools/search.py \"<query>\"                # search pages${NC}"
  echo -e "  ${DIM}  python tools/lint.py                            # health check${NC}"
  echo -e "  ${DIM}  python tools/gaps.py                            # open knowledge gaps${NC}"
  echo -e "  ${DIM}  python tools/diff.py                            # changelog last 7 days${NC}"
  echo -e "  ${DIM}  python tools/diff.py --days 30                  # changelog last 30 days${NC}"
  echo -e "  ${DIM}  python tools/new.py concept \"Title\"             # scaffold page${NC}"
  echo -e "  ${DIM}  python tools/extract.py raw/sources/<file> -o /tmp/out.md${NC}"
  echo
  hdr "Raw sources naming convention"
  echo "  Name files with a date prefix so they sort chronologically:"
  echo -e "  ${DIM}  YYYY-MM-DD-title.md   (articles, notes)${NC}"
  echo -e "  ${DIM}  YYYY-MM-DD-title.pdf  (reports, papers)${NC}"
  echo -e "  ${DIM}  YYYY-MM-DD-title.html (web pages)${NC}"
  echo
}

# ── main ──────────────────────────────────────────────────────────────────────
banner
check_deps
ask_type
ask_target
create_dirs
copy_files
init_git
install_deps
print_next_steps
