#!/usr/bin/env bash
# Hook Settings Backup Script
# Usage: bash scripts/backup-hooks.sh
# Creates a timestamped backup of hooks.json.
# Maintains up to 10 backup generations (oldest are pruned).

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
MAX_BACKUPS=10

echo "=== Hook Settings Backup ==="
echo ""

# Check source file exists
if [ ! -f "$HOOKS_FILE" ]; then
    print_fail "hooks.json not found: $HOOKS_FILE"
    echo "  Nothing to back up."
    exit 1
fi

# Validate JSON before backing up
if ! python3 -c "import json; json.load(open('$HOOKS_FILE'))" 2>/dev/null; then
    print_fail "hooks.json contains invalid JSON. Refusing to back up corrupted file."
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create timestamped backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/hooks.json.${TIMESTAMP}.bak"

cp "$HOOKS_FILE" "$BACKUP_FILE"
print_ok "Backup created: hooks.json.${TIMESTAMP}.bak"

# Compute checksum for integrity verification
if command -v shasum > /dev/null 2>&1; then
    CHECKSUM=$(shasum -a 256 "$BACKUP_FILE" | cut -d' ' -f1)
    echo "$CHECKSUM" > "${BACKUP_FILE}.sha256"
    print_ok "Checksum saved"
fi

# Prune old backups (keep only MAX_BACKUPS most recent)
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/hooks.json.*.bak 2>/dev/null | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt "$MAX_BACKUPS" ]; then
    PRUNE_COUNT=$((BACKUP_COUNT - MAX_BACKUPS))
    ls -1t "$BACKUP_DIR"/hooks.json.*.bak | tail -n "$PRUNE_COUNT" | while read -r old_backup; do
        rm -f "$old_backup" "${old_backup}.sha256"
    done
    print_info "Pruned $PRUNE_COUNT old backup(s). Keeping $MAX_BACKUPS most recent."
fi

# Show current backup count
CURRENT_COUNT=$(ls -1 "$BACKUP_DIR"/hooks.json.*.bak 2>/dev/null | wc -l | tr -d ' ')
print_info "Total backups: $CURRENT_COUNT/$MAX_BACKUPS"

echo ""
echo "=== Backup Complete ==="
