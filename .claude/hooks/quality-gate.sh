#!/usr/bin/env bash
#
# Shared pre-commit quality gate logic.
# Used by the Claude Code PreToolUse hook and the optional .githooks/pre-commit.
#
# Resolves ruff/pytest from .venv/bin first — .venv/ is gitignored and must
# exist locally for any commit that needs them. Missing tools fail closed.
#
# Usage: quality-gate.sh [repo_root]
# Exit 0 on pass, 1 on fail. Human-readable messages (and tool output) go to stderr.

set -uo pipefail

CWD="${1:-.}"
ERRORS=""

resolve_tool() {
    local name="$1"
    if [ -x "$CWD/.venv/bin/$name" ]; then
        echo "$CWD/.venv/bin/$name"
    elif command -v "$name" > /dev/null 2>&1; then
        command -v "$name"
    fi
}

# Check 1: ruff — only when Python files are staged; fail closed if missing.
HAS_STAGED_PY=0
if (cd "$CWD" && git diff --cached --name-only --diff-filter=ACMR -- '*.py' 2>/dev/null | grep -q .); then
    HAS_STAGED_PY=1
fi

if [ "$HAS_STAGED_PY" -eq 1 ]; then
    RUFF=$(resolve_tool ruff)
    if [ -z "$RUFF" ]; then
        ERRORS="${ERRORS}ruff unavailable (install .venv or put ruff on PATH). "
    else
        echo "=== ruff check (staged Python) ===" >&2
        if ! (cd "$CWD" && git diff --cached -z --name-only --diff-filter=ACMR -- '*.py' | xargs -0 "$RUFF" check); then
            ERRORS="${ERRORS}ruff check failed on staged Python files. "
        fi
    fi
fi

# Check 2: pytest — full suite, skipped only when every changed path is Markdown.
# Staged and unstaged changes both count (so `git commit -a` can't sneak Python
# past the skip), renames count by both names, and CSV/JSON always run tests
# because tests read curation data.
DOCS_ONLY=1
CHANGED=$(cd "$CWD" && { git diff --cached --name-only --no-renames; git diff --name-only --no-renames; } 2>/dev/null)
if [ -z "$CHANGED" ] || grep -qvE '\.(md|mdc)$' <<<"$CHANGED"; then
    DOCS_ONLY=0
fi

PYTEST=$(resolve_tool pytest)
if [ "$DOCS_ONLY" -eq 1 ]; then
    echo "=== pytest skipped: only Markdown changed ===" >&2
elif [ -z "$PYTEST" ]; then
    ERRORS="${ERRORS}pytest unavailable (install .venv or put pytest on PATH). "
else
    echo "=== pytest ===" >&2
    if ! (cd "$CWD" && "$PYTEST" --tb=short -q); then
        ERRORS="${ERRORS}pytest failed. "
    fi
fi

if [ -n "$ERRORS" ]; then
    echo "Pre-commit quality gate failed: ${ERRORS}Fix issues before committing." >&2
    exit 1
fi

exit 0
