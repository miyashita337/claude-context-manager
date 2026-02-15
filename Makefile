# Claude Context Manager - Makefile
# 便利なショートカットコマンド集

.PHONY: help install test test-python test-ts test-all test-watch clean build dev lint format format-check startup-check

# デフォルトターゲット: ヘルプを表示
help:
	@echo "Claude Context Manager - 利用可能なコマンド:"
	@echo ""
	@echo "  make startup-check - セッション起動時の健全性チェック"
	@echo "  make install       - 全ての依存関係をインストール"
	@echo "  make test-all      - 全てのテスト（Python + TypeScript）を実行"
	@echo "  make test-python   - Pythonテストのみ実行"
	@echo "  make test-ts       - TypeScriptテストのみ実行"
	@echo "  make test-watch    - テストをwatch モードで実行（TypeScript）"
	@echo "  make lint          - Pythonコードのリント"
	@echo "  make format        - Pythonコードのフォーマット"
	@echo "  make format-check  - フォーマットチェック（CI用）"
	@echo "  make build         - TypeScriptをビルド"
	@echo "  make dev           - 開発モードで実行"
	@echo "  make clean         - ビルド成果物とキャッシュを削除"
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
