#!/usr/bin/env bash
# Pre-Git Check Script
# Git操作前の必須チェック（安定性優先）

set -e

# カラーコード
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_ok() { echo -e "  ${GREEN}✅${NC} $1"; }
print_fail() { echo -e "  ${RED}❌${NC} $1"; }
print_warn() { echo -e "  ${YELLOW}⚠️${NC}  $1"; }

FAILED=0

echo "=== Pre-Git Security & Stability Check ==="
echo ""

# ==========================================
# 1. .gitignore完全性チェック（安定性）
# ==========================================
echo "[1/5] .gitignore completeness..."

REQUIRED_PATTERNS=(
    "__pycache__/"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".env"
    ".env.local"
    "*.backup"
    "*.bak"
    "node_modules/"
    ".DS_Store"
)

for pattern in "${REQUIRED_PATTERNS[@]}"; do
    if ! grep -qF "$pattern" .gitignore 2>/dev/null; then
        print_fail "Missing: $pattern"
        FAILED=1
    fi
done

if [ $FAILED -eq 0 ]; then
    print_ok ".gitignore完全性: OK"
fi
echo ""

# ==========================================
# 2. 不要ファイル検出（安定性）
# ==========================================
echo "[2/5] Unwanted files check..."

UNWANTED_COUNT=0

# Python cache
if find . -type d -name "__pycache__" -path "./.git" -prune -o -print 2>/dev/null | grep -q "__pycache__"; then
    print_warn "__pycache__/ directories found"
    find . -type d -name "__pycache__" -not -path "./.git/*" 2>/dev/null | head -n 5
    UNWANTED_COUNT=$((UNWANTED_COUNT + 1))
fi

# .pyc files
if find . -type f -name "*.pyc" -not -path "./.git/*" 2>/dev/null | grep -q .; then
    print_warn "*.pyc files found"
    UNWANTED_COUNT=$((UNWANTED_COUNT + 1))
fi

# Backup files
if find . -type f \( -name "*.backup" -o -name "*.bak" \) -not -path "./.git/*" 2>/dev/null | grep -q .; then
    print_warn "Backup files found"
    UNWANTED_COUNT=$((UNWANTED_COUNT + 1))
fi

if [ $UNWANTED_COUNT -gt 0 ]; then
    print_warn "Found $UNWANTED_COUNT types of unwanted files"
    echo "    Run: make git-clean"
else
    print_ok "No unwanted files"
fi
echo ""

# ==========================================
# 3. セキュリティスキャン（機密情報検出）
# ==========================================
echo "[3/5] Security scan..."

SECRETS_FOUND=0

# .envファイルチェック
if [ -f .env ]; then
    print_warn ".env file exists"

    if ! grep -qF ".env" .gitignore; then
        print_fail ".env is NOT in .gitignore!"
        FAILED=1
        SECRETS_FOUND=1
    else
        print_ok ".env is in .gitignore"
    fi
fi

# ステージング済みファイルのスキャン
if [ -d .git ]; then
    STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")

    if [ -n "$STAGED_FILES" ]; then
        # .envファイルがステージングされていないか
        if echo "$STAGED_FILES" | grep -qE '\.env'; then
            print_fail ".env file is STAGED for commit!"
            FAILED=1
            SECRETS_FOUND=1
        fi

        # APIキーパターン検出
        while IFS= read -r file; do
            # 除外: テストファイル、ドキュメントファイル（例文を含むため）
            if [[ "$file" == tests/* ]] || \
               [[ "$file" == *.md ]] || \
               [[ "$file" == .claude/PITFALLS.md ]] || \
               [[ "$file" == .claude/skills/* ]]; then
                continue
            fi

            if [ -f "$file" ]; then
                # OpenAI API keys
                if grep -qE 'sk-proj-[a-zA-Z0-9_-]{20,}' "$file" 2>/dev/null; then
                    print_fail "OpenAI API key detected: $file"
                    FAILED=1
                    SECRETS_FOUND=1
                fi

                # Gemini API keys
                if grep -qE 'AIzaSy[a-zA-Z0-9_-]{33}' "$file" 2>/dev/null; then
                    print_fail "Gemini API key detected: $file"
                    FAILED=1
                    SECRETS_FOUND=1
                fi

                # GitHub tokens
                if grep -qE 'ghp_[a-zA-Z0-9]{36}' "$file" 2>/dev/null; then
                    print_fail "GitHub token detected: $file"
                    FAILED=1
                    SECRETS_FOUND=1
                fi
            fi
        done <<< "$STAGED_FILES"
    fi
fi

if [ $SECRETS_FOUND -eq 0 ]; then
    print_ok "No secrets detected"
fi
echo ""

# ==========================================
# 4. Git状態確認
# ==========================================
echo "[4/5] Git repository state..."

if [ ! -d .git ]; then
    print_warn "Not a Git repository"
else
    print_ok "Git repository detected"

    # 初回コミット判定
    if ! git rev-parse HEAD >/dev/null 2>&1; then
        print_warn "Initial commit (no HEAD yet)"
        echo "    → Use 'git rm --cached <file>' instead of 'git reset HEAD'"
    else
        print_ok "Commit history exists"
    fi
fi
echo ""

# ==========================================
# 5. ステージング済みファイル確認
# ==========================================
echo "[5/5] Staged files review..."

if [ -d .git ]; then
    STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')

    if [ "$STAGED_COUNT" -eq 0 ]; then
        print_warn "No files staged"
    elif [ "$STAGED_COUNT" -gt 10 ]; then
        print_warn "Large number of files staged: $STAGED_COUNT"
        echo "    Files:"
        git diff --cached --name-only 2>/dev/null | head -n 10
        echo "    (showing first 10 files...)"
    else
        print_ok "$STAGED_COUNT file(s) staged"
        git diff --cached --name-only 2>/dev/null | sed 's/^/    /'
    fi
fi
echo ""

# ==========================================
# 結果サマリー
# ==========================================
echo "=== Check Summary ==="

if [ $FAILED -eq 0 ]; then
    print_ok "All checks passed"
    echo ""
    echo "You can proceed with Git operations:"
    echo "  git add <files>"
    echo "  git commit -m 'message'"
    echo "  git push"
    exit 0
else
    print_fail "Some checks failed"
    echo ""
    echo "Please fix the issues above before committing."
    echo ""
    echo "Common fixes:"
    echo "  - Remove .env from staging: git rm --cached .env"
    echo "  - Clean unwanted files: make git-clean"
    echo "  - Update .gitignore and re-stage"
    exit 1
fi
