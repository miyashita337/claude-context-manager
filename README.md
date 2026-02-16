# Claude Context Manager

[![Tests](https://github.com/yourusername/claude-context-manager/actions/workflows/test.yml/badge.svg)](https://github.com/yourusername/claude-context-manager/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/yourusername/claude-context-manager/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/claude-context-manager)

A hook-based system that automatically captures and preserves Claude Code conversation history before automatic compaction occurs.

## Overview

Claude Context Manager is a lightweight tool that integrates with Claude Code to:

- **Automatically capture conversation history** (both user prompts and Claude responses)
- **Preserve context before compaction** prevents loss of valuable conversation data
- **Generate searchable Markdown files** compatible with Obsidian and other knowledge management tools
- **Track token usage** to monitor context consumption and detect Lost-in-the-middle issues
- **Enable conversation search** across all historical sessions

## Key Features

### Phase 1 (MVP) - Current Implementation

- Automatic conversation capture via Claude Code hooks
- Real-time logging during sessions
- Markdown export with YAML frontmatter
- Token estimation and statistics
- Session finalization on Claude Code exit
- Organized storage in `~/.claude/context-history/`

### Phase 2 (Roadmap)

- Web dashboard for browsing conversations
- Advanced search with filters
- Token visualization and analytics
- Export to multiple formats (Zenn, PDF, JSON)
- Log rotation and archiving
- Cloud storage integration

## Architecture

### Hook-Based System

Claude Context Manager uses Claude Code's hook system to capture conversations without modifying the core application:

```
User Prompt → UserPromptSubmit Hook (Python)
              ↓
              SessionLogger → Temporary JSON

Claude Response → PostToolUse Hook (Python)
                  ↓
                  SessionLogger → Temporary JSON

Session End → Stop Hook (Python)
              ↓
              TypeScript Finalization → Markdown Generation
```

### Components

1. **Python Hooks** (Real-time capture)
   - `user-prompt-submit.py` - Captures user inputs
   - `post-tool-use.py` - Captures Claude tool usage and responses
   - `stop.py` - Triggers session finalization
   - `shared/logger.py` - Session logging utilities
   - `shared/config.py` - Configuration and path management

2. **TypeScript Finalization** (Post-processing)
   - `cli/finalize-session.ts` - Converts JSON logs to Markdown
   - `core/markdown-writer.ts` - Generates formatted Markdown
   - `core/tokenizer.ts` - Token estimation and analysis
   - `types/session.ts` - Type definitions

## Installation

### Prerequisites

- Node.js 20.x or higher
- Python 3.8 or higher
- Claude Code CLI installed and configured

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/claude-context-manager.git
cd claude-context-manager
```

2. Install dependencies:

```bash
npm install
```

3. Build the project:

```bash
npm run build
```

4. Link hooks to Claude Code:

The hooks are located in `src/hooks/` and should be automatically detected by Claude Code when it runs from this project directory. Alternatively, you can symlink them:

```bash
# Link hooks to your global Claude Code configuration
ln -s $(pwd)/src/hooks/user-prompt-submit.py ~/.claude/hooks/
ln -s $(pwd)/src/hooks/post-tool-use.py ~/.claude/hooks/
ln -s $(pwd)/src/hooks/stop.py ~/.claude/hooks/
ln -s $(pwd)/src/hooks/shared ~/.claude/hooks/
```

## Usage

### Automatic Capture

Once installed, the hooks automatically capture conversations whenever you use Claude Code. No manual intervention is required.

### File Storage

Conversations are stored in:

```
~/.claude/context-history/
├── .tmp/                    # Temporary JSON logs during session
├── sessions/                # Finalized Markdown files
│   └── YYYY-MM-DD/         # Organized by date
│       └── session-{id}.md # Individual session files
├── archives/               # Archived logs (Phase 2)
└── .metadata/              # Session metadata (Phase 2)
```

### Markdown Format

Each session is saved as a Markdown file with frontmatter:

```markdown
---
date: 2026-02-11T12:34:56Z
session_id: abc123
total_tokens: 5420
user_tokens: 1200
assistant_tokens: 4220
compact_detected: false
tags: [claude, conversation]
---

# Claude対話履歴 - 2026-02-11

## 12:34:56 - ユーザー

User prompt here...

**Tokens**: 150 (推定)

## 12:35:01 - Claude

Claude's response...

**Tokens**: 500 (推定)

---

**セッション統計**:
- 総Token数: 5420 (推定)
- ユーザーToken: 1200
- ClaudeToken: 4220
- Compact: なし
- セッション時間: 15分
- エントリ数: 8
```

## セッション起動時チェック

新しいセッションを開始したら、以下のコマンドで健全性チェックを実行できます：

```bash
make startup-check
```

このコマンドは以下をチェックします：

- **Hook動作確認**: UserPromptSubmit、PostToolUse、Stopの動作確認
- **ログファイル作成確認**: `.tmp/`ディレクトリへのログ記録
- **エラーログの確認**: 最近のエラーの有無
- **Hook設定の確認**: プロジェクトhookの設定状態
- **テストスイートの実行**: 自動テストの実行

すべて ✅ なら、Claude Context Manager は正常に動作しています！

詳細は [SESSION_STARTUP_CHECKLIST.md](./SESSION_STARTUP_CHECKLIST.md) を参照してください。

## Skills（新機能）

Claude Context Manager には、エラー予防と自動解決のための3つの Claude Code Skills が含まれています。

### 利用可能なSkills

#### 1. `/fact-check` - 公式ドキュメント照合

実装内容が公式ドキュメントと一致しているか自動検証します。

```bash
# 使用例
/fact-check "Verify Claude Code hook paths are official"
/fact-check "Check if .claude/settings.json is the correct hook configuration path"
```

**特徴**:
- WebSearch/WebFetchで公式ドキュメント検索
- 現在の実装と比較
- 差異を詳細レポート

**いつ使うか**:
- 新機能実装前
- 予期しない動作が発生した時
- 設定パスやフォーマットが不明な時

---

#### 2. `/pre-commit` - コミット前自動チェック

`make pre-git-check`を実行し、エラーを自動解決します。

```bash
# 使用例
/pre-commit
```

**実行内容**:
1. `make pre-git-check`実行
2. エラー検出時、PITFALLS.mdを自動検索
3. 安全な修正を自動適用
4. 再チェック実行

**自動修正例**:
- 機密情報検出 → unstage + .gitignoreに追加
- 不要ファイル検出 → .gitignoreに追加
- 初期コミットHEADエラー → 正しいコマンド提案

---

#### 3. `/git-workflow` - 安全なGit操作ガイド

Git操作を安全にガイドします（初期コミット対応、force push防止）。

```bash
# 使用例
/git-workflow
```

**保護機能**:
- 初期コミット検出とHEADエラー防止
- force push防止（main/master）
- コミット前セキュリティチェック
- 段階的ガイダンス

**特に有用なシーン**:
- 新規リポジトリでの初回コミット
- main/masterへのpush前
- gitエラー発生時

---

### PITFALLS.md - エラーパターンデータベース

過去に発生したエラーとその解決策を記録したナレッジベースです。

**含まれるエラー**:
- `GIT-001`: 初期コミットHEADエラー
- `GIT-002`: 非公式hookパス
- `HOOK-001`: hook実行がテストで検出されない
- `SEC-001`: 機密情報パターン検出

**検索方法**:
```bash
# エラーメッセージで検索
grep "fatal: ambiguous argument" .claude/PITFALLS.md

# エラーIDで検索
grep "GIT-001" .claude/PITFALLS.md

# タグで検索
grep "Tags.*security" .claude/PITFALLS.md
```

**Skills経由の自動検索**:
- `/pre-commit`: エラー発生時に自動検索・解決提案
- `/git-workflow`: git関連エラーを自動検索

詳細は [.claude/CLAUDE.md](.claude/CLAUDE.md) の「Skills使用方法」セクションを参照してください。

## AgentTeams - CI自動修正システム

AgentTeamsを有効にすると、`git push`後にCIを自動監視し、失敗時に自動修正を試みます。

### 有効化

`settings.json`に以下を追加:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

### 仕組み

1. `git push`を検出すると、PostToolUse hookがCI監視リクエストを作成
2. ci-monitorエージェントがPRのCIステータスをポーリング（30秒間隔）
3. CI失敗時、`ci-auto-fixer.py`がPITFALLS.mdを検索し自動修正を適用
4. 修正をコミット・プッシュし、CIの再実行を待機
5. 最大4回リトライ後、手動対応が必要な場合はSendMessageで報告

### 手動CI監視

AgentTeamsを使わずにCI監視する場合:

```bash
make ci-watch PR=<number>
```

### CLI Commands (Phase 2)

Future commands for enhanced functionality:

```bash
# View current session status
claude-context status

# Search conversation history
claude-context search "keyword"

# Export to Obsidian format
claude-context export --format obsidian

# Export to Zenn article
claude-context export --format zenn --output article.md

# View session statistics
claude-context stats

# Configure log rotation
claude-context config --rotate-days 30

# Manual log rotation
claude-context rotate

# List archives
claude-context archive list

# Restore from archive
claude-context archive restore <archive-id>
```

## Directory Structure

```
claude-context-manager/
├── .claude/                    # Claude Code configuration
│   ├── hooks/                  # Hook symlinks (local project)
│   └── settings.local.json     # Local permissions
├── src/
│   ├── cli/                    # CLI commands (Phase 2)
│   │   └── finalize-session.ts # Session finalization script
│   ├── core/                   # Core logic
│   │   ├── markdown-writer.ts  # Markdown generation
│   │   └── tokenizer.ts        # Token estimation
│   ├── hooks/                  # Python hooks
│   │   ├── user-prompt-submit.py
│   │   ├── post-tool-use.py
│   │   ├── stop.py
│   │   └── shared/            # Shared utilities
│   │       ├── __init__.py
│   │       ├── config.py      # Configuration
│   │       └── logger.py      # Session logger
│   └── types/                  # TypeScript types
│       └── session.ts
├── tests/                      # Test files (Phase 2)
├── build/                      # Compiled TypeScript
├── package.json
├── tsconfig.json
├── spec.md                     # Requirements specification
└── README.md
```

## Configuration

### Storage Locations

Default paths can be customized by setting environment variables:

- `CLAUDE_CONTEXT_DIR` - Base directory (default: `~/.claude/context-history`)

### Token Estimation

Currently uses a simple heuristic (1 token ≈ 4 characters). Phase 2 will integrate with tiktoken or Anthropic's official tokenizer for more accurate counting.

## Troubleshooting

### Hooks Not Running

1. Verify hooks have executable permissions:
```bash
chmod +x src/hooks/*.py
```

2. Check Python shebang is correct:
```bash
head -1 src/hooks/user-prompt-submit.py
# Should output: #!/usr/bin/env python3
```

3. Ensure hooks are in the correct location:
```bash
ls -la ~/.claude/hooks/
```

### Session Not Finalizing

1. Check TypeScript build is up to date:
```bash
npm run build
```

2. Verify finalize-session.ts is executable:
```bash
ls -la build/cli/finalize-session.js
```

3. Check temporary logs exist:
```bash
ls -la ~/.claude/context-history/.tmp/
```

### Missing Dependencies

```bash
# Reinstall Node dependencies
npm install

# Verify Python 3 is available
python3 --version

# Check required Python modules
python3 -c "import json, sys, subprocess; print('OK')"
```

## Development

### Build

```bash
# Compile TypeScript
npm run build

# Development with auto-reload
npm run dev
```

### Testing

#### ローカルテスト環境

プロジェクトには包括的なテストスイートが用意されています。

**前提条件:**

```bash
# 依存関係をインストール
make install
# または手動で
npm install
pip install -r requirements-dev.txt
```

**テストの実行:**

```bash
# 全テスト（Python + TypeScript）を実行
make test-all
# または
npm run test:all

# Pythonテストのみ
make test-python
# または
npm run test:python

# TypeScriptテストのみ
make test-ts
# または
npm test

# Watchモード（開発中に便利）
make test-watch
# または
npm run test:watch

# カバレッジレポート付き
npm run test:coverage  # TypeScript
python3 -m pytest tests/ --cov=src/hooks --cov-report=html  # Python

# 特定のテストファイルを実行
npm test -- tests/integration.test.ts
pytest tests/test_hooks.py -v
```

**コード品質チェック:**

```bash
# Pythonコードのリント
npm run lint:python

# Pythonコードのフォーマット
npm run format:python

# フォーマットチェック（CI用）
npm run format:check
```

**テストカバレッジ:**

現在のテストスイートは以下をカバーしています：

- **Python Hooks**: 10のテストケース
  - SessionLogger機能（ファイル作成、エントリ追加、統計計算）
  - 日本語コンテンツ処理
  - 設定とディレクトリ管理
  - Hookの入出力（JSON処理）
  - エラーハンドリング
  - 統合テスト

- **TypeScript Core** (Phase 2):
  - Markdown生成
  - Tokenizer
  - CLI コマンド

**CI/CD:**

GitHub Actionsで自動テストが実行されます：

```bash
# CI環境でのテストをローカルで実行
npm run test:ci
```

詳細なテスト手順とベストプラクティスについては、[CONTRIBUTING.md](CONTRIBUTING.md)を参照してください。

### Continuous Integration

This project uses GitHub Actions for automated testing and quality assurance.

#### CI/CD Pipeline

Every push and pull request triggers the following jobs:

1. **Python Tests** - Matrix testing on Python 3.10, 3.11, 3.12
2. **TypeScript Tests** - Matrix testing on Node.js 18, 20
3. **Integration Tests** - End-to-end testing with both environments
4. **Code Linting** - Code quality checks (flake8, black, TypeScript compiler)

#### Branch Protection (Recommended Setup)

For production use, configure the following branch protection rules on GitHub:

1. Go to **Settings** → **Branches** → **Branch protection rules**
2. Add rule for `main` branch:
   - Require a pull request before merging
   - Require status checks to pass before merging:
     - `Python Tests (3.10)`
     - `Python Tests (3.11)`
     - `Python Tests (3.12)`
     - `TypeScript Tests (18)`
     - `TypeScript Tests (20)`
     - `Integration Tests (Python + TypeScript)`
     - `Code Linting`
   - Require branches to be up to date before merging
   - Require conversation resolution before merging

This ensures all tests pass before code can be merged to main.

### Project Structure

- **Phase 1 Focus**: Hook implementation and basic Markdown export
- **Phase 2 Goals**: CLI commands, web dashboard, advanced features

## Roadmap

### Phase 1 (Current) - MVP
- [x] Hook-based capture system
- [x] Python hooks for real-time logging
- [x] TypeScript session finalization
- [x] Markdown generation with frontmatter
- [x] Token estimation
- [ ] CLI status command
- [ ] CLI search command

### Phase 2 - Advanced Features
- [ ] Web dashboard (React + Next.js)
- [ ] Full-text search
- [ ] Token visualization graphs
- [ ] Multiple export formats (Zenn, PDF, JSON)
- [ ] Log rotation and archiving
- [ ] Cloud storage integration (S3, Google Drive)
- [ ] Compact detection and analysis

### Phase 3 - Enterprise Features
- [ ] Team collaboration features
- [ ] Advanced analytics
- [ ] LLM-powered conversation summarization
- [ ] Integration with other AI tools

## Technical Stack

### Backend
- **Language**: TypeScript + Node.js
- **Hooks**: Python 3.8+
- **Token Estimation**: Custom heuristic (Phase 1), tiktoken (Phase 2)

### Frontend (Phase 2)
- **Framework**: React + Next.js
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui

### Storage
- **Phase 1**: Markdown + JSON (file-based)
- **Phase 2**: SQLite for indexing + file-based storage

## License

ISC

## Contributing

Contributions are welcome. Please ensure:

- Code follows TypeScript/Python best practices
- Commit messages are clear and descriptive
- Tests are included for new features (Phase 2)
- Documentation is updated

## Known Issues

1. Token estimation is approximate (1 token ≈ 4 chars). Will be improved in Phase 2 with tiktoken integration.
2. Large sessions may take a few seconds to finalize. This is expected behavior.
3. Image/screenshot capture is not yet implemented (planned for Phase 2).

## FAQ

**Q: Does this work with Claude API?**
A: Currently only supports Claude Code CLI. Claude API support is planned for Phase 2.

**Q: Will this slow down my Claude Code sessions?**
A: No. Hooks run asynchronously and won't block your interactions.

**Q: Can I use this with other AI assistants?**
A: The architecture is extensible. Support for other assistants (ChatGPT, Gemini) could be added in the future.

**Q: Where can I see my conversation history?**
A: Check `~/.claude/context-history/sessions/` for Markdown files organized by date.

**Q: How accurate is token counting?**
A: Currently uses a 4:1 character-to-token ratio. Phase 2 will integrate official tokenizers for better accuracy.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Current Status**: Phase 1 MVP - Core functionality implemented and working.
# Test CI monitoring log output
