#!/bin/bash
# check-duplicate-issue.sh
# Usage: check-duplicate-issue.sh "keyword1 keyword2"
# Searches open issues for potential duplicates before creating a new issue.
# Exit code 0 = no duplicates found (safe to create)
# Exit code 1 = duplicates found (do NOT create)

set -euo pipefail

REPO="${REPO:-miyashita337/claude-context-manager}"
QUERY="${1:-}"

if [[ -z "$QUERY" ]]; then
    echo "Usage: $0 \"keyword1 keyword2\"" >&2
    exit 2
fi

echo "Searching for potential duplicate issues: \"$QUERY\""
echo "Repository: $REPO"
echo ""

RESULTS=$(gh issue list \
    --state open \
    --search "$QUERY" \
    --repo "$REPO" \
    --limit 10 \
    --json number,title,url \
    --jq '.[] | "#\(.number) \(.title)\n  \(.url)"')

if [[ -z "$RESULTS" ]]; then
    echo "No duplicates found. Safe to create a new issue."
    exit 0
else
    echo "Potential duplicate issues found:"
    echo ""
    echo "$RESULTS"
    echo ""
    echo "If any of the above match your intent, do NOT create a new issue."
    echo "Add a comment to the existing issue instead."
    exit 1
fi
