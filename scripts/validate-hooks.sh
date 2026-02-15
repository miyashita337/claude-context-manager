#!/usr/bin/env bash
# Hook Settings Validation & Consistency Check
# Usage: bash scripts/validate-hooks.sh [--fix]
# Validates project hook settings and checks for inconsistencies with global settings.

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_ok() { echo -e "  ${GREEN}[OK]${NC} $1"; }
print_fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
print_info() { echo -e "  ${BLUE}[INFO]${NC} $1"; }

# Project root detection
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# File paths
PROJECT_HOOKS_FILE="$PROJECT_ROOT/.claude/settings.json"
PROJECT_HOOKS_FILE_OLD="$PROJECT_ROOT/.claude/hooks/hooks.json"  # Legacy non-official path
GLOBAL_SETTINGS_FILE="$HOME/.claude/settings.json"

FIX_MODE=false
ERRORS=0
WARNINGS=0

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix) FIX_MODE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

echo "=== Hook Settings Validation ==="
echo ""

# =========================================
# 1. Project hook file existence check
# =========================================
echo "[1/5] Project hook file..."

if [ ! -f "$PROJECT_HOOKS_FILE" ]; then
    print_fail "Project hook file not found: $PROJECT_HOOKS_FILE"
    ERRORS=$((ERRORS + 1))

    if [ "$FIX_MODE" = true ]; then
        # Check for backup
        BACKUP_DIR="$PROJECT_ROOT/.claude/hooks/backups"
        LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/hooks.json.*.bak 2>/dev/null | head -1)
        if [ -n "$LATEST_BACKUP" ]; then
            print_info "Restoring from backup: $LATEST_BACKUP"
            mkdir -p "$(dirname "$PROJECT_HOOKS_FILE")"
            cp "$LATEST_BACKUP" "$PROJECT_HOOKS_FILE"
            print_ok "Restored from backup"
            ERRORS=$((ERRORS - 1))
        else
            print_fail "No backup found. Manual restoration required."
        fi
    fi
else
    print_ok "Project hook file exists"
fi

# Check for non-official hook path
if [ -f "$PROJECT_HOOKS_FILE_OLD" ]; then
    print_warn "Non-official hook path detected: .claude/hooks/hooks.json"
    print_info "Official paths: .claude/settings.json or .claude/settings.local.json"
    print_info "See: https://code.claude.com/docs/en/hooks#hook-locations"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# =========================================
# 2. JSON validity check
# =========================================
echo "[2/5] JSON validity..."

if [ -f "$PROJECT_HOOKS_FILE" ]; then
    if python3 -c "import json; json.load(open('$PROJECT_HOOKS_FILE'))" 2>/dev/null; then
        print_ok "Project hooks.json is valid JSON"
    else
        print_fail "Project hooks.json is invalid JSON"
        ERRORS=$((ERRORS + 1))
    fi
else
    print_warn "Skipped (file not found)"
fi

if [ -f "$GLOBAL_SETTINGS_FILE" ]; then
    if python3 -c "import json; json.load(open('$GLOBAL_SETTINGS_FILE'))" 2>/dev/null; then
        print_ok "Global settings.json is valid JSON"
    else
        print_fail "Global settings.json is invalid JSON"
        ERRORS=$((ERRORS + 1))
    fi
else
    print_info "Global settings.json not found (optional)"
fi
echo ""

# =========================================
# 3. Required hooks check
# =========================================
echo "[3/5] Required hooks..."

REQUIRED_HOOKS=("UserPromptSubmit" "PostToolUse" "Stop")

if [ -f "$PROJECT_HOOKS_FILE" ]; then
    for hook_name in "${REQUIRED_HOOKS[@]}"; do
        if python3 -c "
import json, sys
data = json.load(open('$PROJECT_HOOKS_FILE'))
hooks = data.get('hooks', {})
if '$hook_name' not in hooks:
    sys.exit(1)
hook_list = hooks['$hook_name']
if not hook_list:
    sys.exit(1)
" 2>/dev/null; then
            print_ok "$hook_name: configured"
        else
            print_fail "$hook_name: missing or empty"
            ERRORS=$((ERRORS + 1))
        fi
    done
else
    for hook_name in "${REQUIRED_HOOKS[@]}"; do
        print_fail "$hook_name: cannot check (file missing)"
        ERRORS=$((ERRORS + 1))
    done
fi
echo ""

# =========================================
# 4. Hook command path validation
# =========================================
echo "[4/5] Hook command paths..."

if [ -f "$PROJECT_HOOKS_FILE" ]; then
    # Extract command paths and validate they exist
    python3 -c "
import json, os, sys

data = json.load(open('$PROJECT_HOOKS_FILE'))
hooks = data.get('hooks', {})
errors = 0

for event_name, event_hooks in hooks.items():
    for hook_group in event_hooks:
        for hook in hook_group.get('hooks', []):
            cmd = hook.get('command', '')
            if not cmd:
                continue
            # Extract the script path from the command
            parts = cmd.split()
            # Find the python/script file path
            script_path = None
            for part in parts:
                if part.endswith('.py') or part.endswith('.sh'):
                    script_path = part
                    break
            if script_path and not script_path.startswith('echo'):
                expanded = os.path.expanduser(script_path)
                if os.path.isfile(expanded):
                    print(f'  \033[0;32m[OK]\033[0m {event_name}: {script_path}')
                else:
                    print(f'  \033[0;31m[FAIL]\033[0m {event_name}: {script_path} (not found)')
                    errors += 1

sys.exit(errors)
" 2>/dev/null
    if [ $? -ne 0 ]; then
        ERRORS=$((ERRORS + $?))
    fi
else
    print_warn "Skipped (file missing)"
fi
echo ""

# =========================================
# 5. Global/project hook overlap check
# =========================================
echo "[5/5] Global/project hook overlap..."

if [ -f "$PROJECT_HOOKS_FILE" ] && [ -f "$GLOBAL_SETTINGS_FILE" ]; then
    python3 -c "
import json, sys

project = json.load(open('$PROJECT_HOOKS_FILE'))
glob = json.load(open('$GLOBAL_SETTINGS_FILE'))

project_hooks = set(project.get('hooks', {}).keys())
global_hooks = set(glob.get('hooks', {}).keys())

overlap = project_hooks & global_hooks

if overlap:
    for hook_name in sorted(overlap):
        print(f'  \033[1;33m[WARN]\033[0m Duplicate hook event: {hook_name}')
        print(f'         Project hooks take precedence over global settings.')
    sys.exit(len(overlap))
else:
    print('  \033[0;32m[OK]\033[0m No overlapping hook events')
    sys.exit(0)
" 2>/dev/null
    OVERLAP_COUNT=$?
    if [ $OVERLAP_COUNT -gt 0 ]; then
        WARNINGS=$((WARNINGS + OVERLAP_COUNT))
    fi
elif [ -f "$PROJECT_HOOKS_FILE" ]; then
    print_ok "No global hooks to compare (global settings has no hooks section or file missing)"
else
    print_warn "Cannot check overlap (project hooks missing)"
fi
echo ""

# =========================================
# Summary
# =========================================
echo "=== Validation Summary ==="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    print_ok "All hook validations passed"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    print_warn "Passed with $WARNINGS warning(s)"
    exit 0
else
    print_fail "$ERRORS error(s), $WARNINGS warning(s)"
    echo ""
    echo "Fixes:"
    echo "  - Restore hooks: make fix-hooks"
    echo "  - Auto-fix: bash scripts/validate-hooks.sh --fix"
    exit 1
fi
