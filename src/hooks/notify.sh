#!/bin/bash
# Notification handler for Claude Code hooks
# Receives JSON input from stdin and handles notifications

set -euo pipefail

# Read JSON input from stdin
input=$(cat)

# Log the notification (optional - can be customized)
log_file="$HOME/.claude/notifications.log"
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$log_file")"

# Log the notification
echo "[$timestamp] $input" >> "$log_file"

# Parse notification type if present
notification_type=$(echo "$input" | grep -o '"notification_type"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "unknown")

# Handle different notification types
case "$notification_type" in
  "stop")
    # Handle stop notification
    cwd=$(echo "$input" | grep -o '"cwd"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    echo "[$timestamp] Stop notification from: $cwd" >> "$log_file"
    # macOS通知バナー＋音（iTerm・VS Code共通）
    terminal-notifier -title "Claude Code" -message "作業完了しました" -sound Glass &
    ;;
  *)
    # Handle other notifications
    echo "[$timestamp] Generic notification: $notification_type" >> "$log_file"
    ;;
esac

# Output empty JSON for Claude Code hook compliance
echo '{}'

# Exit successfully (don't block Claude)
exit 0
