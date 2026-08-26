# claude-context-manager レビュー観点（Bugbot）

Claude のコンテキスト・セッション資産を管理するツール群。Python と TypeScript が混在する。
既存の `.gemini/styleguide.md` の方針を土台に、Bugbot 向けに整理したもの。

## 出力ルール

- コメントは**日本語**で書く。
- 各指摘に **`must` / `should` / `nit`** を明記する。`must` はマージをブロックする欠陥に限る。
- typo・整形のみの nit は省略する。既存コードと同等レベルの軽微な指摘も省略する。
- `.claude/worktrees/**` は作業用 worktree なのでレビュー対象外。

## must として扱う観点

### 1. 機密
API キー・トークンのハードコード、`.env*` の誤コミット、
ログ・エラーメッセージ・生成物への機密の混入。

### 2. コマンドインジェクション
外部入力を shell へ渡す経路（`subprocess` の `shell=True`、文字列連結でのコマンド組み立て、
`eval` / `exec`）。ファイル名・セッション ID など、ユーザー由来の値が混ざる箇所を特に見る。

### 3. Git の危険操作
`git add .`、`--no-verify`、force push、`reset --hard` を実行するスクリプト。
共有チェックアウトや他リポの HEAD を動かす操作。

### 4. サイレントフォールバック
`except Exception: pass`、`catch {}`、API エラーをデフォルト値に潰す。
失敗は必ずログに出して伝播させる。

### 5. セッション資産の破壊
既存のセッションファイル・コンテキストを上書き / 削除する経路。
冪等でない書き込み、書き込み前のバックアップ欠落。

## should として扱う観点

- **Python**: PEP 8、型ヒント、`unittest` ベースのテスト、broad except の絞り込み
- **TypeScript**: `any` 禁止、Zod による外部入力のバリデーション
- **ドキュメント整合性**: `CLAUDE.md` / `PITFALLS.md` と実装が矛盾していないか
- 新規ロジックにテストが無い
