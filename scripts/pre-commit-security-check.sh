#!/bin/bash

###############################################################################
# Pre-Commit Security Check Script
# Purpose: Git操作前に機密情報とセキュリティリスクを検出する
# Usage: ./scripts/pre-commit-security-check.sh [--strict]
###############################################################################

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 変数
STRICT_MODE=false
ERRORS_FOUND=0
WARNINGS_FOUND=0

# オプション解析
while [[ $# -gt 0 ]]; do
  case $1 in
    --strict)
      STRICT_MODE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=================================="
echo "Pre-Commit Security Check"
echo "=================================="

###############################################################################
# Phase 1: 機密情報スキャン
###############################################################################
echo ""
echo "[Phase 1] Scanning for sensitive information..."

# 機密情報パターン
SECRETS_PATTERNS=(
  # APIキー
  "sk-proj-[A-Za-z0-9]{40,}"                    # OpenAI API Key
  "AIzaSy[A-Za-z0-9_-]{33}"                     # Google API Key
  "AKIA[0-9A-Z]{16}"                            # AWS Access Key ID
  # トークン
  "ghp_[a-zA-Z0-9]{36}"                         # GitHub Personal Access Token
  "gho_[a-zA-Z0-9]{36}"                         # GitHub OAuth Token
  "ghs_[a-zA-Z0-9]{36}"                         # GitHub Server Token
  # 汎用パターン
  "(password|passwd|pwd)[\"']?\s*[:=]\s*[\"'][^\"']{8,}[\"']"
  "(api_key|apikey|api-key)[\"']?\s*[:=]\s*[\"'][^\"']{16,}[\"']"
  "(secret|token)[\"']?\s*[:=]\s*[\"'][^\"']{16,}[\"']"
  # プライベートキー
  "-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----"
)

# 除外パターン
EXCLUDE_PATTERNS=(
  ".git"
  "node_modules"
  "__pycache__"
  "dist"
  "build"
  ".venv"
  "venv"
  ".cache"
  "coverage"
  "htmlcov"
)

# 除外オプション生成
EXCLUDE_OPTS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
  EXCLUDE_OPTS="$EXCLUDE_OPTS --exclude-dir=$pattern"
done

# パターンごとにスキャン
for pattern in "${SECRETS_PATTERNS[@]}"; do
  matches=$(grep -r -E $EXCLUDE_OPTS -i "$pattern" . 2>/dev/null | \
            grep -v "node_modules/" | \
            grep -v ".git/" | \
            grep -v "dist/" | \
            grep -v "build/" || true)
  if [ ! -z "$matches" ]; then
    echo -e "${RED}[ERROR]${NC} Potential secret detected:"
    echo "$matches" | head -5
    echo ""
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
  fi
done

# 機密ファイルの検出
SENSITIVE_FILES=(
  ".env"
  ".env.local"
  ".env.production"
  "credentials.json"
  "service-account.json"
  "*.pem"
  "*.key"
  "*.p12"
  "*.pfx"
  "id_rsa"
  "id_dsa"
)

echo ""
echo "Checking for sensitive files..."
for file_pattern in "${SENSITIVE_FILES[@]}"; do
  found_files=$(find . -name "$file_pattern" -not -path "*/\.*" -not -path "*/node_modules/*" -not -path "*/__pycache__/*" 2>/dev/null || true)
  if [ ! -z "$found_files" ]; then
    echo -e "${YELLOW}[WARNING]${NC} Sensitive file found: $found_files"

    # .gitignore に含まれているか確認
    for file in $found_files; do
      if git check-ignore -q "$file" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} File is in .gitignore"
      else
        echo -e "  ${RED}✗${NC} File is NOT in .gitignore"
        ERRORS_FOUND=$((ERRORS_FOUND + 1))
      fi
    done
    WARNINGS_FOUND=$((WARNINGS_FOUND + 1))
  fi
done

###############################################################################
# Phase 2: .gitignore 検証
###############################################################################
echo ""
echo "[Phase 2] Validating .gitignore..."

REQUIRED_IGNORES=(
  # Python
  "__pycache__/"
  "*.py[cod]"
  "*.pyo"
  "*.pyd"
  ".Python"
  "*.egg-info/"
  "dist/"
  "build/"
  # 環境変数
  ".env"
  ".env.local"
  ".env.*.local"
  # IDE
  ".vscode/"
  ".idea/"
  "*.swp"
  "*.swo"
  "*~"
  # バックアップ
  "*.backup"
  "*.bak"
  # ログ
  "*.log"
  "logs/"
  # OS
  ".DS_Store"
  "Thumbs.db"
  # Node.js
  "node_modules/"
  # 仮想環境
  "venv/"
  ".venv/"
)

if [ ! -f ".gitignore" ]; then
  echo -e "${RED}[ERROR]${NC} .gitignore file not found"
  ERRORS_FOUND=$((ERRORS_FOUND + 1))
else
  missing_ignores=()
  for pattern in "${REQUIRED_IGNORES[@]}"; do
    if ! grep -qF "$pattern" .gitignore; then
      missing_ignores+=("$pattern")
    fi
  done

  if [ ${#missing_ignores[@]} -gt 0 ]; then
    echo -e "${YELLOW}[WARNING]${NC} Missing recommended .gitignore patterns:"
    printf '  - %s\n' "${missing_ignores[@]}"
    WARNINGS_FOUND=$((WARNINGS_FOUND + 1))
  else
    echo -e "${GREEN}✓${NC} .gitignore contains all recommended patterns"
  fi
fi

###############################################################################
# Phase 3: Git状態確認
###############################################################################
echo ""
echo "[Phase 3] Checking git status..."

# Git リポジトリかチェック
if [ ! -d ".git" ]; then
  echo -e "${YELLOW}[WARNING]${NC} Not a git repository"
else
  # ステージングされたファイルを確認
  staged_files=$(git diff --cached --name-only 2>/dev/null || true)
  if [ ! -z "$staged_files" ]; then
    echo -e "${YELLOW}[INFO]${NC} Staged files:"
    echo "$staged_files" | sed 's/^/  - /'

    # 大きなファイルをチェック (>1MB)
    while IFS= read -r file; do
      if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
        if [ "$size" -gt 1048576 ]; then
          size_mb=$(echo "scale=2; $size / 1048576" | bc)
          echo -e "${YELLOW}[WARNING]${NC} Large file staged: $file (${size_mb}MB)"
          WARNINGS_FOUND=$((WARNINGS_FOUND + 1))
        fi
      fi
    done <<< "$staged_files"
  fi

  # 追跡されていないファイルをチェック
  untracked_files=$(git ls-files --others --exclude-standard 2>/dev/null || true)
  if [ ! -z "$untracked_files" ]; then
    untracked_count=$(echo "$untracked_files" | wc -l | xargs)
    echo -e "${YELLOW}[INFO]${NC} Untracked files: $untracked_count"
  fi
fi

###############################################################################
# Phase 4: ファイルシステムチェック
###############################################################################
echo ""
echo "[Phase 4] Checking filesystem..."

# 不要なファイルの検出
UNWANTED_FILES=(
  "*~"
  "*.swp"
  "*.swo"
  ".DS_Store"
  "Thumbs.db"
)

unwanted_found=()
for pattern in "${UNWANTED_FILES[@]}"; do
  found=$(find . -name "$pattern" -not -path "*/\.*" 2>/dev/null || true)
  if [ ! -z "$found" ]; then
    unwanted_found+=("$found")
  fi
done

if [ ${#unwanted_found[@]} -gt 0 ]; then
  echo -e "${YELLOW}[WARNING]${NC} Unwanted files found:"
  printf '%s\n' "${unwanted_found[@]}" | sed 's/^/  - /'
  WARNINGS_FOUND=$((WARNINGS_FOUND + 1))
fi

###############################################################################
# 結果サマリー
###############################################################################
echo ""
echo "=================================="
echo "Security Check Summary"
echo "=================================="
echo -e "Errors:   ${RED}$ERRORS_FOUND${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS_FOUND${NC}"

if [ $ERRORS_FOUND -gt 0 ]; then
  echo ""
  echo -e "${RED}[FAILED]${NC} Security check failed. Please fix the errors above."
  exit 1
elif [ $WARNINGS_FOUND -gt 0 ] && [ "$STRICT_MODE" = true ]; then
  echo ""
  echo -e "${YELLOW}[FAILED]${NC} Security check failed in strict mode due to warnings."
  exit 1
else
  echo ""
  echo -e "${GREEN}[PASSED]${NC} Security check completed successfully."
  exit 0
fi
