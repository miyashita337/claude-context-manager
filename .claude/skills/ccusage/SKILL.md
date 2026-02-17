---
name: ccusage
description: Analyze Claude Code session token usage and costs using ccusage CLI. Detects compact events, identifies heavy sessions, and provides optimization recommendations.
tools: Bash, Read, Grep
model: sonnet
---

# ccusage Skill

**Purpose**: Analyze Claude Code session token usage, costs, and compact events using the `ccusage` CLI tool. Identifies high-cost sessions, measures context window usage, and provides actionable optimization recommendations.

**When to Use**:
- To understand how many tokens and how much money has been spent
- When sessions seem slow or expensive and you want to investigate why
- To detect when and why compact events occurred
- To identify Kitchen-Sink or Lost-in-the-Middle problems
- To prepare evidence for recommending alternative solutions for heavy tasks

**Data Source**: `~/.claude/projects/[project-path]/[session-id].jsonl`

---

## Workflow

### Step 1: Parse User Request

Determine what kind of analysis is needed:

| Request | Command |
|---------|---------|
| Today's usage | `ccusage daily --since $(date +%Y%m%d)` |
| Daily breakdown | `ccusage daily --since YYYYMMDD` |
| Session details | `ccusage session` |
| Monthly summary | `ccusage monthly` |
| High-cost sessions | `ccusage session --json \| jq '...'` |
| Project-specific | `ccusage daily --project PROJECT_NAME` |

**Examples**:
```
/ccusage                       → today's summary
/ccusage daily --since 20260201  → February breakdown
/ccusage session               → per-session analysis
/ccusage monthly               → monthly cost summary
```

---

### Step 2: Pre-Flight Check

Before running, verify ccusage is installed globally:

```bash
if ! command -v ccusage &>/dev/null; then
  echo "❌ ccusage is not installed"
  echo "Install: npm install -g ccusage"
  exit 1
fi

# Show version
ccusage --version
```

Also check that session data exists:

```bash
SESSION_DIR="$HOME/.claude/projects"
if [[ ! -d "$SESSION_DIR" ]]; then
  echo "❌ No Claude Code sessions found at $SESSION_DIR"
  exit 1
fi

SESSION_COUNT=$(find "$SESSION_DIR" -name "*.jsonl" | wc -l | tr -d ' ')
echo "✅ Found $SESSION_COUNT session files"
```

---

### Step 3: Run ccusage Analysis

#### Basic Analysis

```bash
# Today's usage
ccusage daily --since "$(date +%Y%m%d)"

# Date range
ccusage daily --since 20260201 --until 20260217

# Session details
ccusage session

# Monthly summary with model breakdown
ccusage monthly --breakdown
```

#### JSON Analysis (for filtering)

```bash
# All sessions as JSON
ccusage session --json | jq '.'

# High-cost sessions (over $5)
ccusage session --json | jq '.entries[] | select(.cost > 5) | {session, cost, totalTokens}'

# Highest token usage
ccusage session --json | jq '.entries | sort_by(-.totalTokens) | .[:5]'

# Today's total cost
ccusage daily --since "$(date +%Y%m%d)" --json | jq '.summary.totalCost'
```

#### Project-Specific Analysis

```bash
# Filter by current project
PROJECT=$(basename "$(pwd)")
ccusage daily --project "$PROJECT"

# Project session details
ccusage session --project "$PROJECT" --json
```

---

### Step 4: Detect Issues

Analyze the results to detect problems:

```bash
# Heavy session threshold (tokens)
KITCHEN_SINK_THRESHOLD=167000   # tokens per session
HIGH_COST_THRESHOLD=5           # USD per session
HIGH_DAILY_TOKEN_THRESHOLD=70000  # tokens per day

# Check for high-cost sessions
HIGH_COST=$(ccusage session --json | jq --argjson threshold "$HIGH_COST_THRESHOLD" \
  '[.entries[] | select(.cost > $threshold)] | length')

if [[ "$HIGH_COST" -gt 0 ]]; then
  echo "⚠️  Found $HIGH_COST high-cost sessions (over \$$HIGH_COST_THRESHOLD)"
fi

# Check for Kitchen-Sink sessions
HEAVY_SESSIONS=$(ccusage session --json | jq --argjson threshold "$KITCHEN_SINK_THRESHOLD" \
  '[.entries[] | select(.totalTokens > $threshold)] | length')

if [[ "$HEAVY_SESSIONS" -gt 0 ]]; then
  echo "⚠️  Found $HEAVY_SESSIONS Kitchen-Sink sessions (over ${KITCHEN_SINK_THRESHOLD} tokens)"
fi
```

---

### Step 5: SpecStory Integration (Optional)

If SpecStory history exists, cross-reference compact events:

```bash
SPECSTORY_DIR=".specstory/history"

if [[ -d "$SPECSTORY_DIR" ]]; then
  echo "📚 SpecStory history found"

  # Count compact events
  COMPACT_COUNT=$(grep -rl "compact_detected: true" "$SPECSTORY_DIR" 2>/dev/null | wc -l | tr -d ' ')
  echo "   Compact events: $COMPACT_COUNT sessions"

  # Show sessions with compacts
  if [[ "$COMPACT_COUNT" -gt 0 ]]; then
    echo "   Sessions with compact:"
    grep -rl "compact_detected: true" "$SPECSTORY_DIR" | while read -r f; do
      TOKENS=$(grep -o 'total_tokens: [0-9]*' "$f" | tail -1 | awk '{print $2}')
      echo "   - $(basename "$f") (${TOKENS} tokens at compact)"
    done
  fi
else
  echo "ℹ️  SpecStory not synced. Run: specstory sync"
fi
```

---

### Step 6: Generate Report

Produce a structured report:

```
## ccusage Analysis Report

### Summary
- Period    : YYYY-MM-DD ~ YYYY-MM-DD
- Total Cost: $XX.XX
- Total Tokens: XX,XXX,XXX
  - Input         : XX,XXX
  - Output        : XX,XXX
  - Cache Create  : XX,XXX,XXX
  - Cache Read    : XX,XXX,XXX

### Alerts
⚠️  [N] high-cost sessions detected (>$5)
⚠️  [N] Kitchen-Sink sessions detected (>167K tokens)
✅  No compact events detected  (or)
⚠️  [N] compact events detected

### Top Sessions by Cost
1. [session-id]  $XX.XX  XXX tokens  last: YYYY-MM-DD
2. ...

### Optimization Recommendations
- [recommendation based on findings]
```

---

## Error Handling

### ccusage Not Installed

```
❌ Error: ccusage not found
   Fix: npm install -g ccusage
         (or) npx ccusage@latest daily
```

Check PITFALLS.md entry: `CCUSAGE-001`

---

### No Session Data

```
❌ Error: No session files found at ~/.claude/projects/
   Cause: Claude Code has not been used yet, or sessions are stored elsewhere
   Fix:
   1. Confirm Claude Code is installed: claude --version
   2. Check actual path: ls ~/.claude/projects/
```

---

### JSON Parse Error

```
❌ Error: jq parse failed
   Cause: ccusage output is not valid JSON, or jq is not installed
   Fix:
   1. Install jq: brew install jq
   2. Test without filter: ccusage session --json
```

---

### Date Format Error

```
❌ Error: Invalid date format
   Cause: Date must be YYYYMMDD format
   Fix: ccusage daily --since 20260201   ✅
        ccusage daily --since 2026-02-01  ❌
```

---

## Examples

### Example 1: Quick Daily Check

```bash
# Run
/ccusage

# Expected output
## ccusage Analysis - Today (2026-02-17)

Total Cost  : $12.50
Total Tokens: 25,430,120
  Cache Read: 24,800,000 (97.5%)

Sessions    : 3 active
Alerts      : None ✅
```

---

### Example 2: Investigate Expensive Month

```bash
# Run
/ccusage monthly --breakdown

# Expected output
## Monthly Summary - February 2026

Total Cost: $107.09
Models:
  - claude-opus-4-6   : $45.00 (42%)
  - claude-sonnet-4-5 : $55.00 (51%)
  - claude-haiku-4-5  : $7.09  (7%)

Recommendation:
  ⚠️  Consider using haiku for simple tasks to reduce cost
```

---

### Example 3: Find Heavy Sessions

```bash
# Run
/ccusage session

# Expected output
## Session Analysis

⚠️  2 high-cost sessions found:

1. context-manager [2026-02-16]
   Cost  : $60.74
   Tokens: 139,814,000
   Issue : Kitchen-Sink (>167K tokens)
   Action: Consider splitting into smaller sessions

2. subagent-analysis [2026-02-15]
   Cost  : $9.29
   Tokens: 48,200,000
   Issue : None
   Action: Normal usage
```

---

### Example 4: Compact Detection via SpecStory

```bash
# Run
/ccusage session  (with SpecStory synced)

# Expected output
## Compact Event Report

SpecStory history: ✅ Found

Sessions with compact:
- 2026-02-16_context-manager.md
  Tokens at compact: 167,340
  Estimated reduction: ~50%

Recommendation:
  Keep sessions under 130K tokens to avoid compact
  Run /compact-analyzer for detailed diff analysis
```

---

## Best Practices

1. **Run daily** to track cost accumulation before it grows too large
2. **Use `--json` with jq** for custom analysis and filtering
3. **Sync SpecStory first** for richer compact detection: `specstory sync`
4. **Set alerts** when daily cost exceeds $10 (project default threshold)
5. **Filter by project** when working across multiple projects

---

## Anti-Patterns

- ❌ Running without checking if ccusage is installed first
- ❌ Using `@ccusage/codex` — that is for Codex CLI, not Claude Code
- ❌ Using date format `2026-02-01` — must be `20260201`
- ❌ Ignoring high-cost sessions without investigating the cause
- ❌ Skipping SpecStory sync before compact analysis

---

## Related Skills

- `/compact-analyzer` — Deep compact event diff analysis
- `/codex` — AI-driven codebase analysis (optional, costs money)
- `/fact-check` — Verify tool behavior against official docs
