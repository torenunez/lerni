#!/usr/bin/env bash
#
# Claude Code Hook: Pre-Commit Quality Gate
# Type: PreToolUse (Bash matcher)
# Purpose: Before any git commit, lint the staged Python files and run the test
#          suite. Block the commit if either fails.
#
# Two deliberate scoping decisions:
#   - ruff lints ONLY the Python files staged for this commit. It is a style
#     gate, and src/ carries pre-existing violations that predate this hook.
#     Judging a commit by debt it did not introduce makes the gate useless.
#   - pytest runs the FULL suite. It is a correctness gate; a change anywhere
#     can break a test anywhere.
#
# Tools are resolved from the project virtualenv first, then PATH. If neither
# has them, the check is skipped with a warning rather than failing closed —
# a missing linter is not evidence of bad code.

set -uo pipefail

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Only care about git commit commands
if ! echo "$COMMAND" | grep -qE '^\s*git\s+commit'; then
    exit 0
fi

CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
ERRORS=""
NOTES=""

# Resolve a tool from the project venv, then PATH. Echoes nothing if unavailable.
resolve_tool() {
    local name="$1"
    if [ -x "$CWD/.venv/bin/$name" ]; then
        echo "$CWD/.venv/bin/$name"
    elif command -v "$name" > /dev/null 2>&1; then
        command -v "$name"
    fi
}

# Check 1: ruff lint, staged Python files only
STAGED_PY=$(cd "$CWD" && git diff --cached --name-only --diff-filter=ACMR -- '*.py' 2>/dev/null)
if [ -n "$STAGED_PY" ]; then
    RUFF=$(resolve_tool ruff)
    if [ -z "$RUFF" ]; then
        NOTES="${NOTES}ruff unavailable, lint skipped. "
    elif ! (cd "$CWD" && echo "$STAGED_PY" | xargs "$RUFF" check) > /dev/null 2>&1; then
        ERRORS="${ERRORS}ruff check failed on staged Python files. "
    fi
fi

# Check 2: pytest, full suite
PYTEST=$(resolve_tool pytest)
if [ -z "$PYTEST" ]; then
    NOTES="${NOTES}pytest unavailable, tests skipped. "
elif ! (cd "$CWD" && "$PYTEST" --tb=short -q) > /dev/null 2>&1; then
    ERRORS="${ERRORS}pytest failed. "
fi

if [ -n "$ERRORS" ]; then
    cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Pre-commit quality gate failed: ${ERRORS}Fix issues before committing."
  }
}
EOF
    exit 2
fi

if [ -n "$NOTES" ]; then
    echo "Pre-commit quality gate: ${NOTES}" >&2
fi

exit 0
