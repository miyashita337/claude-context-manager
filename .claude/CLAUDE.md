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
`make test-all` でテスト実行（詳細は Makefile 参照）

---

## ドキュメント管理
各ドキュメントの役割は README.md を参照。重複を避け、簡潔に保つ。

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

## CI自動監視（AgentTeams）

### 概要
`git push`後、PostToolUse hookがCI監視リクエストファイル(`~/.claude/ci-monitoring-request.json`)を作成します。AgentTeamsが有効な場合、ci-monitorエージェントがこれを検知し自動でCI監視・修正を行います。

### 使い方
通常の`git push`を実行するだけで自動的に動作します。特別な操作は不要です。

### 動作フロー
1. `git push` → hookがPR番号を取得しリクエストファイル作成
2. ci-monitorエージェントが30秒間隔でCIステータスをポーリング
3. CI失敗時 → PITFALLS.md検索 → 自動修正（lint、機密情報除外等）
4. 修正をコミット・プッシュ → CI再実行を待機
5. 最大4回リトライ、解決不可の場合はSendMessageで報告

### 手動でCI監視する場合
```bash
make ci-watch PR=<number>
```

### ログ確認
```bash
# CI監視ログ
cat ~/.claude/ci-watch.log

# 最新のサマリー
cat ~/.claude/ci-auto-fix-summary.txt
```

---

## 調査プロセスチェックリスト（BLOCKING REQUIREMENT）
AI自身が確証バイアスを引き起こす可能性があるので、その防御策

### Phase 1: 証拠の収集
- [ ] 直接観察（ユーザー報告、実行結果）> 間接証拠（ログ）> 推測
- [ ] 矛盾する証拠を無視していないか？
- [ ] 「証拠がない ≠ 問題ない」を認識しているか？

### Phase 2: 仮説の検証
- [ ] 対立仮説を2-3個立てたか？
- [ ] **反証を探したか？**（失敗例も調査）
- [ ] 外部検証（公式ドキュメント、実行テスト）を行ったか？
- [ ] **エラーを最小ケースで再現できるか？**（デバッグ実行、単体テスト）
- [ ] **仮説を実験で検証したか？**（コードを実際に実行して動作確認）

### Phase 3: 結論の検証
- [ ] 全ての証拠を説明できるか？
- [ ] 反証を最後にもう一度探したか？
- [ ] 再現可能な形で表現しているか？

**詳細**: プランファイルまたは過去のセッション transcript を参照

**指示方法**:
- 「調査プロセスチェックリストを使って調査してください」
- 「確証バイアスを避けて、科学的に調査してください」

---

### PITFALLS.md検索
- 手動: `grep "エラーメッセージ" .claude/PITFALLS.md`
- 自動: `/pre-commit`, `/git-workflow` が自動検索

---

### エラー解決フロー
1. エラー発生 → `/pre-commit` または `/git-workflow` 実行
2. Skills が PITFALLS.md を自動検索・解決提案
3. 新規エラーは `/fact-check` で調査 → PITFALLS.md に追加

---

### PITFALLS.md エントリ追加

新規エラー発見時：
1. エラーIDを割り当て（GIT-003, HOOK-002, etc.）
2. PITFALLS.md の既存フォーマットに従ってエントリ追加：
   - Error Signature, Context, Root Cause, Solution, Prevention
   - Tags, Severity, Date Added
3. メタデータ更新（Total Entries カウント）

詳細: `.claude/PITFALLS.md` の既存エントリを参照。

---

## 参照
- [IMPROVEMENT_PLAN.md](.claude/IMPROVEMENT_PLAN.md) - 実装計画と進捗
- [SESSION_STARTUP_CHECKLIST.md](../SESSION_STARTUP_CHECKLIST.md) - 起動時チェック
- [PITFALLS.md](.claude/PITFALLS.md) - エラーパターンデータベース
