# Gemini Code Assist Style Guide

このリポジトリ（claude-context-manager）のレビュー指針。

## 言語
- レビューコメントは**日本語**で記述してください。

## 重点チェック項目
- **セキュリティ**: 機密情報（APIキー等）のハードコード、`.env*` の誤コミット、コマンドインジェクション
- **Git安全性**: `git add .` / `--no-verify` / force push などの危険操作
- **Python品質**: PEP 8、型ヒント、`unittest` ベースのテスト
- **TypeScript品質**: `any` 禁止、Zod バリデーション
- **ドキュメント整合性**: CLAUDE.md / PITFALLS.md との矛盾

## ノイズ抑制
- typo/スタイルのみの nit は省略
- 既存コードと同等レベルの軽微指摘は省略
- `must` / `should` / `nit` の分類を明記

## 無視
- `.claude/worktrees/**` 配下（worktree 作業ディレクトリ）
