#!/bin/bash
# Topic Server インストーラー (Issue #28)
# sentence-transformers をインストールし、launchd で自動起動を設定する

set -euo pipefail

LABEL="com.claude.topic-server"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_PATH="$SCRIPT_DIR/server.py"
LOG_DIR="$HOME/.claude"
PYTHON="$(python3 -c 'import sys; print(sys.executable)')"

echo "🔧 Topic Server インストール開始..."
echo "   Python:  $PYTHON"
echo "   Server:  $SERVER_PATH"
echo "   Plist:   $PLIST_PATH"
echo ""

# --- 1. sentence-transformers インストール ---
echo "📦 sentence-transformers をインストール中..."
"$PYTHON" -m pip install --quiet sentence-transformers
echo "   ✅ インストール完了"

# --- 2. ログディレクトリ作成 ---
mkdir -p "$LOG_DIR"

# --- 3. plist 生成 ---
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${SERVER_PATH}</string>
    </array>

    <!-- ログイン時に自動起動 -->
    <key>RunAtLoad</key>
    <true/>

    <!-- クラッシュ時に launchd が自動再起動 -->
    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/topic-server.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/topic-server-error.log</string>

    <!-- 起動失敗時のスロットリング (10秒待ってから再試行) -->
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
EOF
echo "   ✅ plist 生成: $PLIST_PATH"

# --- 4. 既存サービスを停止してから再ロード ---
if launchctl list "$LABEL" &>/dev/null; then
    echo "   既存サービスを停止中..."
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

launchctl load "$PLIST_PATH"
echo "   ✅ launchd 登録完了"

# --- 5. 起動確認 (モデルロードに時間がかかるため少し待つ) ---
echo ""
echo "⏳ サーバー起動待機中 (モデルロード ~10秒)..."
for i in $(seq 1 20); do
    sleep 1
    if curl -sf http://127.0.0.1:8765/health > /dev/null 2>&1; then
        echo "   ✅ サーバー起動確認 (${i}秒)"
        curl -s http://127.0.0.1:8765/health | python3 -m json.tool
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "   ⚠️  起動タイムアウト。ログを確認: $LOG_DIR/topic-server-error.log"
    fi
done

echo ""
echo "✅ インストール完了！"
echo ""
echo "管理コマンド:"
echo "  make status-topic-server  - 動作確認"
echo "  make stop-topic-server    - 停止"
echo "  make start-topic-server   - 手動起動"
echo "  make uninstall-topic-server - アンインストール"
