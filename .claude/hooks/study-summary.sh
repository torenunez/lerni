#!/usr/bin/env bash
#
# Claude Code Hook: Session Start Study Summary
# Type: SessionStart (no matcher — fires on every session start)
# Purpose: Show how many questions are due today when starting a Claude Code session.
#
# What this teaches:
#   - SessionStart event: fires when a new session begins or resumes
#   - Context injection: stdout from SessionStart hooks is added to Claude's context
#   - Direct DB queries: hook can query the Lerni SQLite DB directly
#   - Providing helpful context without making decisions

set -euo pipefail

LERNI_DB="$HOME/.lerni/lerni.db"

# If no database exists, this is a fresh install — nothing to report
if [ ! -f "$LERNI_DB" ]; then
    echo "Lerni: No database found. Run 'study new' to create your first question."
    exit 0
fi

# Query for questions due today (next_review_at <= now)
NOW=$(date -u +"%Y-%m-%d %H:%M:%S")

DUE_COUNT=$(sqlite3 "$LERNI_DB" \
    "SELECT COUNT(*) FROM questions WHERE next_review_at <= '$NOW';" 2>/dev/null || echo "0")

TOTAL_COUNT=$(sqlite3 "$LERNI_DB" \
    "SELECT COUNT(*) FROM questions;" 2>/dev/null || echo "0")

# Build summary message
if [ "$DUE_COUNT" -gt 0 ] 2>/dev/null; then
    echo "Lerni: $DUE_COUNT question(s) due for review today ($TOTAL_COUNT total). Run 'study review' to start."
elif [ "$TOTAL_COUNT" -gt 0 ] 2>/dev/null; then
    echo "Lerni: All caught up! No reviews due today ($TOTAL_COUNT questions total)."
else
    echo "Lerni: No questions yet. Run 'study new' to create your first question."
fi

exit 0
