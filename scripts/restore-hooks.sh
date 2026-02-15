#!/usr/bin/env bash
# Hook Settings Restore Script
# Usage: bash scripts/restore-hooks.sh [backup_file]
# Without arguments, restores from the most recent backup.
# With a filename argument, restores from the specified backup.

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_ok() { echo -e "  ${GREEN}[OK]${NC} $1"; }
print_fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }
print_info() { echo -e "  ${YELLOW}[INFO]${NC} $1"; }

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_FILE="$PROJECT_ROOT/.claude/hooks/hooks.json"
BACKUP_DIR="$PROJECT_ROOT/.claude/hooks/backups"

echo "=== Hook Settings Restore ==="
echo ""

# Check backup directory
if [ ! -d "$BACKUP_DIR" ]; then
    print_fail "No backup directory found: $BACKUP_DIR"
    echo "  Run 'make backup-hooks' first to create backups."
    exit 1
fi

# Determine which backup to restore
if [ -n "$1" ]; then
    # Specific backup file
    if [ -f "$1" ]; then
        RESTORE_FILE="$1"
    elif [ -f "$BACKUP_DIR/$1" ]; then
        RESTORE_FILE="$BACKUP_DIR/$1"
    else
        print_fail "Backup file not found: $1"
        exit 1
    fi
else
    # Most recent backup
    RESTORE_FILE=$(ls -1t "$BACKUP_DIR"/hooks.json.*.bak 2>/dev/null | head -1)
    if [ -z "$RESTORE_FILE" ]; then
        print_fail "No backup files found in $BACKUP_DIR"
        exit 1
    fi
fi

print_info "Restore source: $(basename "$RESTORE_FILE")"

# Verify backup JSON validity
if ! python3 -c "import json; json.load(open('$RESTORE_FILE'))" 2>/dev/null; then
    print_fail "Backup file contains invalid JSON. Aborting restore."
    exit 1
fi
print_ok "Backup JSON is valid"

# Verify checksum if available
CHECKSUM_FILE="${RESTORE_FILE}.sha256"
if [ -f "$CHECKSUM_FILE" ]; then
    EXPECTED=$(cat "$CHECKSUM_FILE")
    ACTUAL=$(shasum -a 256 "$RESTORE_FILE" 2>/dev/null | cut -d' ' -f1)
    if [ "$EXPECTED" = "$ACTUAL" ]; then
        print_ok "Checksum verified"
    else
        print_fail "Checksum mismatch! Backup may be corrupted."
        echo "  Expected: $EXPECTED"
        echo "  Actual:   $ACTUAL"
        exit 1
    fi
fi

# Show what will be restored
echo ""
echo "Required hooks in backup:"
python3 -c "
import json
data = json.load(open('$RESTORE_FILE'))
hooks = data.get('hooks', {})
for name in sorted(hooks.keys()):
    count = len(hooks[name])
    print(f'  - {name}: {count} handler(s)')
"

# Ensure target directory exists
mkdir -p "$(dirname "$HOOKS_FILE")"

# Restore
cp "$RESTORE_FILE" "$HOOKS_FILE"
print_ok "Restored to $HOOKS_FILE"

# Validate restored file
echo ""
echo "Post-restore validation:"
if bash "$SCRIPT_DIR/validate-hooks.sh" > /dev/null 2>&1; then
    print_ok "Validation passed"
else
    print_fail "Validation failed after restore. Check with: make validate-hooks"
fi

echo ""
echo "=== Restore Complete ==="
