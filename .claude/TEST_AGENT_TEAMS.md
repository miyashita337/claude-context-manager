# AgentTeams CI Auto-Fix Test

This file is created to test the AgentTeams-based CI monitoring system.

## Test Timestamp
2026-02-16 15:30

## Expected Behavior
1. git push triggers post-tool-use hook
2. Signal file created at ~/.claude/ci-monitoring-request.json
3. ci-monitor agent detects signal
4. CI monitoring starts
5. Agent reports results via SendMessage to team-lead

## Team Configuration
- Team: ci-auto-fix
- Members:
  - team-lead (parent/you)
  - ci-monitor (background agent)
