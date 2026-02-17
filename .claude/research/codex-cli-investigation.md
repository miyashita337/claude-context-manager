# Codex CLI 調査レポート

**調査日**: 2026-02-16
**担当タスク**: Task #2 - Phase 1: Codex CLI調査

---

## 📦 インストール情報

### Codex CLI
- **パッケージ名**: `@openai/codex`
- **インストールコマンド**: `npm install -g @openai/codex`
- **バージョン**: 0.101.0（2026-02-12リリース）
- **コマンド名**: `codex`

### ccusage
- **パッケージ名**: `@ccusage/codex`
- **インストールコマンド**: `npm install -g @ccusage/codex`
- **バージョン**: 18.0.5（2026-01-09リリース）
- **コマンド名**: `ccusage-codex`（**注意**: `ccusage`ではない）

---

## 🔧 Codex CLI 機能

### 主要コマンド

```bash
# インタラクティブモード（デフォルト）
codex [PROMPT]

# 非インタラクティブ実行
codex exec [PROMPT]

# コードレビュー
codex review

# ログイン管理
codex login
codex logout

# セッション管理
codex resume    # 過去のセッションを再開
codex fork      # 過去のセッションをフォーク
codex apply     # 最新のdiffをgit applyとして適用

# MCP統合（実験的）
codex mcp
codex mcp-server

# その他
codex app       # デスクトップアプリ起動
codex sandbox   # サンドボックス実行
codex debug     # デバッグツール
codex features  # 機能フラグ確認
```

### 重要なオプション

#### モデル選択
```bash
-m, --model <MODEL>         # 使用するモデルを指定
--oss                       # ローカルOSSモデルを使用（LM Studio/Ollama）
--local-provider <PROVIDER> # ローカルプロバイダー指定（lmstudio/ollama）
```

#### 実行ポリシー
```bash
-s, --sandbox <MODE>        # サンドボックスポリシー
                            # read-only: 読み取り専用
                            # workspace-write: ワークスペース書き込み可
                            # danger-full-access: フルアクセス（危険）

-a, --ask-for-approval <POLICY>  # 承認ポリシー
                                 # untrusted: 信頼されたコマンドのみ自動実行
                                 # on-failure: 失敗時のみ確認
                                 # on-request: モデルが判断
                                 # never: 確認なし

--full-auto                 # 低摩擦サンドボックス自動実行
                            # (-a on-request --sandbox workspace-write)

--dangerously-bypass-approvals-and-sandbox  # 全確認をスキップ（極めて危険）
```

#### その他
```bash
-i, --image <FILE>...       # 画像添付
-C, --cd <DIR>              # 作業ディレクトリ指定
--search                    # ライブWeb検索有効化
-c, --config <key=value>    # 設定上書き
-p, --profile <PROFILE>     # 設定プロファイル指定
```

---

## 🔐 認証

### 認証要件
- **OpenAI APIキー必須**
- ChatGPT Plus/Pro/Business/Edu/Enterpriseサブスクリプション推奨

### ログイン方法

#### 方法1: インタラクティブログイン
```bash
codex login
```

#### 方法2: APIキーでログイン
```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

#### 方法3: デバイス認証
```bash
codex login --device-auth
```

### ログイン状態確認
```bash
codex login status
```

### ログアウト
```bash
codex logout
```

---

## 📊 ccusage 機能

### 主要コマンド

```bash
# 日次レポート
ccusage-codex daily [OPTIONS]

# 月次レポート
ccusage-codex monthly [OPTIONS]

# セッション別レポート
ccusage-codex session [OPTIONS]
```

### オプション

```bash
-j, --json                  # JSON出力
-s, --since <YYYY-MM-DD>    # 開始日フィルター
-u, --until <YYYY-MM-DD>    # 終了日フィルター（inclusive）
-z, --timezone <IANA>       # タイムゾーン（デフォルト: Asia/Tokyo）
-l, --locale <LOCALE>       # ロケール（デフォルト: en-CA）
-O, --offline               # キャッシュされた価格データ使用
--compact                   # コンパクトなテーブルレイアウト
--color / --noColor         # カラー出力の有効/無効
-h, --help                  # ヘルプ表示
-v, --version               # バージョン表示
```

### 使用例

```bash
# 2026年2月の使用量を表示
ccusage-codex daily --since 2026-02-01 --until 2026-02-29

# JSON出力
ccusage-codex monthly --json

# 特定のタイムゾーンで表示
ccusage-codex daily --timezone America/New_York
```

---

## 🗂️ セッションファイルの場所

### Codex CLI（OpenAI）
- **ホームディレクトリ**: `~/.codex/`
- **セッションファイル**: `~/.codex/sessions/` ⚠️ 未検証（セッション未作成）
- **設定ファイル**: `~/.codex/config.toml`

### Claude Code（Anthropic）
- **公式セッション**: `~/.claude/projects/[project-path]/[session-id].jsonl`
- **このプロジェクトのhook**: `~/.claude/context-history/sessions/[date]/`

**重要**: ccusageは**Codex CLI専用**で、**Claude Codeのセッションには非対応**

---

## ⚠️ 重要な発見

### 1. Codex CLI ≠ Claude Code
- **Codex CLI**: OpenAI製のコーディングエージェント
- **Claude Code**: Anthropic製のコーディングエージェント
- **別物**: セッションフォーマット、APIキー、機能が異なる

### 2. ccusageの対応範囲
- ✅ **対応**: Codex CLIのセッション（`~/.codex/sessions/`）
- ❌ **非対応**: Claude Codeのセッション（`~/.claude/projects/`）

### 3. 認証要件
- Codex CLIはOpenAI APIキー必須
- ログインしないと実行不可（401 Unauthorized）

---

## 🎯 Claude Code統合ポイント

### Skillとしての統合

#### Codex Skill（OpenAI Codex CLI）
```yaml
---
name: codex
description: Analyze codebase using OpenAI Codex CLI
tools: Bash, Read, Grep
model: sonnet
---
```

**用途**:
- コードベース分析（Codex CLIの機能）
- コードレビュー（`codex review`）
- コード生成・編集（`codex exec`）

**注意点**:
- OpenAI APIキー必須
- ログイン状態の確認が必要
- `codex login status`で確認

**実行例**:
```bash
# ログイン確認
codex login status

# コードベース分析
codex exec "Analyze this codebase and suggest improvements"

# コードレビュー
codex review --files src/**/*.py
```

---

## 🔍 次のステップ（Task #3, #4）

### Task #3: ccusage調査
- ✅ ccusageインストール完了
- ⏳ Claude Code用の代替ツール調査が必要
- ⏳ 独自のセッション分析スクリプト検討

### Task #4: SpecStory統合調査
- ⏳ SpecStoryの出力フォーマット調査
- ⏳ SpecStory保存先の特定
- ⏳ Claude Codeセッション（`~/.claude/projects/`）との関連性調査

---

## 📝 サンプル出力

### Codex CLIヘルプ（一部抜粋）
```
Commands:
  exec        Run Codex non-interactively
  review      Run a code review non-interactively
  login       Manage login
  logout      Remove stored authentication credentials
  mcp         Run Codex as an MCP server
  apply       Apply the latest diff as git apply
  resume      Resume a previous session
  fork        Fork a previous session
  sandbox     Run commands within sandbox
  debug       Debugging tools
```

### ccusage-codexヘルプ（一部抜粋）
```
COMMANDS:
  daily       Show Codex token usage grouped by day
  monthly     Show Codex token usage grouped by month
  session     Show Codex token usage grouped by session

OPTIONS:
  -j, --json              Output as JSON
  -s, --since <date>      Filter from date
  -u, --until <date>      Filter until date
  -z, --timezone <tz>     Timezone (default: Asia/Tokyo)
```

---

## 🚨 制限事項

### Codex CLI
1. **APIキー必須**: OpenAI APIキーがないと動作しない
2. **サブスクリプション推奨**: ChatGPT Plus/Proなどのサブスクリプション推奨
3. **ネットワーク依存**: オフラインでは動作不可（ローカルモデル除く）

### ccusage
1. **Codex CLI専用**: Claude Codeのセッションには非対応
2. **セッションファイル必須**: `~/.codex/sessions/`にファイルが必要
3. **事後分析のみ**: リアルタイム監視は非対応

---

## 📚 参考リンク

- [Codex CLI - OpenAI](https://developers.openai.com/codex/cli/)
- [Codex GitHub Repository](https://github.com/openai/codex)
- [ccusage GitHub Repository](https://github.com/ryoppippi/ccusage)
- [Codex npm package](https://www.npmjs.com/package/@openai/codex)
- [ccusage npm package](https://www.npmjs.com/package/@ccusage/codex)

---

**調査完了日**: 2026-02-16
**次のタスク**: Task #3（ccusage調査）、Task #4（SpecStory統合調査）
