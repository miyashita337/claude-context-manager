# ADR-001: SpecStory 非採用決定

- **Status**: Accepted
- **Date**: 2026-04-15
- **Related**: Issue #2, PR #5, `.claude/research/specstory-investigation.md`

## 背景

Issue #2（2026-02-21 Close）で SpecStory の導入可否を検証し、PR #5 で検証成果物をマージしたが、本体パイプラインへの統合可否は未決のまま `.specstory/history/*.md`（1ファイル・1.4MB）だけが残存していた。却下を明示したドキュメントも存在せず、採用/非採用が曖昧な状態が約2ヶ月継続。

## 決定

**SpecStory を claude-context-manager の本体パイプラインに採用しない。**

既存の Token Analyzer（JSONL 直読）路線を正とし、将来の「匿名化共有」「注意横取り検知レポート」も自作 exporter で対応する。

## 根拠

### 1. データソースの一次性
- `~/.claude/projects/**/*.jsonl`（91プロジェクト / 1,425セッション / 931MB）は Claude Code 公式が書き出す**一次ソース**。
- SpecStory はこの JSONL を Markdown に変換する派生物であり、`input/output/cache_creation/cache_read` の分離情報が `total_tokens` に丸められる等、情報量が減る。
- 集計（Token Analyzer）・ブロッキング（hooks）・パターン検出のホットパスでは**一次ソース直読が必須**。

### 2. ブロッキング用途への不適合
- SpecStory は `sync`/`watch` による**事後バッチ変換**モデル。
- `user-prompt-submit.py` の P0/P1/P2 パイプラインはプロンプト送信の**同期経路**で動く必要があり、Markdown 化待ちは成立しない。
- キッチンシンク/話題逸脱/注意横取りの**事前ブロッキング**という本プロジェクトの中核要件と構造的に合わない。

### 3. 91プロジェクト運用コスト
- SpecStory は「プロジェクトごとに `specstory sync`」設計。グローバル1コマンドで全プロジェクトを一括処理する公式機能は無い。
- `.specstory/history/*.md` が各プロジェクトに分散 → `.gitignore` 漏れで機密会話が git commit される事故リスク（RW-005 類似）。

### 4. 自作 exporter の優位
- 既存 Token Analyzer（`src/analyzer/jsonl_parser.py`）に `--export-md` 拡張を加える規模（MVP 2-3人日）で賄える。
- 構造化マスキング（`tool_use.input` のパスのみ redact、`message.content[].text` の PII 検出等）を**フィールド単位で制御**可能。
- Markdown 正規表現頼みの誤爆リスクを排除できる。

#### 既存 TypeScript 側 Markdown Writer との役割分担
`src/core/markdown-writer.ts`（`MarkdownWriter` クラス）は既に存在するが、**用途が異なる**ため重複ではない：

| レイヤー | 既存 TS (`src/core/markdown-writer.ts`) | 新規 Python (`src/exporters/` 予定) |
|---|---|---|
| 用途 | **リアルタイム** セッションログ → Obsidian 互換 Markdown | **バッチ** JSONL → 匿名化済み共有用 Markdown |
| データソース | SessionLogger 経由の LogEntry（`src/types/session.ts`） | `~/.claude/projects/**/*.jsonl`（Claude Code 公式） |
| 呼び出し元 | `src/cli/finalize-session.ts`（セッション終了時） | Token Analyzer CLI / 注意横取り検知レポーター |
| 匿名化 | なし（個人利用前提） | 必須（他者共有前提） |
| tokens_estimate | 推定値（`tokens_estimate`） | JSONL `usage` の正確値 |

将来的に共通処理（Markdown ヘッダ生成、frontmatter 整形等）を抽出する余地はあるが、Phase 1 では別モジュールとして独立実装し、Phase 2 以降で共通化を検討する。

### 5. マルチエージェント対応（反証への応答）
- Skeptic 論拠「SpecStory は Codex/Cursor/Gemini にも対応」は弱い：
  - Gemini Code Assist PoC (#137) がマージ済みで本プロジェクトも multi-agent 化の兆候あり。
  - ただし他エージェントの transcript 仕様を自作 parser が吸収するコストは限定的（各エージェントの出力形式は基本的にJSONベース）。
  - SpecStory の抽象層に乗るより、プロジェクト側で schema 正規化層を持つ方が中長期のメンテ性が高い。

## 代替アーキテクチャ

```text
[Hot path — ブロッキング]
  UserPromptSubmit hook → JSONL tail read
  → topic-server（埋め込み）→ Haiku判定 → block/warn

[Warm path — 集計/検索]
  ~/.claude/projects/**/*.jsonl
  → DuckDB (CREATE TABLE AS read_json_auto)
  → ripgrep で全文検索
  → Token Analyzer（既存）

[Cold path — 共有/指摘レポート]
  自作 exporter: JSONL → 匿名化 → Markdown
  ├ 構造化マスキング（フィールド別ポリシー）
  ├ 注意横取り箇所の注釈付与（該当 Epic で実装）
  └ Issue 貼り付け用スニペット生成
```

## 影響範囲

### 削除
- `.specstory/.project.json`
- `.specstory/history/2026-02-16_07-19-30Z-*.md`（1.4MB 検証サンプル）
- `spec_story/package.json`（空の npm 雛形）
- `.specstory/`, `spec_story/` ディレクトリ

### 残置
- `.claude/research/specstory-investigation.md`（判断根拠の一次資料として保全）
- グローバル `npm i -g specstory`（別プロジェクトで使う可能性があるため撤去しない）
- `.gitignore` の `.specstory/`, `spec_story/` エントリ（再発防止として残置）

## フォローアップ

- 注意横取り検知 Epic を起票し、自作 exporter の仕様を逆算。
- Issue #2 にクローズコメントとして本 ADR を参照する経緯を追記。
