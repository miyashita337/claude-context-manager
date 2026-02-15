#!/usr/bin/env bash
# Claude Context Manager - セッション起動時チェックスクリプト
# Usage: bash scripts/startup-check.sh
# Environment variables:
#   SKIP_TESTS=1 - テストスイート実行をスキップ（CI用）

set -e

# カラーコード
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 成功/失敗/警告表示
print_ok() {
    echo -e "  ${GREEN}✅${NC} $1"
}

print_fail() {
    echo -e "  ${RED}❌${NC} $1"
}

print_warn() {
    echo -e "  ${YELLOW}⚠️${NC}  $1"
}

echo "=== セッション起動時チェック ==="
echo ""

# 1. Hook動作確認
echo "1. Hook動作確認..."
if echo '{"session_id": "startup-check-001", "prompt": "起動確認テスト"}' | python3 src/hooks/user-prompt-submit.py > /dev/null 2>&1; then
    print_ok "UserPromptSubmit: OK"
else
    print_fail "UserPromptSubmit: FAILED"
fi

if echo '' | python3 src/hooks/user-prompt-submit.py > /dev/null 2>&1; then
    print_ok "空stdin処理: OK"
else
    print_fail "空stdin処理: FAILED"
fi
echo ""

# 2. ログファイル作成確認
echo "2. ログファイル作成確認..."
if [ -f ~/.claude/context-history/.tmp/session-startup-check-001.json ]; then
    print_ok "OK"
else
    print_warn "未作成"
fi
echo ""

# 3. エラーログ確認
echo "3. エラーログ確認..."
if [ -f ~/.claude/hook-debug.log ]; then
    if tail -n 10 ~/.claude/hook-debug.log 2>/dev/null | grep -qi "error"; then
        print_warn "最近のエラーあり"
    else
        print_ok "クリーン"
    fi
else
    print_ok "クリーン（ログファイル未作成）"
fi
echo ""

# 4. Hook設定検証（整合性チェック含む）
echo "4. Hook設定検証..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if bash "$SCRIPT_DIR/validate-hooks.sh" > /dev/null 2>&1; then
    print_ok "Hook設定検証: 全チェック通過"
else
    print_fail "Hook設定検証: 問題あり（詳細は make validate-hooks で確認）"
fi
echo ""

# 5. テストスイート実行（オプション）
if [ "${SKIP_TESTS}" != "1" ]; then
    echo "5. テストスイート実行..."
    python3 -m pytest tests/test_hooks.py::test_stdin_empty_handling tests/test_hooks.py::test_stdin_whitespace_only_handling -v --tb=no -q
    echo ""
else
    echo "5. テストスイート実行..."
    print_warn "スキップ（SKIP_TESTS=1）"
    echo ""
fi

echo "=== チェック完了 ==="
