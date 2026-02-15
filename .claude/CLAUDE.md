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
.claude/settings.json     # プロジェクト固有のhook設定（公式パス）
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

## Skills使用方法（新機能）

### 利用可能なSkills

#### `/fact-check` - 公式ドキュメント照合
**用途**: 実装内容が公式ドキュメントと一致しているか検証

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

#### `/pre-commit` - コミット前自動チェック
**用途**: `make pre-git-check`を実行し、エラーを自動解決

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

#### `/git-workflow` - 安全なGit操作ガイド
**用途**: Git操作を安全にガイド（初期コミット対応、force push防止）

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

### PITFALLS.md検索方法

#### 手動検索
```bash
# エラーメッセージで検索
grep "fatal: ambiguous argument" .claude/PITFALLS.md

# エラーIDで検索
grep "GIT-001" .claude/PITFALLS.md

# タグで検索
grep "Tags.*security" .claude/PITFALLS.md
```

#### Skills経由の自動検索
Skillsは自動的にPITFALLS.mdを検索します：
- `/pre-commit`: エラー発生時に自動検索・解決提案
- `/git-workflow`: git関連エラーを自動検索

---

### エラー解決ワークフロー

#### 標準フロー
```
1. エラー発生
   ↓
2. /pre-commit または /git-workflow 実行
   ↓
3. Skillが自動的にPITFALLS.md検索
   ↓
4. 解決策適用（自動または手動）
   ↓
5. 再チェック
```

#### 新規エラーの場合
```
1. エラー発生
   ↓
2. /fact-check で公式ドキュメント確認
   ↓
3. 手動解決
   ↓
4. PITFALLS.mdに新規エントリ追加
   - 次回からSkillsが自動検出・解決
```

---

### PITFALLS.mdエントリ追加方法

新しいエラーパターンを発見した場合：

1. **エラーIDを割り当て**
   ```
   GIT-003, HOOK-002, SEC-002, etc.
   ```

2. **エントリを追加**
   ```markdown
   ### [ERROR-ID]: [Brief Title]

   **Error Signature**: `[exact error message]`

   **Context**: [When this occurs]

   **Root Cause**: [Why this happens]

   **Solution**:
   [step-by-step fix]

   **Prevention**:
   [how to avoid in future]

   **Tags**: `[tag1]`, `[tag2]`

   **Severity**: [Critical/High/Medium/Low]

   **Date Added**: YYYY-MM-DD
   ```

3. **メタデータ更新**
   - Total Entries カウントを増やす
   - Version History に追記

---

## 参照
- [IMPROVEMENT_PLAN.md](.claude/IMPROVEMENT_PLAN.md) - 実装計画と進捗
- [SESSION_STARTUP_CHECKLIST.md](../SESSION_STARTUP_CHECKLIST.md) - 起動時チェック
- [PITFALLS.md](.claude/PITFALLS.md) - エラーパターンデータベース
