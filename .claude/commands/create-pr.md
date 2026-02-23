# /create-pr <ISSUE_NUMBER>

引数: `/create-pr <N>`（例: `/create-pr 42`）

> **通常は `/investigate <N>` の Step 6 から自動的に呼ばれる。**
> 単体で呼ぶことも可能（調査済みの場合）。

---

## 実行手順

### Step 1: 事前確認

```bash
# 1. 作業ブランチが clean か確認
git status

# 2. Issue の最新情報を取得（実装内容の最終確認）
gh issue view $ARGUMENTS --repo miyashita337/claude-context-manager \
  --json number,title,body,labels
```

---

### Step 2: ブランチ作成

Issue タイトルをもとにブランチ名を決定し、main から分岐する:

```bash
# ブランチ命名規則: fix/issue-{N}-{短い説明}
# 例: fix/issue-42-modal-display-bug
git checkout main
git pull origin main
git checkout -b fix/issue-$ARGUMENTS-{short-description}
```

命名ルール:
- バグ修正: `fix/issue-{N}-{description}`
- 機能追加: `feat/issue-{N}-{description}`
- ドキュメント: `docs/issue-{N}-{description}`

---

### Step 3: 実装

`/investigate` の調査レポートを参照し、「変更が必要なファイル（推定）」と「推奨アクション」に基づいて実装する。

実装方針:
- 最小限の変更に留める（YAGNI / KISS）
- 関係ないコードのリファクタリングは行わない
- コメント・型アノテーションは変更箇所のみ

---

### Step 4: テスト実行

```bash
make test-all 2>&1
```

テスト結果の判定:
- ✅ 全 pass → Step 5 へ進む
- ❌ fail あり → 実装を修正して再実行（Step 3 に戻る）

---

### Step 5: ブラウザ・UI 系バグの After 検証（該当する場合のみ）

Issue がブラウザ表示に関わる場合のみ実行する。
**サーバーは起動済みを前提とする。**

#### 5-A: 修正後スクリーンショット検証ループ

以下のループを最大 **5回** 繰り返す:

```
[試行 {n}/5]

① Issue に記載された再現手順で対象画面に遷移する

② /ss でスクリーンショットを取得する

③ バグが解消されているか判定する:

   ✅ 解消を確認 → ループを抜けて Step 6 へ進む

   ❌ まだ再現する / 想定と異なる場合:
      - 何が期待と違うかを具体的に記述する
      - 原因を特定して実装を修正する（Step 3 に戻る）
      - 試行回数をインクリメントして次のループへ
```

#### 5-B: 5回試行しても解消しない場合

ループを抜けてユーザーに以下の形式で報告し、**処理を停止する**:

```
⚠️ Issue #$ARGUMENTS の修正検証が 5回試行後も解決しませんでした。

## 試行履歴
| 試行 | 変更内容 | スクリーンショット確認結果 |
|------|---------|--------------------------|
| 1/5  | {変更内容} | {何が期待と違ったか} |
| 2/5  | {変更内容} | {何が期待と違ったか} |
| 3/5  | {変更内容} | {何が期待と違ったか} |
| 4/5  | {変更内容} | {何が期待と違ったか} |
| 5/5  | {変更内容} | {何が期待と違ったか} |

## 現在の状態
{最新スクリーンショットで確認できる状態を記述}

## 考えられる原因
1. {仮説1}
2. {仮説2}

## 次のアクションの提案
- [ ] {提案1}
- [ ] {提案2}

指示をお願いします。
```

---

### Step 6: コミット

```bash
# 変更ファイルを個別に stage（git add . は使わない）
git add {file1} {file2} ...

# コミットメッセージ（末尾に Closes #N は必須）
git commit -m "$(cat <<'EOF'
fix: {Issue タイトルを簡潔に言い換えた説明}

{変更内容の補足（任意、1-3行）}

Closes #$ARGUMENTS
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Step 7: Push & PR 作成

```bash
git push -u origin fix/issue-$ARGUMENTS-{short-description}
```

PR を作成する:

```bash
gh pr create \
  --repo miyashita337/claude-context-manager \
  --title "fix: {Issue タイトルを簡潔に言い換えた説明}" \
  --body "$(cat <<'EOF'
## Summary

- {変更内容を箇条書き 1-3点}

## Test plan

- [ ] `make test-all` 全 pass 確認
- [ ] {ブラウザ確認が必要な場合: スクリーンショットで修正を確認}

## Screenshots（UI 変更がある場合）

**Before:**
{/investigate Step 2.5 で撮影したスクリーンショットの説明}

**After:**
{Step 5 で撮影したスクリーンショットの説明}

Closes #$ARGUMENTS

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

### Step 8: 完了報告

ユーザーに以下を表示する:

```
✅ PR 作成完了

Issue  : #$ARGUMENTS
Branch : fix/issue-$ARGUMENTS-{short-description}
PR URL : {gh pr create の出力 URL}

次のステップ:
- CI が通ったことを確認してください
- レビュー後にマージすると Issue が自動 Close されます
```
