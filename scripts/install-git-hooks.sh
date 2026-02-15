#!/usr/bin/env bash
# Git Hooks インストールスクリプト
# Usage: bash scripts/install-git-hooks.sh

set -e

# Color codes
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

print_ok() { printf "${GREEN}✅${NC} %s\n" "$1"; }
print_warn() { printf "${YELLOW}⚠️${NC}  %s\n" "$1"; }

echo "🔧 Installing Git hooks..."
echo ""

# Git リポジトリチェック
if [ ! -d .git ]; then
    echo "❌ Error: Not a Git repository"
    exit 1
fi

# hooksディレクトリ作成
mkdir -p .git/hooks

# pre-commitフックをインストール
HOOK_SOURCE="scripts/git-hooks/pre-commit"
HOOK_TARGET=".git/hooks/pre-commit"

if [ -f "$HOOK_SOURCE" ]; then
    if [ -f "$HOOK_TARGET" ]; then
        # 既存のフックをバックアップ
        cp "$HOOK_TARGET" "$HOOK_TARGET.backup"
        print_warn "Existing hook backed up to $HOOK_TARGET.backup"
    fi

    cp "$HOOK_SOURCE" "$HOOK_TARGET"
    chmod +x "$HOOK_TARGET"
    print_ok "Pre-commit hook installed"
else
    echo "❌ Error: Hook source not found: $HOOK_SOURCE"
    exit 1
fi

echo ""
print_ok "Git hooks installation complete!"
echo ""
echo "The pre-commit hook will automatically run before each commit."
echo ""
echo "To test the hook:"
echo "  1. Stage a file: git add <file>"
echo "  2. Try to commit: git commit -m 'test'"
echo "  3. Hook will automatically check for secrets and unwanted files"
echo ""
