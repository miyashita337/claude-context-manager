# Claude Context Manager - Makefile
# 便利なショートカットコマンド集

.PHONY: help install test test-python test-ts test-all test-watch clean build dev lint format format-check startup-check pre-git-check git-clean git-safe-push git-hooks validate-hooks test-hooks fix-hooks backup-hooks restore-hooks ci-watch ci-auto-fix ccusage-report analytics analytics-update validate-analytics review review-latest review-list update-antipatterns install-topic-server start-topic-server stop-topic-server uninstall-topic-server status-topic-server sync-labels

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
	@echo "📋 セッションレビュー:"
	@echo "  make review SESSION=<id>  - セッションデータをキャッシュ（/review の前準備）"
	@echo "  make review-latest        - 最新セッションをキャッシュ"
	@echo "  make review-list          - 既存レビュー一覧表示"
	@echo "  make update-antipatterns  - /antipatterns スキルの更新チェック"
	@echo ""
	@echo "🧠 話題逸脱検出サーバー (Issue #28):"
	@echo "  make install-topic-server   - sentence-transformers インストール + launchd 登録"
	@echo "  make status-topic-server    - サーバー動作確認"
	@echo "  make start-topic-server     - 手動起動"
	@echo "  make stop-topic-server      - 停止"
	@echo "  make uninstall-topic-server - launchd から削除"
	@echo ""
	@echo "🏷️  ラベル管理:"
	@echo "  make sync-labels         - GitHub Labels を priority_config.py と同期"
	@echo ""
	@echo "🔄 CI/CD:"
	@echo "  make ci-watch PR=<n>     - PR #nのCI監視（表示のみ）"
	@echo "  make ci-auto-fix PR=<n>  - PR #nのCI自動修正ループ（最大3回リトライ）"
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

# CI自動修正ループ（手動実行用）
ci-auto-fix:
	@if [ -z "$(PR)" ]; then \
		echo "❌ ERROR: PR number required"; \
		echo "Usage: make ci-auto-fix PR=<number>"; \
		exit 1; \
	fi
	@echo "🔄 Starting CI auto-fix loop for PR #$(PR)..."
	@python3 src/hooks/ci_auto_fix.py $(PR) $(shell pwd) $(if $(MAX_RETRIES),$(MAX_RETRIES),3); \
	case $$? in \
		0) echo "✅ CI passed!" ;; \
		1) echo "⛔ Max retries reached. Manual fix required." ;; \
		2) echo "⛔ Commit/push failed. Check git status." ;; \
	esac

# Analytics ダッシュボード生成 + 自己診断 + ブラウザ起動
analytics:
	@echo "📊 Generating analytics data..."
	@python3 .claude/analytics/engine.py \
		--sessions 10 \
		--html-output .claude/analytics/dashboard/dashboard.html
	@$(MAKE) --no-print-directory validate-analytics
	@echo "🌐 Opening dashboard..."
	@open .claude/analytics/dashboard/dashboard.html 2>/dev/null || \
		xdg-open .claude/analytics/dashboard/dashboard.html 2>/dev/null || \
		echo "Open: .claude/analytics/dashboard/dashboard.html"

# Analytics データのみ更新（ブラウザは開かない）
analytics-update:
	@echo "📊 Updating analytics data..."
	@python3 .claude/analytics/engine.py \
		--sessions 10 \
		--html-output .claude/analytics/dashboard/dashboard.html
	@$(MAKE) --no-print-directory validate-analytics

# Analytics 自己診断（構造チェック + Playwright スクリーンショット）
validate-analytics:
	@bash scripts/validate-analytics.sh

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

# セッションレビュー（AI分析）
review:
	@if [ -z "$(SESSION)" ]; then \
		echo "❌ SESSION is required"; \
		echo "Usage: make review SESSION=<session-id>"; \
		echo "Or:    make review-latest"; \
		exit 1; \
	fi
	@echo "📋 Caching session data for review: $(SESSION)"
	@mkdir -p ~/.claude/reviews/.cache
	@python3 .claude/analytics/engine.py \
		--session-id $(SESSION) \
		--output ~/.claude/reviews/.cache/$(SESSION).json
	@echo "✅ Cache ready. Use /review $(SESSION) in Claude Code for full AI review."

# 最新セッションをレビュー
review-latest:
	@echo "📋 Finding latest session..."
	@LATEST=$$(python3 .claude/analytics/engine.py --sessions 1 --output /tmp/_review_latest.json 2>/dev/null && \
		python3 -c "import json; d=json.load(open('/tmp/_review_latest.json')); print(d['sessions'][0]['session_id'])" 2>/dev/null); \
	if [ -z "$$LATEST" ]; then echo "❌ No sessions found"; exit 1; fi; \
	echo "Latest session: $$LATEST"; \
	$(MAKE) review SESSION=$$LATEST

# 既存レビュー一覧
review-list:
	@echo "📋 Existing reviews (~/.claude/reviews/):"
	@ls ~/.claude/reviews/*.md 2>/dev/null | sed 's|.*/||' || echo "  (no reviews yet)"
	@echo ""
	@echo "💡 Use /review [SESSION_ID] in Claude Code to create a review"

# /antipatterns スキルを公式ドキュメントと照合・更新チェック
update-antipatterns:
	@echo "📋 /antipatterns skill の最終確認日:"
	@grep "最終確認" .claude/skills/antipatterns/SKILL.md || echo "  (日付未設定)"
	@echo ""
	@echo "🔄 更新方法:"
	@echo "  Claude Code 内で実行:"
	@echo "  /fact-check \"Verify antipatterns match official docs at code.claude.com/docs/en/best-practices\""
	@echo ""
	@echo "💡 30日以上経過している場合は更新を推奨します"

# ============================================================
# 話題逸脱検出サーバー管理 (Issue #28)
# ============================================================

TOPIC_SERVER_LABEL = com.claude.topic-server
TOPIC_SERVER_PLIST = $(HOME)/Library/LaunchAgents/$(TOPIC_SERVER_LABEL).plist

install-topic-server:
	@echo "🧠 話題逸脱検出サーバーをインストール中..."
	@chmod +x src/topic-server/install.sh
	@src/topic-server/install.sh

status-topic-server:
	@echo "🧠 Topic Server ステータス:"
	@if curl -sf http://127.0.0.1:8765/health > /dev/null 2>&1; then \
		echo "  ✅ 起動中"; \
		curl -s http://127.0.0.1:8765/health | python3 -m json.tool; \
	else \
		echo "  ❌ 停止中"; \
		echo "  起動: make start-topic-server"; \
	fi

start-topic-server:
	@echo "🧠 Topic Server を起動中..."
	@launchctl start $(TOPIC_SERVER_LABEL) 2>/dev/null || \
		launchctl load $(TOPIC_SERVER_PLIST) 2>/dev/null || \
		(echo "❌ launchd 未登録。先に make install-topic-server を実行してください"; exit 1)
	@echo "✅ 起動リクエスト送信完了"

stop-topic-server:
	@echo "🧠 Topic Server を停止中..."
	@launchctl stop $(TOPIC_SERVER_LABEL) 2>/dev/null && echo "✅ 停止しました" || echo "⚠️  既に停止済みです"

uninstall-topic-server:
	@echo "🧠 Topic Server をアンインストール中..."
	@launchctl unload $(TOPIC_SERVER_PLIST) 2>/dev/null || true
	@rm -f $(TOPIC_SERVER_PLIST)
	@echo "✅ アンインストール完了（sentence-transformers は削除しません）"

# 優先度ラベル管理
sync-labels:
	@echo "🏷️  GitHub Labels を priority_config.py と同期中..."
	@python3 scripts/sync_labels.py
	@echo "✅ ラベル同期完了"

# Token Analyzer インストール
TOOL_DIR = $(HOME)/.claude/tools/token-analyzer

install: ## Token Analyzer を ~/.claude/tools/ にインストール（承認必須）
	@echo "=== Token Analyzer Install ==="
	@SRC_VER=$$(cat src/VERSION); \
	DEST_VER=$$(cat $(TOOL_DIR)/VERSION 2>/dev/null || echo "not installed"); \
	echo "Current: $$DEST_VER → New: $$SRC_VER"; \
	echo ""; \
	echo "Files to install:"; \
	find src/analyzer src/output src/monitor src/cache src/config src/cli.py src/VERSION -type f 2>/dev/null | sort; \
	echo ""; \
	read -p "Install? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		mkdir -p $(TOOL_DIR); \
		rsync -av --delete \
			src/analyzer/ $(TOOL_DIR)/analyzer/; \
		rsync -av --delete \
			src/output/ $(TOOL_DIR)/output/; \
		rsync -av --delete \
			src/monitor/ $(TOOL_DIR)/monitor/; \
		rsync -av --delete \
			src/cache/ $(TOOL_DIR)/cache/; \
		rsync -av --delete \
			src/config/ $(TOOL_DIR)/config/; \
		cp src/cli.py $(TOOL_DIR)/cli.py; \
		cp src/VERSION $(TOOL_DIR)/VERSION; \
		echo "✓ Installed v$$SRC_VER to $(TOOL_DIR)"; \
	else \
		echo "Cancelled."; \
	fi
