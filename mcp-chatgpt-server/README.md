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
export OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxxxxxxxxxx"
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
