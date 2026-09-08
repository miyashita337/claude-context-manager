# MCP ChatGPT Server

Claude CodeからChatGPT APIを呼び出すためのMCPサーバー

## セットアップ

### 1. 依存関係のインストール

```bash
cd mcp-chatgpt-server
npm install
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集してOPENAI_API_KEYを設定
```

または、システム環境変数として設定:

```bash
# ~/.zshrc or ~/.bash_profile
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 3. ビルド

```bash
npm run build
```

### 4. Claude Codeでの設定

プロジェクトルートの`.mcp.json`に設定が記載されています。
環境変数`OPENAI_API_KEY`を設定してください。

## 使い方

Claude Codeから以下のように使用できます:

```
ChatGPTに「Rustの所有権について説明して」と質問して
```

## 提供機能

### chatgptツール

ChatGPTに質問を送信して回答を取得

**パラメータ:**
- `prompt` (必須): 質問内容
- `model` (オプション): 使用モデル (デフォルト: gpt-4o)
  - 選択肢: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
- `temperature` (オプション): ランダム性 (0-2, デフォルト: 0.7)
- `max_tokens` (オプション): 最大トークン数 (デフォルト: 2000)

**レスポンス:**
- ChatGPTの回答テキスト
- 使用モデル名
- トークン使用量 (prompt/completion/total)

### generate-diagramツール（OpenAI Images）

OpenAI Images API（`gpt-image-1`）で概念図やドキュメント用画像を生成。フローチャートやアーキテクチャ図にはMermaidを使用してください。

**必要な環境変数:**
- `OPENAI_API_KEY` (必須): OpenAI APIキー
- `OPENAI_IMAGE_MODEL` (オプション): 使用モデル (デフォルト: `gpt-image-1`)
- `OPENAI_IMAGE_SIZE` / `OPENAI_IMAGE_QUALITY` / `OPENAI_IMAGE_FORMAT` (オプション): 各引数の既定値

**パラメータ:**
- `prompt` (必須): 生成したい画像の説明
- `filename` (オプション): 出力ファイル名（省略時は自動生成）
- `output_dir` (オプション): 保存先ディレクトリ（デフォルト: `docs/images/`）
- `size` (オプション): 画像サイズ（デフォルト: `1536x1024`）
  - 選択肢: `auto`, `1024x1024`, `1536x1024`, `1024x1536`
- `quality` (オプション): レンダリング品質（デフォルト: `medium`）
  - 選択肢: `auto`, `low`, `medium`, `high`
- `output_format` (オプション): ファイル形式（デフォルト: `png`）
  - 選択肢: `png`, `jpeg`, `webp`

**使用例:**
```
概念図を生成して：「マイクロサービス間のイベント駆動通信パターン」
```

**Gemini からの移行（2026-09）:**

画像生成のバックエンドを Nano Banana（Gemini）から OpenAI Images API に置き換えました。`gpt-image-1` には旧
`aspect_ratio`（5種）/ `resolution`（4段階）に相当する値が存在しないため、引数は OpenAI ネイティブの
`size` / `quality` / `output_format` に置き換えています（黙って近似せず、旧値はスキーマで弾きます）。
許容値の出典は `node_modules/openai/resources/images.d.ts:62, 242-287`。

なお `/research` CLI は `--model gemini` を引き続きサポートするため、`GEMINI_API_KEY` と
`@google/generative-ai` 依存は残しています（画像生成専用だった `@google/genai` のみ除去）。

## テスト方法

### MCP Inspectorでテスト

```bash
npx @modelcontextprotocol/inspector node build/index.js
```

ブラウザでGUIからツールをテスト可能です。

### Claude Codeでテスト

1. Claude Codeを再起動
2. 「ChatGPTに『TypeScriptのジェネリクスを簡潔に説明して』と聞いて」と質問
3. ChatGPTの回答が返されることを確認

## 開発

### ビルドスクリプト

- `npm run build`: TypeScriptをビルド
- `npm run watch`: ファイル変更を監視して自動ビルド
- `npm run dev`: ビルド後にサーバーを起動
- `npm start`: ビルド済みサーバーを起動
- `npm test`: ユニットテスト実行（vitest）

## トラブルシューティング

### APIキーエラー

```
Error: OPENAI_API_KEY environment variable is required
```

→ `.env`ファイルまたはシステム環境変数に`OPENAI_API_KEY`を設定してください。

### MCPサーバーが見つからない

Claude Codeを再起動してください。設定変更は再起動後に反映されます。

## ライセンス

MIT
