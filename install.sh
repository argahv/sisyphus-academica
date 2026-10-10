#!/bin/bash
# Sisyphus Academica: interactive installer
# Installs the sisyphus CLI and the 25 OpenCode agents, writes .env, builds the voice profile.
#
# Usage: bash install.sh [--yes] [--dev] [--check]
#   --yes     Skip all prompts, use defaults (CLI-only when OpenCode is missing)
#   --dev     Also pip-install test and analysis dependencies
#   --check   Only validate an existing installation

set -euo pipefail

SISYPHUS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENCODE_CONFIG="${OPENCODE_CONFIG:-$HOME/.config/opencode}"
OPENCODE_AGENTS="${OPENCODE_AGENTS:-$OPENCODE_CONFIG/agents}"
OPENCODE_SKILLS="${OPENCODE_SKILLS:-$OPENCODE_CONFIG/skills}"
BIN_DIR="${SISYPHUS_BIN_DIR:-$HOME/.local/bin}"
S="$SISYPHUS_DIR/bin/sisyphus"

SKIP_PROMPTS=false
DEV=false
CHECK_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --yes) SKIP_PROMPTS=true ;;
        --dev) DEV=true ;;
        --check) CHECK_ONLY=true ;;
        *) echo "Unknown option: $arg"; exit 2 ;;
    esac
done

ask() {
    local var_name="$1" prompt="$2" default="${3:-}" input=""
    if [ "$SKIP_PROMPTS" = false ]; then
        local hint=""
        [ -n "$default" ] && hint=" [$default]"
        read -r -p "$prompt$hint: " input || true
    fi
    printf -v "$var_name" '%s' "${input:-$default}"
}

confirm() {
    local prompt="$1" default="${2:-y}" answer=""
    if [ "$SKIP_PROMPTS" = true ]; then
        [ "$default" = "y" ]
        return
    fi
    local hint="[Y/n]"
    [ "$default" = "n" ] && hint="[y/N]"
    read -r -p "$prompt $hint " answer || true
    case "${answer:-$default}" in
        [yY]|[yY][eE][sS]) return 0 ;;
        *) return 1 ;;
    esac
}

validate() {
    local errors=0
    echo "Validating installation..."
    if python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
        echo "  ✓ Python $(python3 -c 'import platform; print(platform.python_version())')"
    else
        echo "  ✗ Python 3.10+ is required"; errors=$((errors + 1))
    fi
    if "$S" --help >/dev/null 2>&1; then
        echo "  ✓ sisyphus CLI runs ($S)"
    else
        echo "  ✗ sisyphus CLI failed to start"; errors=$((errors + 1))
    fi
    command -v sisyphus >/dev/null 2>&1 && echo "  ✓ sisyphus on PATH" \
        || echo "  ⚠ sisyphus not on PATH (add $BIN_DIR to PATH, or use $S)"
    if command -v opencode >/dev/null 2>&1 || [ -d "$OPENCODE_AGENTS" ]; then
        if python3 "$SISYPHUS_DIR/tools/agents.py" --check --dest "$OPENCODE_AGENTS"; then :; else errors=$((errors + 1)); fi
    else
        echo "  - OpenCode agents not installed (CLI-only mode)"
    fi
    [ -f "$SISYPHUS_DIR/.env" ] && echo "  ✓ .env present" || echo "  ⚠ .env missing: run $S configure"
    if command -v latexmk >/dev/null 2>&1 || command -v pdflatex >/dev/null 2>&1; then
        echo "  ✓ LaTeX found"
    else
        echo "  ⚠ LaTeX not found: papers stop at .tex (or use: sisyphus build RUN --docker)"
    fi
    [ "$errors" -eq 0 ] && echo "  ✓ Validation passed" || echo "  ✗ $errors problem(s)"
    return "$errors"
}

if [ "$CHECK_ONLY" = true ]; then
    validate
    exit $?
fi

echo "Sisyphus Academica installer"
echo ""

# ------------------------------------------------------------------ interview
echo "[0/6] Setup questions"
python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null \
    || { echo "  ✗ Python 3.10+ is required (found: $(python3 --version 2>&1))"; exit 1; }

ask AUTHOR_NAME "  Your name (for CITATION.cff and paper bylines)" "${USER:-anonymous}"
if grep -q 'given-names: ""' "$SISYPHUS_DIR/CITATION.cff" 2>/dev/null; then
    FAMILY="${AUTHOR_NAME##* }"
    GIVEN="${AUTHOR_NAME% *}"
    [ "$GIVEN" = "$AUTHOR_NAME" ] && GIVEN=""
    python3 - "$SISYPHUS_DIR/CITATION.cff" "$FAMILY" "$GIVEN" <<'PY'
import re, sys
path, family, given = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
text = re.sub(r'family-names: ".*"', f'family-names: "{family}"', text, count=1)
text = re.sub(r'given-names: ".*"', f'given-names: "{given}"', text, count=1)
open(path, "w", encoding="utf-8").write(text)
PY
    echo "  ✓ CITATION.cff updated"
fi

PLATFORM="opencode"
if command -v opencode &>/dev/null; then
    echo "  ✓ OpenCode detected: $(opencode --version 2>/dev/null | head -1)"
else
    echo "  ⚠ OpenCode not found (https://opencode.ai/docs). Without it you get the CLI tools only."
    if confirm "  Continue with the CLI tools only?" "y"; then
        PLATFORM="manual"
    else
        echo "  → Install OpenCode, then re-run: bash install.sh"
        exit 0
    fi
fi

DEFAULT_MODEL=""
if [ "$PLATFORM" = "opencode" ]; then
    if [ ! -f "$OPENCODE_CONFIG/oh-my-openagent.json" ] && [ ! -f "$OPENCODE_CONFIG/oh-my-openagent.jsonc" ]; then
        echo "  - oh-my-openagent not detected (optional; agents work in plain OpenCode)"
    fi
    echo ""
    echo "  LLM provider (agents use provider/model strings from config/agent-config.json)"
    HAS_CLAUDE=false
    HAS_OPENAI=false
    confirm "  Do you use Anthropic (Claude) models?" "n" && HAS_CLAUDE=true
    confirm "  Do you use OpenAI models?" "n" && HAS_OPENAI=true
    if [ "$HAS_CLAUDE" = true ]; then
        DEFAULT_MODEL="anthropic/claude-sonnet-4"
    elif [ "$HAS_OPENAI" = true ]; then
        DEFAULT_MODEL="openai/gpt-4o"
        echo "  ⚠ The writer and novelty engines were tuned on Claude; expect more revision rounds."
    else
        echo "  → Keeping default_model from config/agent-config.json"
    fi
fi

echo ""
ask SEMANTIC_SCHOLAR_KEY "  Semantic Scholar API key (free, semanticscholar.org/product/api; enter to skip)" ""
ask CROSSREF_EMAIL "  Email for the CrossRef/OpenAlex polite pool (enter to skip)" ""

HAS_LATEX=false
if command -v latexmk &>/dev/null || command -v pdflatex &>/dev/null; then
    HAS_LATEX=true
    echo "  ✓ LaTeX detected"
elif command -v docker &>/dev/null; then
    echo "  ⚠ LaTeX not installed; Docker found. Build PDFs with: sisyphus build RUN --docker"
else
    echo "  ⚠ LaTeX not found. Papers will stop at .tex (install TeX Live for PDFs)."
fi

echo ""
echo "  Plan: platform=$PLATFORM  model=${DEFAULT_MODEL:-config default}  latex=$HAS_LATEX"
if ! confirm "  Proceed?" "y"; then
    echo "  → Aborted."
    exit 0
fi
echo ""

# ------------------------------------------------------------------ CLI
echo "[1/6] sisyphus CLI"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/sisyphus" <<EOF
#!/bin/sh
exec "$S" "\$@"
EOF
chmod +x "$BIN_DIR/sisyphus" "$S"
echo "  ✓ $BIN_DIR/sisyphus -> $S"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "  ⚠ Add $BIN_DIR to PATH to call 'sisyphus' directly" ;; esac
if [ "$DEV" = true ]; then
    python3 -m pip install -e "$SISYPHUS_DIR[dev,analysis]" \
        || echo "  ⚠ pip install failed; try a virtualenv: python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
fi

# ------------------------------------------------------------------ .env
echo "[2/6] Configuration"
CONFIGURE_ARGS=()
[ -n "$SEMANTIC_SCHOLAR_KEY" ] && CONFIGURE_ARGS+=(--semantic-scholar-key "$SEMANTIC_SCHOLAR_KEY")
[ -n "$CROSSREF_EMAIL" ] && CONFIGURE_ARGS+=(--crossref-email "$CROSSREF_EMAIL")
"$S" configure ${CONFIGURE_ARGS[@]+"${CONFIGURE_ARGS[@]}"} </dev/null | sed 's/^/  /'

# ------------------------------------------------------------------ skills
echo "[3/6] Writing skills"
if [ "$PLATFORM" = "opencode" ]; then
    mkdir -p "$OPENCODE_SKILLS/skill-academic-humanizer"
    cp "$SISYPHUS_DIR/skills/skill-academic-humanizer/SKILL.md" "$OPENCODE_SKILLS/skill-academic-humanizer/SKILL.md"
    echo "  ✓ skill-academic-humanizer (patterns 31-41)"
    if [ -f "$OPENCODE_SKILLS/humanizer/SKILL.md" ]; then
        echo "  ✓ humanizer already installed (patterns 1-30)"
    elif command -v git &>/dev/null && git clone --depth 1 https://github.com/blader/humanizer.git \
            "$OPENCODE_SKILLS/humanizer" >/dev/null 2>&1; then
        echo "  ✓ humanizer (patterns 1-30) from github.com/blader/humanizer"
    else
        echo "  ⚠ Could not clone blader/humanizer. The gates still check all 41 patterns in code;"
        echo "    writers lose the skill's examples. Retry: git clone https://github.com/blader/humanizer.git $OPENCODE_SKILLS/humanizer"
    fi
else
    echo "  - skipped (no OpenCode)"
fi

# ------------------------------------------------------------------ agents
echo "[4/6] Agents"
if [ "$PLATFORM" = "opencode" ]; then
    AGENT_ARGS=(--dest "$OPENCODE_AGENTS" --opencode-config "$OPENCODE_CONFIG")
    [ -n "$DEFAULT_MODEL" ] && AGENT_ARGS+=(--default-model "$DEFAULT_MODEL")
    python3 "$SISYPHUS_DIR/tools/agents.py" "${AGENT_ARGS[@]}"
    echo "  → Models come from config/agent-config.json; edit it and re-run install.sh to change them."
else
    echo "  - skipped (no OpenCode)"
fi

# ------------------------------------------------------------------ voice
echo "[5/6] Voice calibration"
if ls "$SISYPHUS_DIR"/data/voice-profile/*.txt >/dev/null 2>&1; then
    "$S" voice | sed 's/^/  /' || echo "  ⚠ Voice samples too short; add 2-3 paragraphs and run: sisyphus voice"
else
    echo "  - No samples. Optional: put 2-3 paragraphs of your published writing in"
    echo "    $SISYPHUS_DIR/data/voice-profile/sample.txt and run: sisyphus voice"
fi

# ------------------------------------------------------------------ check
echo "[6/6] Validation"
validate || true

echo ""
echo "Done."
echo "  Try the gates offline:  sisyphus demo"
if [ "$PLATFORM" = "opencode" ]; then
    echo "  Write a paper:          OpenCode → agent tab → research-director → \"write a paper about [topic]\""
    if [ "${HAS_CLAUDE:-false}" = true ] || [ "${HAS_OPENAI:-false}" = true ]; then
        echo "  Authenticate providers: opencode auth login"
    fi
fi
