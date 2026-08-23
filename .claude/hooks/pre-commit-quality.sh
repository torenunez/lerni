#!/usr/bin/env bash
#
# Claude Code Hook: Pre-Commit Quality Gate
# Type: PreToolUse (Bash matcher)
# Purpose: Before any git commit, run the shared quality gate.
#
# Core logic lives in quality-gate.sh so .githooks/pre-commit can reuse it.
# Requires jq to parse the PreToolUse payload; missing jq denies the commit.

set -uo pipefail

INPUT=$(cat)

if ! command -v jq > /dev/null 2>&1; then
    cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Pre-commit quality gate requires jq. Install jq, then retry the commit."
  }
}
EOF
    exit 2
fi

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if ! echo "$COMMAND" | grep -qE '^\s*git\s+commit'; then
    exit 0
fi

CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! "$SCRIPT_DIR/quality-gate.sh" "$CWD"; then
    cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Pre-commit quality gate failed. Fix issues before committing."
  }
}
EOF
    exit 2
fi

exit 0
