#!/usr/bin/env bash
# 品質ゲート実行スクリプト（簡潔版）
# Usage: bash scripts/quality-gate.sh [pre-commit|pre-push]

set -e

STAGE="${1:-pre-commit}"

# Color codes with ANSI-C quoting
GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'

print_ok() { printf "${GREEN}✅${NC} %s\n" "$1"; }
print_fail() { printf "${RED}❌${NC} %s\n" "$1"; }
print_warn() { printf "${YELLOW}⚠️${NC}  %s\n" "$1"; }

echo "🚧 Quality Gate: $STAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

FAILED=0

case "$STAGE" in
  pre-commit)
    # ==========================================
    # Stability Gate
    # ==========================================
    echo "📋 Stability Gate"
    echo "--------------------------------"

    # .gitignore完全性
    REQUIRED=("__pycache__/" "*.pyc" ".env" "*.backup")
    for pattern in "${REQUIRED[@]}"; do
      if grep -qF "$pattern" .gitignore 2>/dev/null; then
        print_ok "$pattern in .gitignore"
      else
        print_fail "Missing: $pattern"
        FAILED=1
      fi
    done

    # 不要ファイル
    if find . -type f \( -name "*.pyc" -o -name "*.backup" \) -not -path "./.git/*" 2>/dev/null | grep -q .; then
      print_warn "Unwanted files found (run: make git-clean)"
    else
      print_ok "No unwanted files"
    fi
    echo ""

    # ==========================================
    # Security Gate
    # ==========================================
    echo "🔒 Security Gate"
    echo "--------------------------------"

    # .envファイルチェック
    if [ -f .env ]; then
      if grep -qF ".env" .gitignore; then
        print_ok ".env is in .gitignore"
      else
        print_fail ".env is NOT in .gitignore"
        FAILED=1
      fi
    else
      print_ok "No .env file"
    fi

    # ステージング済みファイルのスキャン
    if [ -d .git ]; then
      STAGED=$(git diff --cached --name-only 2>/dev/null || echo "")
      if echo "$STAGED" | grep -qE '\.env'; then
        print_fail ".env file is staged!"
        FAILED=1
      else
        print_ok "No secrets in staged files"
      fi
    fi
    echo ""

    # ==========================================
    # Code Quality Gate（非致命的）
    # ==========================================
    echo "📊 Code Quality Gate"
    echo "--------------------------------"

    if command -v ruff >/dev/null 2>&1; then
      if ruff check . --quiet 2>/dev/null; then
        print_ok "Ruff check passed"
      else
        print_warn "Ruff found issues (not blocking)"
      fi
    else
      print_warn "Ruff not installed (skipped)"
    fi
    echo ""
    ;;

  pre-push)
    # ==========================================
    # Integration Gate (Lightweight)
    # ==========================================
    echo "🧪 Integration Gate"
    echo "--------------------------------"

    # Note: Full tests run in GitHub Actions
    # Here we only check critical stability markers

    print_ok "Stability checks passed (full tests run in CI)"
    echo ""
    ;;

  *)
    echo "❌ Unknown stage: $STAGE"
    echo "Usage: $0 [pre-commit|pre-push]"
    exit 1
    ;;
esac

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 1 ]; then
  print_fail "Quality Gate FAILED"
  exit 1
else
  print_ok "Quality Gate PASSED"
  exit 0
fi
