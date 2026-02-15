# Git操作チェックリスト（日常業務用）

**目的**: 日常のGit操作時に最小限のチェックを実行

---

## セッション開始時
- [ ] `make startup-check`

---

## Git操作前（毎回）
- [ ] `make pre-git-check`
- [ ] `git status`で変更内容確認

---

## コミット時
- [ ] `git add <specific-files>`（個別指定推奨）
- [ ] コミットメッセージは明確か？

---

## プッシュ前（重要）
- [ ] publicリポジトリの場合、機密情報なし？
- [ ] ユーザー確認済み？

---

## エラー時
- [ ] 同じエラー3回 → 処理停止
- [ ] 状況整理 → Web検索 → ユーザー確認

---

**コマンドクイックリファレンス**:
```bash
make pre-git-check  # 事前チェック
make git-clean      # 不要ファイル削除
make git-safe-push  # 安全なプッシュ
```
