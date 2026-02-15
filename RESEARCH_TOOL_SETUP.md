# Web調査ツール セットアップガイド（claude-context-managerプロジェクト用）

このプロジェクトでClaude CodeのWeb調査ツール（`/research`コマンド）を使用するためのセットアップガイドです。

**✨ 新機能**: ChatGPT と Gemini の両方に対応！`--model` オプションでモデルを選択できます。

---

## 🚀 クイックスタート

### 1. 依存関係のインストール

```bash
cd /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server
npm install
```

### 2. 環境変数の設定

```bash
cd /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server
cp .env.example .env
```

`.env`ファイルを編集してAPIキーを設定：

```bash
# .env

# OpenAI (ChatGPT) - 少なくとも1つのAPIキーが必要
OPENAI_API_KEY=your-openai-api-key-here

# Gemini - オプション（Geminiを使う場合は設定）
GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxx

# デフォルト設定（オプション）
DEFAULT_MODEL=openai  # または gemini
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.0-flash-exp
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000
```

**重要**: 少なくとも `OPENAI_API_KEY` または `GEMINI_API_KEY` の1つが必要です。

### 3. ビルド

```bash
cd /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server
npm run build
```

### 4. Claude Codeを再起動

Claude Codeを再起動して、新しいSKILLを認識させます。

### 5. 使ってみる

**基本的な使い方**:
```
/research TypeScriptのジェネリクスについて
```

**Geminiを使う**:
```
/research 量子コンピュータの市場規模 --model gemini
```

**Gemini + Google検索（Grounding）**:
```
/research 2026年のAIトレンド --model gemini --grounding
```

---

## 📁 プロジェクト構成

```
/Users/harieshokunin/claude-context-manager/
│
├── mcp-chatgpt-server/              # コピーされたMCPサーバー
│   ├── src/                         # TypeScriptソースコード
│   │   ├── tools/
│   │   │   ├── web-research.ts
│   │   │   └── types.ts
│   │   ├── formatters/
│   │   │   └── markdown-formatter.ts
│   │   ├── utils/
│   │   │   └── file-manager.ts
│   │   └── cli/
│   │       └── research.ts
│   │
│   ├── build/                       # ビルド後（npm run build後に生成）
│   │   └── cli/
│   │       └── research.js          # これが実行される
│   │
│   ├── node_modules/                # npm install後に生成
│   ├── package.json
│   ├── tsconfig.json
│   ├── .env                         # 自分で作成（APIキー設定）
│   └── .env.example
│
├── .claude/
│   └── commands/
│       └── research.md              # SKILL定義（パス修正済み）
│
└── RESEARCH_TOOL_SETUP.md           # このファイル

~/.claude/research/                   # 調査結果保存先（全プロジェクト共通）
└── YYYY-MM-DD_topic-name.md
```

---

## ⚙️ 必要な環境変数

### OPENAI_API_KEY（少なくとも1つ必要）

OpenAI APIキーを取得：
1. [OpenAI Platform](https://platform.openai.com/api-keys)にアクセス
2. 「Create new secret key」でキーを生成
3. `sk-proj-` で始まるキーをコピー
4. `.env`ファイルに貼り付け

### GEMINI_API_KEY（オプション、Gemini使用時は必須）

Gemini APIキーを取得：
1. [Google AI Studio](https://aistudio.google.com/app/apikey)にアクセス
2. 「Create API key」でキーを生成
3. キーをコピー
4. `.env`ファイルに貼り付け

### その他（オプション）

| 環境変数 | デフォルト | 説明 |
|---------|-----------|------|
| `DEFAULT_MODEL` | `openai` | デフォルトのプロバイダー (openai/gemini) |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI使用時のモデル |
| `GEMINI_MODEL` | `gemini-2.0-flash-exp` | Gemini使用時のモデル |
| `OPENAI_TEMPERATURE` | `0.7` | ランダム性（0-2） |
| `OPENAI_MAX_TOKENS` | `2000` | 最大トークン数 |

---

## 🔧 トラブルシューティング

### エラー: "Cannot find module"

**原因**: 依存関係がインストールされていない

**解決策**:
```bash
cd /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server
npm install
```

### エラー: "OPENAI_API_KEY not set" または "GEMINI_API_KEY not set"

**原因**: 環境変数が設定されていない

**解決策**:
```bash
cd /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server
cp .env.example .env
# .envファイルを編集してAPIキーを設定
# OpenAI使用時: OPENAI_API_KEY=sk-proj-...
# Gemini使用時: GEMINI_API_KEY=...
```

### エラー: "research.js not found"

**原因**: プロジェクトがビルドされていない

**解決策**:
```bash
cd /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server
npm run build
```

### エラー: "/research command not found"

**原因**: SKILL定義が認識されていない

**解決策**:
1. ファイルが存在するか確認:
   ```bash
   ls -la /Users/harieshokunin/claude-context-manager/.claude/commands/research.md
   ```
2. Claude Codeを再起動

---

## 📊 使用例

### 基本的な使い方（ChatGPT）

```
/research TypeScriptのジェネリクスについて
```

### Geminiを使う

```
/research 量子コンピュータの市場規模 --model gemini
```

### Gemini + Google検索（Grounding）

```
/research 2026年のAIトレンド --model gemini --grounding
```

### 並行実行（マルチエージェント）

```bash
# Claude自身とChatGPT、Geminiで同時に調査
# Task(Explore)は自動で並行実行される
/research "React 19の新機能" --model openai &
/research "React 19の新機能" --model gemini --grounding &
wait
```

### 実行結果

```
🔍 Researching: TypeScriptのジェネリクスについて

✅ Research complete!

📊 Tokens used: 1245
🔗 Sources found: 5
📁 Saved to: /Users/harieshokunin/.claude/research/2026-02-11_typescript.md

---

# 調査結果: TypeScriptのジェネリクスについて

## メタ情報
- 調査日時: 2026-02-11 16:55:00
- 調査ツール: ChatGPT (gpt-4o)
- トークン使用: 1245 tokens

## 主要な発見
...
```

### 調査結果の確認

```bash
# 最新の調査結果を表示
ls -lt ~/.claude/research/ | head -5

# 特定のトピックを検索
grep -r "TypeScript" ~/.claude/research/
```

---

## 🔄 更新手順

元のwater_misleadプロジェクトで機能追加があった場合：

```bash
# 1. 最新版をコピー
cp -r /Users/harieshokunin/water_mislead/mcp-chatgpt-server /Users/harieshokunin/claude-context-manager/

# 2. .envを再設定（APIキーが消えるため）
cd /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server
cp .env.example .env
# .envファイルを編集

# 3. 再インストールとビルド
npm install
npm run build

# 4. research.mdのパスを確認
# 必要に応じて修正（/Users/harieshokunin/claude-context-manager/...に修正）
```

---

## 📝 カスタマイズ

このプロジェクト専用のカスタマイズが可能です。

### モデルを変更

`.env`ファイルで：
```bash
# OpenAI モデル
OPENAI_MODEL=gpt-4o-mini  # コスト削減
OPENAI_MODEL=gpt-4o       # 標準
OPENAI_MODEL=o1-preview   # 高品質

# Gemini モデル
GEMINI_MODEL=gemini-2.0-flash-exp      # 標準（推奨）
GEMINI_MODEL=gemini-1.5-pro-latest     # 高品質
```

### 出力形式をカスタマイズ

`mcp-chatgpt-server/src/formatters/markdown-formatter.ts`を編集後：
```bash
npm run build
```

---

## 💰 コスト試算

### ChatGPT (gpt-4o)
- 1回の調査: 約2.5円
- 月100回: 約250円
- 月1000回: 約2500円

### Gemini (gemini-2.0-flash-exp)
- 1回の調査: 約0.1円（無料枠あり）
- 月100回: 約10円
- 月1000回: 約100円

### Gemini + Grounding
- 1回の調査: 約1円
- 月100回: 約100円
- 月1000回: 約1000円

**注意**: レート制限に注意してください。制限に達した場合は、Claude WebSearchを代替として使用できます。

---

## 🆘 サポート

問題が発生した場合は、以下をチェック：

1. ✅ `.env`ファイルにAPIキーが設定されているか
2. ✅ `npm install`と`npm run build`を実行したか
3. ✅ `build/cli/research.js`ファイルが存在するか
4. ✅ Claude Codeを再起動したか

詳細なガイドは`/Users/harieshokunin/water_mislead/RESEARCH_TOOL_GUIDE.md`を参照してください。

---

## ✅ セットアップ完了チェックリスト

- [ ] `npm install`を実行した
- [ ] `.env`ファイルを作成した
- [ ] `OPENAI_API_KEY` または `GEMINI_API_KEY` を設定した
- [ ] `npm run build`を実行した
- [ ] `build/cli/research.js`が存在する
- [ ] `.claude/commands/research.md`が存在する
- [ ] Claude Codeを再起動した
- [ ] `/research テスト`で動作確認した（ChatGPT）
- [ ] `/research テスト --model gemini`で動作確認した（Gemini - オプション）

すべてチェックが入れば、準備完了です！🎉

---

## 🎯 次のステップ

1. **GEMINI_API_KEYを設定**（まだの場合）
   - [Google AI Studio](https://aistudio.google.com/app/apikey)でキーを取得
   - `.env`に追加して`npm run build`

2. **マルチエージェント調査を試す**
   ```
   # Claude WebSearch + ChatGPT + Gemini で並行調査
   /research "最新のReact技術" --model openai
   /research "最新のReact技術" --model gemini --grounding
   ```

3. **CLAUDE.mdの調査憲法を確認**
   - `~/.claude/CLAUDE.md` に調査アプローチが記載されています
