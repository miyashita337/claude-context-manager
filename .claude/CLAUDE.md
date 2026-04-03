# Claude Context Manager - プロジェクト固有ガイドライン

## プロジェクト概要
Claude Code品質管理ツールキット + トークン消費分析

主要機能:
- **Token Analyzer**: プロジェクト別トークン消費量の可視化（JSONL解析 + ccusageコスト連携）
- **PITFALLS.md**: 構造化エラーパターンDB
- **品質管理Skills**: `/fact-check` `/pre-commit` `/git-workflow` `/context-check`
- **話題逸脱検知**: topic-serverによるセッション品質管理
- **CI自動監視**: hookベースの自動修正ループ

### Token Analyzer 使い方
```bash
# プロジェクト別トークン消費レポート
python3 -m src.cli --top 10

# コストなし（トークン量のみ）
python3 -m src.cli --top 10 --no-cost

# ランタイムにデプロイ（ユーザー承認必須）
make install
# → ~/.claude/tools/token-analyzer/ にインストール
```

---

## Git操作（プロジェクト固有ルール）

### 必須コマンド
```bash
make pre-git-check  # Git操作前の必須チェック
make git-clean      # 不要ファイル削除
make git-safe-push  # 安全なプッシュ
```

### 注意点

**Hook設定ファイル**:
- `.claude/settings.json` — プロジェクト固有（公式パス）
- `~/.claude/settings.json` — グローバル設定（重複注意）

**機密情報（除外必須）**:
- `.env` / `.claude/settings.local.json` / `mcp-chatgpt-server/.env`

### PR作成ルール（BLOCKING REQUIREMENT）

PR bodyには必ず `Closes #XX` を記載する。
- PRマージ時にGitHubがISSUEを自動Close
- ガントチャートの `Target date` が自動セット

---

## 開発ワークフロー

```bash
# コード変更後
make test-all       # Python テスト
make lint           # コード品質チェック

# Git操作時
make pre-git-check  # セキュリティ + 安定性チェック
git add <files>     # 個別ファイル指定（推奨）
git commit
```

---

## テスト
`make test-all` でテスト実行（詳細は Makefile 参照）

---

## Skills

利用可能なSkillsは各Skillファイル（`.claude/skills/*/SKILL.md`）を参照。
主要Skills: `/fact-check` `/pre-commit` `/git-workflow` `/ccusage` `/investigate` `/create-pr` `/review`
追加予定: `/token-usage`

---

## CI自動監視（AgentTeams）

`git push`後、PostToolUse hookがCI監視を自動起動。特別な操作は不要。

動作フロー:
1. `git push` → hookがPR番号を取得しリクエストファイル作成
2. ci-monitorが30秒間隔でCIポーリング
3. CI失敗時 → PITFALLS.md検索 → 自動修正
4. 最大4回リトライ、解決不可の場合はSendMessageで報告

手動: `make ci-watch PR=<number>`

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
- [ ] **エラーを最小ケースで再現できるか？**
- [ ] **仮説を実験で検証したか？**

### Phase 3: 結論の検証
- [ ] 全ての証拠を説明できるか？
- [ ] 反証を最後にもう一度探したか？
- [ ] 再現可能な形で表現しているか？

---

## PITFALLS.md

エラーパターンDB。Skills（`/pre-commit`, `/git-workflow`）が自動検索。

- 手動検索: `grep "エラーメッセージ" .claude/PITFALLS.md`
- 新規エラー発見時: エラーID割り当て → 既存フォーマットに従い追加
- 詳細: `.claude/PITFALLS.md` の既存エントリを参照

---

## 参照
- [PITFALLS.md](.claude/PITFALLS.md) - エラーパターンデータベース
- [workflow-guide.md](.claude/docs/workflow-guide.md) - トークン効率改善ワークフロー
- [Token Analyzer設計](../docs/superpowers/specs/2026-04-04-token-analyzer-design.md) - 設計ドキュメント
