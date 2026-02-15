# Claude Context Manager - 要件定義書

**作成日**: 2026-02-11
**プロジェクト名**: Claude Context Manager
**バージョン**: v0.1.0
**ステータス**: 要件定義中

---

## 1. プロジェクト概要

### 1.1 プロジェクト名
**Claude Context Manager**（仮称）

### 1.2 概要
Claude CLI/Code利用時の対話履歴を完全保存し、コンテキスト管理・可視化を行うツール。自動compactによる履歴消失を防ぎ、Lost-in-the-middle問題を可視化・定量化する。

### 1.3 プロジェクトの目的
- Claude対話履歴を**compact前に完全保存**（ユーザー発言 + Claude返答）
- コンテキスト量（token数）を**リアルタイム可視化**
- Lost-in-the-middle問題の**定量化・警告**
- 対話履歴の**全文検索・Export**（Obsidian連携、Zenn記事化）

---

## 2. 要件定義

### 2.1 背景・課題

#### ペイン
1. **1セッションのtoken量がわからない**
   - Claude CLI/Codeは総token使用量は表示するが、1セッション単位の可視化がない
   - Lost-in-the-middle問題に直面してから気づく

2. **自動compactで履歴が失われる**
   - Claudeは一定のコンテキスト量を超えると自動的にcompactする
   - compact前の会話内容が失われる（要約のみ残る）
   - ユーザーの質問内容も消失

3. **対話履歴の保存が不完全**
   - 既存PR（#109）はClaude返答のみlog
   - ユーザー発言がlogされない
   - Web版はExport機能なし

4. **検索・再利用が困難**
   - 過去の対話を振り返れない
   - Zenn記事化、技術ノート作成に活用できない

### 2.2 ターゲットユーザー
- Claude CLI/Code ヘビーユーザー
- 技術ブログ執筆者（Zenn、Qiita、個人ブログ）
- 個人開発者、フルスタックエンジニア
- AI活用を記録・分析したい研究者

### 2.3 ユーザーストーリー

**As a** Claude CLI ユーザー
**I want to** 対話履歴をcompact前に完全保存したい
**So that** 過去の質問・回答を振り返り、再利用できる

**As a** 技術ブロガー
**I want to** Claude対話をMarkdown形式でExportしたい
**So that** Zenn記事化を効率化できる

**As a** 開発者
**I want to** コンテキスト量を可視化したい
**So that** Lost-in-the-middle問題を回避できる

---

## 3. 機能要件

### 3.1 Phase 1: CLI版（MVP）

#### 3.1.1 対話履歴の完全保存
- **ユーザー発言 + Claude返答**を両方保存
- **compact前の状態**を保存
- **Markdown形式**でGit管理（Obsidian互換）
- **画像・スクリーンショット**も含めて保存
- **タイムスタンプ**記録（YYYY-MM-DD HH:MM:SS）

#### 3.1.2 Token可視化
- **1セッションのtoken量をリアルタイム表示**
  - ユーザー発言token
  - Claude返答token
  - 累積token
- **Lost-in-the-middle警告**
  - しきい値設定（デフォルト: 50,000 tokens?）
  - 教師学習による自動調整（100回、1000回の対話データ）
- **コンテキスト量の定量化グラフ**
  - CLI上で簡易グラフ表示（ASCII art or 数値）

#### 3.1.3 Compactタイミング検出
- **Compact時間を記録**
  - セッションのどこでcompactされたか計測
- **Compact前後の差分表示**
  - compact前の内容を保存
  - compact後の要約内容を保存
  - 差分をMarkdownで出力

#### 3.1.4 検索・Export
- **過去の対話履歴を全文検索**
  - キーワード検索
  - 日付範囲指定
  - token量でフィルタ
- **Obsidian連携**
  - Markdown保存（双方向リンク対応）
  - デイリーノート形式で保存
- **Zenn記事化用のExport**
  - Zenn Markdown形式に変換
  - 画像パスの自動調整

#### 3.1.5 ログローテーション機能
- **自動削除機能**
  - デフォルト: **1ヶ月（30日）以上のログを自動削除**
  - 設定可能: 7日、14日、30日、90日、180日、365日、無期限
  - 削除前に確認プロンプト（オプション、デフォルト: OFF）
- **アーカイブ機能**
  - 削除前に圧縮アーカイブ（.tar.gz）
  - アーカイブ保存先: `~/.claude-context/archives/`
  - Phase 2: 外部ストレージ連携（S3、Google Drive等）
- **段階的削除**
  - **30日後**: 詳細ログ削除、サマリーのみ保持
  - **90日後**: サマリーも削除、統計のみ保持
  - **180日後**: 完全削除（統計も削除）
- **重要ログの保護**
  - タグ付けで保護（例: `#keep`, `#important`, `#archive`）
  - 保護されたログは自動削除されない
- **自動実行**
  - 毎日1回、バックグラウンドで実行（設定可能）
  - CLIコマンドで手動実行も可能

#### 3.1.6 CLI コマンド設計
```bash
# 対話履歴保存の開始
claude-context start

# 現在のtoken量を表示
claude-context status

# 対話履歴を検索
claude-context search "keyword"

# Obsidianに保存
claude-context export --format obsidian

# Zenn記事化
claude-context export --format zenn --output article.md

# 統計情報を表示
claude-context stats

# ログローテーション設定
claude-context config --rotate-days 30

# 手動ローテーション実行
claude-context rotate

# アーカイブ一覧表示
claude-context archive list

# アーカイブ復元
claude-context archive restore <archive-id>
```

### 3.2 Phase 2: Web Dashboard版

#### 3.2.1 Web UI
- **ChatGPT/Claude/Gemini風のUI**
  - タイムラインビュー
  - ユーザー発言 vs Claude返答の区別
  - 画像・スクリーンショット表示
- **検索UI**
  - フルテキスト検索
  - フィルタ機能（日付、token量）
- **統計ダッシュボード**
  - Token使用量グラフ
  - Compactタイミング可視化
  - セッション数、平均token数

#### 3.2.2 Export機能
- **複数形式対応**
  - Markdown（Obsidian互換）
  - Zenn Markdown
  - PDF
  - JSON

---

## 4. 技術スタック

### 4.1 言語・フレームワーク

#### バックエンド
- **言語**: TypeScript + Node.js
  - 理由: Web Dashboard展開が容易、Claude Code環境との親和性、エコシステム豊富
- **ランタイム**: Node.js 20.x 以上

#### フロントエンド（Phase 2）
- **フレームワーク**: React + Next.js
  - 理由: SSG/SSR対応、エコシステム豊富、UIテンプレート利用可能
- **スタイリング**: Tailwind CSS
- **UIコンポーネント**: shadcn/ui or Radix UI

### 4.2 ライブラリ

#### CLI
- **Commander.js** or **yargs**: CLIフレームワーク
- **chalk**: コンソール色付け
- **ora**: スピナー表示
- **cli-table3**: テーブル表示

#### Markdown処理
- **remark**: Markdown parser
- **rehype**: HTML処理
- **gray-matter**: Frontmatter処理

#### Token計測
- **tiktoken** (OpenAI) or **@anthropic-ai/tokenizer**: Token計測
  - Claudeの公式tokenizerがあれば優先

#### Git連携
- **simple-git**: Git操作
- **fs-extra**: ファイル操作

#### データ保存
- **SQLite** (Phase 2): 対話履歴のインデックス、検索用
- **JSON**: 設定ファイル

### 4.3 開発ツール
- **TypeScript**: 型安全性
- **ESLint**: Linter
- **Prettier**: Formatter
- **Jest**: テストフレームワーク
- **tsx**: TypeScript実行環境（開発時）

### 4.4 コーディング規約
- **Airbnb TypeScript Style Guide**準拠
- **関数型プログラミング**優先
- **Pure Function**を基本とする
- **副作用の分離**（I/O、API呼び出し）

### 4.5 テスト方針
- **単体テスト**: Jest
- **統合テスト**: 主要フロー（保存→検索→Export）
- **E2Eテスト**: Phase 2でWeb UIのテスト
- **カバレッジ目標**: 80%以上

---

## 5. アーキテクチャ

### 5.1 ディレクトリ構成

```
claude-context-manager/
├── src/
│   ├── cli/              # CLI関連
│   │   ├── commands/     # コマンド実装
│   │   ├── index.ts      # CLIエントリーポイント
│   ├── core/             # コアロジック
│   │   ├── logger.ts     # 対話履歴保存
│   │   ├── tokenizer.ts  # Token計測
│   │   ├── compactor.ts  # Compact検出
│   │   ├── exporter.ts   # Export処理
│   ├── storage/          # データ保存
│   │   ├── markdown.ts   # Markdown保存
│   │   ├── git.ts        # Git操作
│   │   ├── db.ts         # SQLite操作（Phase 2）
│   ├── web/              # Web Dashboard（Phase 2）
│   │   ├── app/          # Next.js app
│   │   ├── components/   # Reactコンポーネント
│   ├── types/            # 型定義
│   ├── utils/            # ユーティリティ
├── tests/                # テスト
├── docs/                 # ドキュメント
├── examples/             # サンプル
├── package.json
├── tsconfig.json
└── README.md
```

### 5.2 データフロー

```
Claude CLI/Code
    ↓
Claude Code Hook（user-prompt-submit, tool-result）
    ↓
Claude Context Manager
    ↓ (保存)
Git Repository（Markdown形式）
    ↓ (連携)
Obsidian Vault
```

### 5.3 Claude Code Hook統合

Claude Codeの`.claude/hooks/`を利用：
- `user-prompt-submit-hook`: ユーザー発言をキャプチャ
- `tool-result-hook`: Claude返答をキャプチャ
- カスタムhookで対話履歴を保存

### 5.4 Markdown保存形式

```markdown
---
date: 2026-02-11
session_id: abc123
total_tokens: 1234
user_tokens: 500
assistant_tokens: 734
tags: [claude, development, rust]
---

# Claude対話履歴 - 2026-02-11

## 20:00:00 - ユーザー

Rustの非同期処理について教えてください。

**Tokens**: 15

## 20:00:05 - Claude

Rustの非同期処理は...

**Tokens**: 500

---

**セッション統計**:
- 総Token数: 1234
- ユーザーToken: 500
- ClaudeToken: 734
- Compact: なし
```

### 5.5 データライフサイクル管理

#### 5.5.1 ログローテーション戦略

**目的**: 年間運用で数GB以上になるログを管理し、Git Repository肥大化を防ぐ

**ライフサイクル**:
```
作成 → 保持（30日） → サマリー化（30-90日） → 統計のみ（90-180日） → 削除/アーカイブ（180日以降）
```

**実装方針**:
1. **日次バッチ処理**
   - cron or タスクスケジューラーで毎日実行
   - 対象ファイルをスキャン
   - 保持期間を超えたログを処理

2. **ストレージ容量見積もり**
   - 1日の対話数: 平均10セッション
   - 1セッション: 平均50KB（Markdown + 画像込み）
   - 1日のログ: 500KB
   - 1ヶ月: 15MB
   - 1年（ローテーション前）: 180MB
   - 1年（ローテーション後）: 約50MB（サマリー + 統計）

3. **段階的削除の詳細**
   - **0-30日**: 完全保存（詳細ログ + 画像）
   - **30-90日**: サマリーのみ（画像削除、主要な質問・回答のみ保持）
   - **90-180日**: 統計のみ（Token数、セッション時間、タグ）
   - **180日以降**: アーカイブ or 完全削除

4. **サマリー生成**
   - セッションのタイトル
   - 主要なトピック（タグ）
   - Token統計
   - 重要な質問・回答（ユーザーが`#important`タグ付け）

#### 5.5.2 アーカイブ形式

**アーカイブファイル名**: `claude-context-{YYYY-MM}.tar.gz`

**内容**:
- Markdown形式の対話履歴
- 画像ファイル
- メタデータ（JSON）

**保存先**:
- ローカル: `~/.claude-context/archives/`
- Phase 2: クラウドストレージ（S3、Google Drive等）

---

## 6. 将来性

[[PRINCIPAL.md]]に記載

## 7. 法的根拠

[[PRINCIPAL.md]]に記載

---

## 8. 類似プロダクト

### 8.1 既存ツール
- **ChatGPT Export Tools**: ChatGPT会話のExportツール（Chrome拡張など）
- **LangChain**: 会話履歴管理機能（大規模すぎる）
- **LlamaIndex**: データインデックス・管理

### 8.2 参考にできる点
- **ChatGPT Export Tools**: UIデザイン、Export形式
- **Obsidian Git Plugin**: Git自動同期の実装
- **tiktoken**: Token計測ロジック

---

## 9. ロードマップ

### Phase 1: CLI版（MVP） - 2-3ヶ月
- **Week 1-2**: 基盤実装
  - プロジェクトセットアップ
  - Claude Code Hook統合
  - 対話履歴保存（Markdown形式）
- **Week 3-4**: Token可視化
  - Tokenizer実装
  - リアルタイム表示
- **Week 5-6**: Export機能
  - Obsidian連携
  - Zenn記事化
- **Week 7-8**: テスト、ドキュメント、リリース

### Phase 2: Web Dashboard版 - 3-4ヶ月
- **Month 1**: Web UI基盤
  - Next.js セットアップ
  - 対話履歴表示UI
- **Month 2**: 検索・分析機能
  - 全文検索
  - 統計ダッシュボード
- **Month 3**: Export、最適化
  - 複数形式Export
  - パフォーマンス改善
- **Month 4**: テスト、リリース

---

## 10. 懸念点

### 10.1 技術的懸念
1. **Claude API変更リスク**
   - Anthropicが仕様変更した場合の対応
   - 対策: APIバージョン固定、変更監視

2. **Compactアルゴリズム推測の難しさ**
   - Claudeのcompactアルゴリズムは非公開
   - 対策: 経験則、教師学習による推測

3. **Token計測の精度**
   - Claude専用tokenizerがない場合、tiktoken（OpenAI）で代用
   - 対策: 公式tokenizerが出たら切り替え

### 10.2 運用的懸念
1. **Git Repository肥大化**
   - 対話履歴が増えるとGitリポジトリが巨大化
   - 対策: **ログローテーション機能**（デフォルト30日）、定期的なアーカイブ、Git LFS利用

2. **画像保存の容量問題**
   - スクリーンショットが多いと容量圧迫
   - 対策: 画像圧縮、外部ストレージ連携（Phase 2）、**30日後の自動削除**

3. **ローテーション設定の難しさ**
   - ユーザーにとって最適な保持期間は異なる
   - 対策: デフォルト30日、設定変更可能、`#keep`タグで保護機能

4. **アーカイブの管理コスト**
   - アーカイブが増えるとストレージコスト増加
   - 対策: Phase 1はローカルのみ、Phase 2でクラウドストレージ連携（有料版）

---

## 11. 決定事項

| 項目 | 決定内容 | 決定日 |
|------|---------|--------|
| プロジェクト名 | Claude Context Manager（仮称） | 2026-02-11 |
| 技術スタック | TypeScript + Node.js | 2026-02-11 |
| Phase 1目標 | CLI版（対話履歴保存、Token可視化、Export、ログローテーション） | 2026-02-11 |
| Phase 2目標 | Web Dashboard版 | 2026-02-11 |
| 保存形式 | Markdown + Git | 2026-02-11 |
| ログローテーション | デフォルト30日、設定可能（7/14/30/90/180/365日/無期限） | 2026-02-11 |
| アーカイブ形式 | .tar.gz形式、ローカル保存（~/.claude-context/archives/） | 2026-02-11 |

---

## 12. 未決定事項

| 項目 | 状態 | 次のアクション |
|------|------|--------------|
| Claude専用tokenizerの有無 | 調査中 | Anthropic公式ドキュメント確認 |
| Compactしきい値の初期値 | 未定 | 実験的に決定 |
| Web Dashboard UIテンプレート | 未選定 | 既存UIライブラリ調査 |

---

**更新履歴**:
- 2026-02-11 23:00: ログローテーション機能追加（デフォルト30日、段階的削除、アーカイブ機能）
- 2026-02-11 22:30: 初版作成
