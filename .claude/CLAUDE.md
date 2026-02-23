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

### PR作成ルール（BLOCKING REQUIREMENT）

**PR bodyには必ず対応するISSUE番号を `Closes #XX` で記載する。**

```markdown
## Summary
...

Closes #XX  ← 必須。これがないとISSUEが自動Closeされない。
```

**理由**:
- PRマージ時にGitHubがISSUEを自動Close
- ガントチャートの `Target date` が自動セットされる（gantt-auto-dates workflow）
- 振り返り時にPR↔ISSUE の対応が追える

**NGパターン**:
```markdown
# #40 のリンクをbodyに書かない → ISSUEがCloseされず、Target dateがセットされない
```

---

## テスト
`make test-all` でテスト実行（詳細は Makefile 参照）

---

## ドキュメント管理
各ドキュメントの役割は README.md を参照。重複を避け、簡潔に保つ。

---

## Skills

利用可能なSkillsは各Skillファイル（`.claude/skills/*/SKILL.md`）を参照。
主要Skills: `/fact-check` `/pre-commit` `/git-workflow` `/ccusage` `/investigate` `/create-pr` `/review`

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
