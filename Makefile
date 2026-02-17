# Claude Context Manager - Makefile
# 便利なショートカットコマンド集

.PHONY: help install test test-python test-ts test-all test-watch clean build dev lint format format-check startup-check pre-git-check git-clean git-safe-push git-hooks validate-hooks test-hooks fix-hooks backup-hooks restore-hooks ci-watch ccusage-report analytics analytics-update

# デフォルトターゲット: ヘルプを表示
help:
	@echo "Claude Context Manager - 利用可能なコマンド:"
	@echo ""
	@echo "🚀 セッション管理:"
	@echo "  make startup-check    - セッション起動時の健全性チェック"
	@echo ""
	@echo "🔒 Git操作（安全性優先）:"
	@echo "  make pre-git-check    - Git操作前の必須チェック"
	@echo "  make git-clean        - 不要ファイル削除（__pycache__, *.pyc, *.backup）"
	@echo "  make git-safe-push    - 安全なGit push（チェック付き）"
	@echo "  make git-hooks        - Git hooksインストール（pre-commit）"
	@echo ""
	@echo "🔧 Hook管理:"
	@echo "  make validate-hooks   - Hook設定の検証（整合性チェック含む）"
	@echo "  make test-hooks       - Hook動作テスト"
	@echo "  make fix-hooks        - Hook設定の自動修復（バックアップから復元）"
	@echo "  make backup-hooks     - Hook設定のバックアップ作成"
	@echo "  make restore-hooks    - Hook設定をバックアップから復元"
	@echo ""
	@echo "📊 分析:"
	@echo "  make ccusage-report   - Claude Codeトークン使用量レポート（今日）"
	@echo "  make analytics        - Analytics ダッシュボードを生成・起動"
	@echo "  make analytics-update - Analytics データを更新（ブラウザは開かない）"
	@echo ""
	@echo "🔄 CI/CD:"
	@echo "  make ci-watch PR=<n>  - PR #nのCI監視（自動リトライ）"
	@echo ""
	@echo "📦 開発:"
	@echo "  make install          - 全ての依存関係をインストール"
	@echo "  make test-all         - 全てのテスト（Python + TypeScript）"
	@echo "  make test-python      - Pythonテストのみ"
	@echo "  make test-ts          - TypeScriptテストのみ"
	@echo "  make lint             - Pythonコードのリント"
	@echo "  make format           - Pythonコードのフォーマット"
	@echo "  make build            - TypeScriptをビルド"
	@echo "  make clean            - ビルド成果物とキャッシュを削除"
	@echo ""

# 依存関係のインストール
install:
	@echo "依存関係をインストール中..."
	npm install
	@echo "Python開発用依存関係をインストール中..."
	pip install -r requirements-dev.txt
	@echo "インストール完了！"

# 全テストを実行
test-all: test-python test-ts
	@echo "全てのテストが完了しました！"

# Pythonテストを実行
test-python:
	@echo "Pythonテストを実行中..."
	python3 -m pytest tests/ -v --cov=src/hooks

# TypeScriptテストを実行
test-ts:
	@echo "TypeScriptテストを実行中..."
	npm test

# TypeScriptテストをwatchモードで実行
test-watch:
	@echo "テストをwatchモードで実行中..."
	npm run test:watch

# TypeScriptをビルド
build:
	@echo "TypeScriptをビルド中..."
	npm run build
	@echo "ビルド完了！"

# 開発モードで実行
dev:
	@echo "開発モードで実行中..."
	npm run dev

# クリーンアップ
clean:
	@echo "ビルド成果物とキャッシュを削除中..."
	rm -rf build/
	rm -rf node_modules/.cache/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "クリーンアップ完了！"

# CI用テスト（カバレッジレポート付き）
test-ci:
	@echo "CI用テストを実行中..."
	npm run test:ci

# Pythonコードのリント
lint:
	@echo "Pythonコードをリント中..."
	npm run lint:python

# Pythonコードのフォーマット
format:
	@echo "Pythonコードをフォーマット中..."
	npm run format:python

# フォーマットチェック（CI用）
format-check:
	@echo "フォーマットをチェック中..."
	npm run format:check

# セッション起動時チェック
startup-check:
	@bash scripts/startup-check.sh

# Git操作前チェック（安定性優先）
pre-git-check:
	@bash scripts/pre-git-check.sh

# Git不要ファイル削除
git-clean:
	@echo "不要ファイルを削除中..."
	@find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -not -path "./.git/*" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -not -path "./.git/*" -delete 2>/dev/null || true
	@find . -type f \( -name "*.backup" -o -name "*.bak" \) -not -path "./.git/*" -delete 2>/dev/null || true
	@echo "✅ クリーンアップ完了"

# 安全なGit push（チェック統合）
git-safe-push: pre-git-check
	@echo ""
	@echo "📊 Git Status:"
	@git status --short
	@echo ""
	@read -p "Continue with push? (yes/no): " answer; \
	if [ "$$answer" = "yes" ]; then \
		git push; \
		echo "✅ Push complete"; \
	else \
		echo "❌ Push cancelled"; \
	fi

# Git hooksインストール
git-hooks:
	@bash scripts/install-git-hooks.sh

# Hook設定の検証（整合性チェック含む）
validate-hooks:
	@bash scripts/validate-hooks.sh

# Hook動作テスト（設定検証 + Pythonテスト実行）
test-hooks: validate-hooks
	@echo ""
	@echo "=== Hook Tests ==="
	@python3 -m pytest tests/test_hooks.py -v --tb=short

# Hook設定の自動修復（バックアップから復元）
fix-hooks:
	@bash scripts/restore-hooks.sh
	@echo ""
	@bash scripts/validate-hooks.sh

# Hook設定のバックアップ作成
backup-hooks:
	@bash scripts/backup-hooks.sh

# Hook設定をバックアップから復元
restore-hooks:
	@bash scripts/restore-hooks.sh

# CI監視（自動リトライ）
ci-watch:
	@if [ -z "$(PR)" ]; then \
		echo "❌ ERROR: PR number required"; \
		echo "Usage: make ci-watch PR=<number>"; \
		exit 1; \
	fi
	@echo "🔍 Monitoring PR #$(PR) CI status..."
	@echo ""
	@while true; do \
		PENDING=$$(gh pr checks $(PR) --json bucket --jq '[.[] | select(.bucket == "pending")] | length'); \
		FAILED=$$(gh pr checks $(PR) --json bucket --jq '[.[] | select(.bucket == "fail")] | length'); \
		TOTAL=$$(gh pr checks $(PR) --json bucket --jq 'length'); \
		if [ "$$PENDING" -gt 0 ]; then \
			COMPLETED=$$(($$TOTAL - $$PENDING)); \
			echo "⏳ $$COMPLETED/$$TOTAL checks completed ($$PENDING pending)..."; \
			sleep 10; \
		elif [ "$$FAILED" -gt 0 ]; then \
			echo ""; \
			echo "❌ $$FAILED/$$TOTAL CI check(s) FAILED:"; \
			gh pr checks $(PR) --json bucket,name --jq '.[] | select(.bucket == "fail") | "  - " + .name'; \
			echo ""; \
			echo "Check details: gh pr view $(PR) --web"; \
			echo "After fixing, re-run: make ci-watch PR=$(PR)"; \
			exit 1; \
		else \
			echo ""; \
			echo "✅ All $$TOTAL CI checks passed!"; \
			gh pr checks $(PR); \
			exit 0; \
		fi; \
	done

# Analytics ダッシュボード生成 + ブラウザ起動
analytics:
	@echo "📊 Generating analytics data..."
	@python3 .claude/analytics/engine.py \
		--sessions 10 \
		--output .claude/analytics/dashboard/analytics.json
	@echo "🌐 Opening dashboard..."
	@open .claude/analytics/dashboard/index.html 2>/dev/null || \
		xdg-open .claude/analytics/dashboard/index.html 2>/dev/null || \
		echo "Open: .claude/analytics/dashboard/index.html"

# Analytics データのみ更新（ブラウザは開かない）
analytics-update:
	@echo "📊 Updating analytics data..."
	@python3 .claude/analytics/engine.py \
		--sessions 10 \
		--output .claude/analytics/dashboard/analytics.json
	@echo "✅ Done. Open .claude/analytics/dashboard/index.html to view."

# ccusageトークン使用量レポート
ccusage-report:
	@if ! command -v ccusage &>/dev/null; then \
		echo "❌ ccusage is not installed"; \
		echo "   Fix: npm install -g ccusage"; \
		exit 1; \
	fi
	@echo "📊 Claude Code Token Usage - Today"
	@echo ""
	@ccusage daily --since "$$(date +%Y%m%d)"
	@echo ""
	@echo "💡 For more options, use the /ccusage skill in Claude Code"
