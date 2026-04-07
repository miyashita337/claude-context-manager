#!/usr/bin/env bash
# SessionStart hook: print last-7-days guardrail summary (only if >0 violations).
# Also triggers archive of >30day entries. Fail-open: always exit 0.
set -u
DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"
STATE_DIR="${HOME}/.claude/guardrails"
STAMP="${STATE_DIR}/.last_archive_date"
TODAY="$(date +%Y-%m-%d)"
mkdir -p "$STATE_DIR" 2>/dev/null || true
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP" 2>/dev/null)" != "$TODAY" ]; then
  if python3 "$DIR/archive_violations.py" >/dev/null 2>&1; then
    echo "$TODAY" > "$STAMP" 2>/dev/null || true
  fi
fi
python3 "$DIR/guardrails_report.py" summary --days 7 2>/dev/null || true
exit 0
