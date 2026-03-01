#!/bin/bash
# Session Title インストーラー (Issue #109)
# セッションタイトル管理スクリプトを ~/.claude/ にデプロイする

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEST_SCRIPTS="$HOME/.claude/scripts"
DEST_SKILL="$HOME/.claude/skills/title"
DEST_TITLES="$HOME/.claude/session-titles"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "🏷️  Session Title インストール開始..."
echo "   Source:  $SCRIPT_DIR"
echo "   Dest:    $DEST_SCRIPTS"
echo ""

# --- 1. スクリプトコピー ---
echo "📦 スクリプトをコピー中..."
mkdir -p "$DEST_SCRIPTS"
cp "$SCRIPT_DIR/session_title_utils.py" "$DEST_SCRIPTS/"
cp "$SCRIPT_DIR/session-start-title.py" "$DEST_SCRIPTS/"
cp "$SCRIPT_DIR/prompt-title-check.py" "$DEST_SCRIPTS/"
cp "$SCRIPT_DIR/statusline.py" "$DEST_SCRIPTS/"
echo "   ✅ 4ファイルをコピー完了"

# --- 2. SKILL.md コピー ---
echo "📋 SKILL.md をコピー中..."
mkdir -p "$DEST_SKILL"
REPO_SKILL_DIR="$SCRIPT_DIR/../../.claude/skills/title"
if [ -f "$REPO_SKILL_DIR/SKILL.md" ]; then
    cp "$REPO_SKILL_DIR/SKILL.md" "$DEST_SKILL/"
    echo "   ✅ SKILL.md コピー完了"
else
    echo "   ⚠️  SKILL.md が見つかりません: $REPO_SKILL_DIR"
fi

# --- 3. タイトル保存ディレクトリ作成 ---
mkdir -p "$DEST_TITLES"
echo "   ✅ session-titles ディレクトリ作成完了"

# --- 4. settings.json にフック設定をマージ ---
echo "🔧 settings.json にフック設定をマージ中..."
python3 - "$SETTINGS_FILE" "$DEST_SCRIPTS" << 'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
scripts_dir = sys.argv[2]

# Load existing settings
if settings_path.exists():
    settings = json.loads(settings_path.read_text())
else:
    settings = {}

hooks = settings.setdefault("hooks", {})

# Helper: add hook entry if not already present
def ensure_hook(event_name, hook_entry):
    event_hooks = hooks.setdefault(event_name, [])
    # Check if already registered (by command match)
    for existing in event_hooks:
        if existing.get("command") == hook_entry["command"]:
            return  # Already present
    event_hooks.append(hook_entry)

# SessionStart hook
ensure_hook("SessionStart", {
    "type": "command",
    "command": f"python3 {scripts_dir}/session-start-title.py"
})

# UserPromptSubmit hook
ensure_hook("UserPromptSubmit", {
    "type": "command",
    "command": f"python3 {scripts_dir}/prompt-title-check.py"
})

# StatusLine hook
ensure_hook("StatusLine", {
    "type": "command",
    "command": f"python3 {scripts_dir}/statusline.py"
})

# Write back
settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
PYEOF

echo "   ✅ フック設定マージ完了"

echo ""
echo "✅ インストール完了！"
echo ""
echo "管理コマンド:"
echo "  make install-session-title    - 再インストール"
echo "  make uninstall-session-title  - アンインストール"
