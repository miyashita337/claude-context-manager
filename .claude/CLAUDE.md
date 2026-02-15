# Claude Context Manager - プロジェクト固有ガイドライン

## 🎯 プロジェクト概要
Claude Codeの対話履歴を自動保存・管理するhookシステム

---

## Git操作（プロジェクト固有ルール）

### 必須コマンド
```bash
# Git操作前
make pre-git-check

# 不要ファイル削除
make git-clean

# 安全なプッシュ
make git-safe-push
```

### このプロジェクト特有の注意点

#### 1. Hook設定ファイル
```bash
.claude/hooks/hooks.json  # プロジェクト固有のhook設定
~/.claude/settings.json   # グローバル設定（重複注意）
```

**重複チェック**:
- プロジェクトhookとグローバルhookの重複を避ける
- `make startup-check`で重複を検出

#### 2. 機密情報
```bash
# 除外必須
.env                              # APIキー（OPENAI, GEMINI）
.claude/settings.local.json       # ローカル設定
mcp-chatgpt-server/.env           # MCPサーバー設定
```

#### 3. セッションログ
```bash
~/.claude/context-history/        # 保存先（Gitで追跡しない）
  ├── .tmp/                       # 一時ログ
  ├── sessions/                   # 確定ログ
  └── archives/                   # アーカイブ
```

---

## 開発ワークフロー

### セッション開始時
```bash
make startup-check  # Hook動作確認、ログファイル確認
```

### コード変更後
```bash
make test-all       # Python + TypeScript テスト
make lint           # コード品質チェック
```

### Git操作時
```bash
make pre-git-check  # セキュリティ + 安定性チェック
make git-clean      # 不要ファイル削除（必要に応じて）
git add <files>     # 個別ファイル指定（推奨）
git commit          # pre-commitフックが自動実行（P1実装後）
```

---

## テスト

### 実行方法
```bash
make test-all       # 全テスト
make test-python    # Pythonのみ
make test-ts        # TypeScriptのみ
```

### 期待結果
- Python: 12/13 PASS（stopフックは既知の問題）
- TypeScript: 全PASS

---

## ドキュメント管理

### 役割分担
| ファイル | 役割 | 更新タイミング |
|---------|------|---------------|
| README.md | プロジェクト概要、セットアップ | 機能追加時 |
| SESSION_STARTUP_CHECKLIST.md | セッション起動時の手動チェック | 手順変更時 |
| IMPROVEMENT_PLAN.md | 改善タスク管理 | タスク完了時 |
| CLAUDE.md（これ） | 開発ガイドライン | ワークフロー変更時 |

### 整理原則
- **役割が明確**であること
- **重複を削除**（ソースコードで確認できる内容は削除）
- **簡潔に保つ**（無駄を省く）

---

## AgentTeam活用（このプロジェクト）

### 利用実績
- セキュリティエンジニア: 機密情報検出、多層防御戦略
- DevOpsエンジニア: Git操作改善、CI/CD統合
- QAエンジニア: 品質ゲート、テスト戦略
- PM: プロセス改善、プロンプト最適化
- シニアエンジニア: アーキテクチャレビュー

### 次回活用シーン
- 大規模リファクタリング前
- 新機能設計時
- セキュリティ監査
- 定期的な振り返り（タスク完了時 + 肥大化検知時）

---

## 参照
- [IMPROVEMENT_PLAN.md](.claude/IMPROVEMENT_PLAN.md) - 実装計画と進捗
- [SESSION_STARTUP_CHECKLIST.md](../SESSION_STARTUP_CHECKLIST.md) - 起動時チェック
