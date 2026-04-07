#!/usr/bin/env bash
# SessionStart hook: print last-7-days guardrail summary (only if >0 violations).
# Also triggers archive of >30day entries. Fail-open: always exit 0.
set -u
DIR="$(cd "$(dirname "$0")/../scripts" && pwd)"
python3 "$DIR/archive_violations.py" >/dev/null 2>&1 || true
python3 "$DIR/guardrails_report.py" summary --days 7 2>/dev/null || true
exit 0
