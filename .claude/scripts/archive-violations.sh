#!/usr/bin/env bash
# Archive violations.jsonl entries older than 30 days into
# ~/.claude/guardrails/archive/violations-YYYY-MM.jsonl.gz
# Fail-open: exit 0 on any error.
set -u
python3 "$(dirname "$0")/archive_violations.py" "$@" 2>/dev/null || true
exit 0
