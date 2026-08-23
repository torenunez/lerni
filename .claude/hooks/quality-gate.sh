#!/usr/bin/env bash
#
# Shared pre-commit quality gate logic.
# Used by the Claude Code PreToolUse hook and the optional .githooks/pre-commit.
#
# Resolves ruff/pytest from .venv/bin first — .venv/ is gitignored and must
# exist locally. Exits 0 when tools are absent (warns) rather than failing closed.
#
# Usage: quality-gate.sh [repo_root]
# Exit 0 on pass, 1 on fail. Human-readable messages go to stderr.

set -uo pipefail

CWD="${1:-.}"
ERRORS=""
NOTES=""

resolve_tool() {
    local name="$1"
    if [ -x "$CWD/.venv/bin/$name" ]; then
        echo "$CWD/.venv/bin/$name"
    elif command -v "$name" > /dev/null 2>&1; then
        command -v "$name"
    fi
}

STAGED_PY=$(cd "$CWD" && git diff --cached --name-only --diff-filter=ACMR -- '*.py' 2>/dev/null)
if [ -n "$STAGED_PY" ]; then
    RUFF=$(resolve_tool ruff)
    if [ -z "$RUFF" ]; then
        NOTES="${NOTES}ruff unavailable, lint skipped. "
    elif ! (cd "$CWD" && echo "$STAGED_PY" | xargs "$RUFF" check) > /dev/null 2>&1; then
        ERRORS="${ERRORS}ruff check failed on staged Python files. "
    fi
fi

PYTEST=$(resolve_tool pytest)
if [ -z "$PYTEST" ]; then
    NOTES="${NOTES}pytest unavailable, tests skipped. "
elif ! (cd "$CWD" && "$PYTEST" --tb=short -q) > /dev/null 2>&1; then
    ERRORS="${ERRORS}pytest failed. "
fi

if [ -n "$ERRORS" ]; then
    echo "Pre-commit quality gate failed: ${ERRORS}Fix issues before committing." >&2
    exit 1
fi

if [ -n "$NOTES" ]; then
    echo "Pre-commit quality gate: ${NOTES}" >&2
fi

exit 0
