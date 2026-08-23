#!/usr/bin/env bash
#
# Claude Code Hook: Auto-Format on Edit
# Type: PostToolUse (Edit|Write matcher), async
# Purpose: After Claude writes/edits a .py file in src/, run ruff format on it.
#
# What this teaches:
#   - PostToolUse event: fires after a tool has already executed
#   - Async hooks: runs in background, doesn't block Claude
#   - File path extraction: parse tool_input from stdin JSON
#   - Selective formatting: only act on Python files in src/

set -euo pipefail

# Read JSON input from stdin
INPUT=$(cat)

# Extract the file path from tool input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only format Python files in src/
if [ -z "$FILE_PATH" ]; then
    exit 0
fi

if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

if [[ "$FILE_PATH" != *src/* ]]; then
    exit 0
fi

# File exists check
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Run ruff format (async — won't block Claude)
ruff format "$FILE_PATH" 2>/dev/null || true

exit 0
