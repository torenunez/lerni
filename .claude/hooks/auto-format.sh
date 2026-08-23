#!/usr/bin/env bash
#
# Claude Code Hook: Auto-Format on Edit
# Type: PostToolUse (Edit|Write matcher), async
# Purpose: After Claude writes/edits a .py file in src/, run ruff format on it.

set -euo pipefail

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

if [[ "$FILE_PATH" != *src/* ]]; then
    exit 0
fi

if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

RUFF=""
if [ -x "$CWD/.venv/bin/ruff" ]; then
    RUFF="$CWD/.venv/bin/ruff"
elif command -v ruff > /dev/null 2>&1; then
    RUFF="$(command -v ruff)"
fi

if [ -z "$RUFF" ]; then
    exit 0
fi

"$RUFF" format "$FILE_PATH" 2>/dev/null || true

exit 0
