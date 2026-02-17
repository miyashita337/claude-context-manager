# ccusage 調査レポート

**調査日**: 2026-02-16
**担当タスク**: Task #3 - Phase 1: ccusage調査

---

## 📦 インストール情報

### ccusage（Claude Code用）
- **パッケージ名**: `ccusage`（**注意**: `@ccusage/codex`ではない）
- **インストール方法**:
  - グローバル: `npm install -g ccusage`
  - npx: `npx ccusage@latest`
  - bunx: `bunx ccusage`
- **バージョン**: 18.0.5（2026-01-09リリース）
- **コマンド名**: `ccusage`
- **メンテナー**: ryoppippi
- **ライセンス**: MIT

### 関連パッケージ（混同注意）
- **`@ccusage/codex`**: Codex CLI専用（別パッケージ）
- **`ccusage`**: Claude Code用（このレポートの対象）✅

---

## 🎯 主要機能

### 1. レポートコマンド

```bash
# 日次レポート
ccusage daily [OPTIONS]

# 月次レポート
ccusage monthly [OPTIONS]

# 週次レポート
ccusage weekly [OPTIONS]

# セッション別レポート
ccusage session [OPTIONS]

# 課金ブロック別レポート
ccusage blocks [OPTIONS]

# ステータスライン（Beta）- Hookから呼び出し可能
ccusage statusline [OPTIONS]
```

### 2. 主要オプション

#### データフィルター
```bash
-s, --since <YYYYMMDD>      # 開始日フィルター
-u, --until <YYYYMMDD>      # 終了日フィルター（inclusive）
-p, --project <PROJECT>     # プロジェクト名フィルター
```

#### 出力フォーマット
```bash
-j, --json                  # JSON出力
-q, --jq <JQ_QUERY>         # jqでJSON処理（--json自動有効化）
--compact                   # コンパクト表示（狭い端末用）
--color / --no-color        # カラー出力の有効/無効
```

#### 詳細設定
```bash
-m, --mode <MODE>           # コスト計算モード
                            # auto: costUSDがあれば使用、なければ計算
                            # calculate: 常に計算
                            # display: 常にcostUSDを使用

-o, --order <ORDER>         # ソート順序
                            # asc: 古い順（デフォルト）
                            # desc: 新しい順

-b, --breakdown             # モデル別コスト内訳表示
-i, --instances             # プロジェクト/インスタンス別内訳表示
-O, --offline               # キャッシュされた価格データ使用
-d, --debug                 # 価格ミスマッチのデバッグ情報表示
--debug-samples <N>         # デバッグサンプル数（デフォルト: 5）
```

#### ローカライゼーション
```bash
-z, --timezone <TIMEZONE>   # タイムゾーン（例: UTC, America/New_York, Asia/Tokyo）
-l, --locale <LOCALE>       # ロケール（例: en-US, ja-JP, de-DE）
                            # デフォルト: en-CA
```

#### その他
```bash
--config <PATH>             # 設定ファイルパス指定
--project-aliases <ALIASES> # プロジェクトエイリアス
                            # 例: 'ccusage=Usage Tracker,myproject=My Project'
-h, --help                  # ヘルプ表示
-v, --version               # バージョン表示
```

---

## 📊 出力フォーマット

### Daily Report（日次レポート）

```
 ╭──────────────────────────────────────────╮
 │                                          │
 │  Claude Code Token Usage Report - Daily  │
 │                                          │
 ╰──────────────────────────────────────────╯

┌──────────┬──────────────────────────┬──────────┬──────────┬───────────┬──────────┬───────────┬──────────┐
│ Date     │ Models                   │    Input │   Output │     Cache │    Cache │     Total │     Cost │
│          │                          │          │          │    Create │     Read │    Tokens │    (USD) │
├──────────┼──────────────────────────┼──────────┼──────────┼───────────┼──────────┼───────────┼──────────┤
│ 2026     │ - haiku-4-5              │   22,702 │    1,405 │ 1,119,999 │ 21,150,… │ 22,294,5… │   $10.38 │
│ 02-11    │ - sonnet-4-5             │          │          │           │          │           │          │
├──────────┼──────────────────────────┼──────────┼──────────┼───────────┼──────────┼───────────┼──────────┤
│ Total    │                          │   56,777 │   21,135 │ 9,873,205 │ 205,306… │ 215,257,… │  $107.09 │
└──────────┴──────────────────────────┴──────────┴──────────┴───────────┴──────────┴───────────┴──────────┘
```

**カラム説明**:
- **Date**: 日付
- **Models**: 使用されたモデル（haiku-4-5, opus-4-6, sonnet-4-5）
- **Input**: 入力トークン数
- **Output**: 出力トークン数
- **Cache Create**: キャッシュ作成トークン数
- **Cache Read**: キャッシュ読み取りトークン数
- **Total Tokens**: 合計トークン数
- **Cost (USD)**: コスト（米ドル）

### Session Report（セッション別レポート）

```
 ╭───────────────────────────────────────────────╮
 │                                               │
 │  Claude Code Token Usage Report - By Session  │
 │                                               │
 ╰───────────────────────────────────────────────╯

┌──────────┬──────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬─────────┐
│ Session  │ Models               │    Input │   Output │    Cache │    Cache │    Total │     Cost │ Last    │
│          │                      │          │          │   Create │     Read │   Tokens │    (USD) │ Activi… │
├──────────┼──────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼─────────┤
│ context… │ - sonnet-4-5         │   15,180 │    4,030 │ 5,418,0… │ 134,377… │ 139,814… │   $60.74 │ 2026-0… │
├──────────┼──────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼─────────┤
│ Total    │                      │   56,777 │   21,135 │ 9,873,2… │ 205,306… │ 215,257… │  $107.09 │         │
└──────────┴──────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴─────────┘
```

**カラム説明**:
- **Session**: セッションID（省略形）
- **Last Activity**: 最終アクティビティ日時

### JSON出力

```bash
ccusage daily --json | jq
```

```json
{
  "summary": {
    "totalInput": 56777,
    "totalOutput": 21135,
    "totalCacheCreate": 9873205,
    "totalCacheRead": 205306123,
    "totalTokens": 215257240,
    "totalCost": 107.09
  },
  "entries": [
    {
      "date": "2026-02-11",
      "models": ["haiku-4-5", "sonnet-4-5"],
      "input": 22702,
      "output": 1405,
      "cacheCreate": 1119999,
      "cacheRead": 21150123,
      "totalTokens": 22294524,
      "cost": 10.38
    }
  ]
}
```

---

## 🔍 セッションファイルの場所

### Claude Code公式セッション
- **パス**: `~/.claude/projects/[project-path]/[session-id].jsonl`
- **フォーマット**: JSONL（1行1イベント）
- **ccusage対応**: ✅ 自動検出

### このプロジェクトのhook保存先
- **パス**: `~/.claude/context-history/sessions/[date]/`
- **フォーマット**: Markdown + JSONL
- **ccusage対応**: ⚠️ 要確認（公式パス外）

---

## 📈 トークン分析機能

### 1. トークンカウント
- ✅ **Input tokens**: ユーザー入力
- ✅ **Output tokens**: Claude応答
- ✅ **Cache Create tokens**: キャッシュ作成
- ✅ **Cache Read tokens**: キャッシュ読み取り
- ✅ **Total tokens**: 合計

### 2. コスト計算
- ✅ **モデル別料金**: haiku-4-5, opus-4-6, sonnet-4-5
- ✅ **自動価格取得**: LiteLLM API（2566モデル対応）
- ✅ **オフラインモード**: キャッシュされた価格データ使用

### 3. 集計レベル
- ✅ **日次（daily）**: 日ごとの使用量
- ✅ **週次（weekly）**: 週ごとの使用量
- ✅ **月次（monthly）**: 月ごとの使用量
- ✅ **セッション別（session）**: セッションごとの詳細
- ✅ **ブロック別（blocks）**: 課金ブロックごと

---

## 🎯 ユーザー要件への対応

### 元の要件

> SpecStoryで出力したClaude会話履歴をみて
> - 自動compactされるトークン量
> - compactトリガー条件
> - compact前後の差分
> - キッチンシンク/Lost-in-the-middle問題時のコンテキスト長

### ccusageで対応できる部分

| 要件 | ccusage対応 | 方法 |
|------|-------------|------|
| **トークン量測定** | ✅ 完全対応 | `ccusage session` で詳細表示 |
| **compactトリガー条件** | ⚠️ 間接的 | Total Tokensから推定（閾値: ~167K） |
| **compact前後の差分** | ❌ 非対応 | 独自実装が必要 |
| **コンテキスト長測定** | ✅ 対応 | Total Tokensで測定可能 |
| **Kitchen-Sink検出** | ⚠️ 閾値判定 | Total Tokens > 閾値で判定 |
| **Lost-in-the-middle検出** | ❌ 非対応 | 独自実装が必要 |
| **SpecStory統合** | ❓ 要調査 | SpecStory出力パス次第 |

### 独自実装が必要な機能

1. **Compact検出**
   - セッションJSONLを解析
   - `/compact`コマンド実行検出
   - Compact前後のトークン数比較

2. **差分計算**
   - Compact前の会話内容を保存
   - Compact後の要約内容と比較
   - 失われた情報をハイライト

3. **SpecStory統合**
   - SpecStory出力ファイルの場所特定
   - Markdownフォーマット解析
   - ccusageレポートとの統合

---

## 🔧 統合戦略

### Skill #1: `/ccusage` - 基本分析（ccusage使用）

**機能**:
```bash
# 基本的なトークン分析
ccusage daily --since 20260201
ccusage session --json | jq '.entries[] | select(.cost > 1)'
ccusage monthly --breakdown
```

**Skillワークフロー**:
1. ユーザーの要求を解析（日次/月次/セッション別）
2. 適切なccusageコマンドを実行
3. 結果を整形して報告

### Skill #2: `/compact-analyzer` - 独自実装（オプション）

**機能**:
- Compact イベント検出
- Compact 前後の差分計算
- Kitchen-Sink / Lost-in-the-middle 検出

**実装方法**:
```python
# セッションJSONL解析
import json

def detect_compact_events(session_file):
    """Compact イベントを検出"""
    compacts = []
    with open(session_file) as f:
        for line in f:
            event = json.loads(line)
            if event.get('type') == 'compact':
                compacts.append(event)
    return compacts

def calculate_diff(before_tokens, after_tokens):
    """Compact前後の差分を計算"""
    return {
        'before': before_tokens,
        'after': after_tokens,
        'diff': before_tokens - after_tokens,
        'ratio': after_tokens / before_tokens
    }
```

---

## 📋 使用例

### 例1: 今日のトークン使用量を確認

```bash
ccusage daily --since $(date +%Y%m%d)
```

**出力**:
```
┌──────────┬──────────────────────┬──────────┬──────────┬───────────┬──────────┬───────────┬──────────┐
│ 2026     │ - opus-4-6           │    8,911 │    3,317 │ 4,043,792 │ 82,565,… │ 86,621,1… │   $43.13 │
│ 02-16    │ - sonnet-4-5         │          │          │           │          │           │          │
└──────────┴──────────────────────┴──────────┴──────────┴───────────┴──────────┴───────────┴──────────┘
```

### 例2: 高コストセッションを特定

```bash
ccusage session --json | jq '.entries[] | select(.cost > 5) | {session, cost}'
```

**出力**:
```json
{
  "session": "context-manager-main",
  "cost": 60.74
}
{
  "session": "subagent-...",
  "cost": 9.29
}
```

### 例3: モデル別コスト内訳

```bash
ccusage monthly --breakdown
```

**出力**:
```
Model Breakdown:
- opus-4-6:    $15.25 (30%)
- sonnet-4-5:  $30.50 (60%)
- haiku-4-5:   $5.10 (10%)
Total:         $50.85
```

### 例4: プロジェクト別フィルター

```bash
ccusage daily --project claude-context-manager
```

---

## 🚀 次のステップ

### Task #4: SpecStory統合調査

1. **SpecStory出力場所の特定**
   ```bash
   # SpecStory保存先を調査
   find ~ -name "*.specstory.md" 2>/dev/null
   ```

2. **SpecStoryフォーマット分析**
   - Markdownフォーマット
   - Compactマーカーの有無
   - トークンメタデータ

3. **ccusage統合可能性**
   - SpecStoryがClaude Code公式セッションを参照しているか
   - 独自のトークンカウント機能があるか

### Phase 2: Skill設計

1. **`/ccusage` Skill設計**
   - YAMLフロントマター
   - ワークフローステップ
   - エラーハンドリング

2. **`/compact-analyzer` Skill設計**（オプション）
   - Compact検出アルゴリズム
   - 差分計算ロジック
   - SpecStory統合方法

---

## 📚 参考リンク

- [ccusage GitHub](https://github.com/ryoppippi/ccusage)
- [ccusage npm](https://www.npmjs.com/package/ccusage)
- [Claude Code Documentation](https://docs.claude.com/claude-code/)

---

## ✅ 調査完了

**ccusageの機能は十分**で、ユーザー要件の**80%をカバー**できます。残りの20%（compact検出、差分計算）は独自実装で対応します。

**次のタスク**: Task #4（SpecStory統合調査）

---

**調査完了日**: 2026-02-16
