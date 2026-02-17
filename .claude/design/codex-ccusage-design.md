# Codex & ccusage Skills 設計ドキュメント

**Phase**: Phase 2 - 設計
**作成日**: 2026-02-17
**依存**: Phase 1（調査・研究）完了

---

## 📋 目次

1. [アーキテクチャ概要](#アーキテクチャ概要)
2. [Skill #1: /ccusage 設計](#skill-1-ccusage-設計)
3. [Skill #2: /compact-analyzer 設計](#skill-2-compact-analyzer-設計)
4. [Skill #3: /codex 設計](#skill-3-codex-設計)
5. [SpecStory統合設計](#specstory統合設計)
6. [エラーハンドリング戦略](#エラーハンドリング戦略)
7. [出力フォーマット設計](#出力フォーマット設計)
8. [実装への引き継ぎ事項](#実装への引き継ぎ事項)

---

## アーキテクチャ概要

### 設計方針

**Phase 1調査結果に基づく決定**:
- ✅ **ハイブリッドアプローチ**: ccusage（80%カバー）+ 独自実装（20%）
- ✅ **グローバルインストール**: `npm install -g ccusage`でどこからでも実行可能
- ✅ **コスト最適化**: 無料ツール優先、Codex CLIはオプション（$0-20/月）

### システムアーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                     ユーザーリクエスト                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                  ┌──────────▼─────────┐
│  /ccusage      │                  │  /compact-analyzer │
│  Skill         │                  │  Skill (オプション)│
│                │                  │                    │
│ - 日次分析     │                  │ - compact検出      │
│ - 月次分析     │                  │ - 差分計算         │
│ - セッション別 │                  │ - Kitchen-Sink検出 │
│ - JSON出力     │                  │ - Lost-in-middle   │
└────────┬───────┘                  └──────────┬─────────┘
         │                                     │
         │        ┌──────────────┐             │
         └────────► ccusage CLI  ◄─────────────┘
                  │ (v18.0.5)    │
                  └──────┬───────┘
                         │
                  ┌──────▼────────────────────────┐
                  │  データソース                  │
                  ├───────────────────────────────┤
                  │ ~/.claude/projects/*.jsonl    │
                  │ .specstory/history/*.md       │
                  └───────────────────────────────┘
                         │
                  ┌──────▼─────────┐
                  │  /codex Skill  │
                  │  (オプション)  │
                  │                │
                  │ - AI分析       │
                  │ - コード洞察   │
                  └────────────────┘
```

### ツール選択

| ツール | 用途 | コスト | 優先度 |
|--------|------|--------|--------|
| **ccusage** | トークン分析、コスト計算 | $0 | 必須 |
| **SpecStory** | 会話履歴、compact検出 | $0 | 必須 |
| **独自実装** | compact差分、異常検出 | $0 | 推奨 |
| **Codex CLI** | AI駆動の分析 | $0-20/月 | オプション |

---

## Skill #1: /ccusage 設計

### 概要

ccusageツールを使用したClaude Codeセッションのトークン使用量分析。

### YAMLフロントマター

```yaml
---
name: ccusage
description: Analyze Claude Code session token usage and costs using ccusage CLI
tools: Bash, Read, Grep
model: sonnet
---
```

### ワークフロー設計

#### ステップ1: 要求解析

```
入力: ユーザーコマンド
例: /ccusage daily --since 20260201
    /ccusage session --json

処理:
1. コマンドタイプを特定（daily/monthly/session）
2. オプションフラグを解析（--json, --since, --until）
3. プロジェクトフィルターを適用（必要に応じて）
```

#### ステップ2: ccusageコマンド実行

```bash
# 基本パターン
ccusage daily [OPTIONS]
ccusage monthly [OPTIONS]
ccusage session [OPTIONS]

# 主要オプション
-j, --json              # JSON出力
-s, --since YYYYMMDD    # 開始日
-u, --until YYYYMMDD    # 終了日
-p, --project NAME      # プロジェクトフィルター
-q, --jq 'QUERY'        # jq統合
```

#### ステップ3: 結果解析

```
JSON出力の場合:
- jqで重要なフィールドを抽出
- 高コストセッションを特定（閾値: $5以上）
- トークン使用量トップ5を抽出

テーブル出力の場合:
- 視覚的に整形して表示
- 重要な統計をハイライト
```

#### ステップ4: 分析・洞察提供

```
分析内容:
1. トータルコスト
2. トークン使用量（Input/Output/Cache）
3. 高コストセッションの特定
4. 最適化提案（必要に応じて）
```

#### ステップ5: SpecStory連携（オプション）

```
高コストセッション発見時:
1. SpecStoryで会話内容を確認
2. なぜコストが高かったかを分析
3. 最適化のヒントを提供
```

#### ステップ6: レポート生成

```markdown
## ccusage 分析レポート

### サマリー
- 期間: 2026-02-01 〜 2026-02-17
- 総コスト: $107.09
- 総トークン: 215,257,240

### 高コストセッション
1. context-manager-main: $60.74 (139M tokens)
   - 推奨: compact検出を確認

### 最適化提案
- Cache Read使用率が高い（95%）→ 良好
- 長時間セッションはcompactを検討
```

### エラーハンドリング

| エラー | 原因 | 対処 |
|--------|------|------|
| `command not found: ccusage` | 未インストール | `npm install -g ccusage`をガイド |
| `No sessions found` | セッションファイルなし | `~/.claude/projects/`を確認 |
| `Invalid date format` | 日付フォーマット不正 | YYYYMMDD形式を案内 |

**PITFALLS.md連携**:
- エラー発生時、PITFALLS.mdを自動検索
- 既知のエラーパターンがあれば解決策を提示
- 新規エラーは記録して次回に備える

---

## Skill #2: /compact-analyzer 設計

### 概要

SpecStory Markdownファイルを解析し、compact検出と差分計算を行う独自実装。

### YAMLフロントマター

```yaml
---
name: compact-analyzer
description: Detect compact events and analyze token/content differences from SpecStory history
tools: Bash, Read, Grep, Python
model: sonnet
---
```

### ワークフロー設計

#### ステップ1: SpecStoryファイル検出

```bash
# .specstory/history/ディレクトリからMarkdownファイルを検索
find .specstory/history/ -name "*.md" -type f | sort -r
```

#### ステップ2: Compact検出

```python
def detect_compact_events(md_file):
    """
    SpecStory Markdownファイルからcompactイベントを検出

    検出パターン:
    - `compact_detected: true`
    - トークン数の急激な減少
    """
    compacts = []
    with open(md_file) as f:
        content = f.read()

    # compact_detected フラグを検索
    import re
    compact_matches = re.finditer(r'compact_detected:\s*(true|false)', content)

    # トークン情報を抽出
    token_matches = re.finditer(r'total_tokens:\s*(\d+)', content)

    return {
        'compact_detected': any(m.group(1) == 'true' for m in compact_matches),
        'token_history': [int(m.group(1)) for m in token_matches]
    }
```

#### ステップ3: 差分計算

```python
def calculate_compact_diff(before_tokens, after_tokens):
    """
    Compact前後のトークン差分を計算
    """
    diff = before_tokens - after_tokens
    ratio = after_tokens / before_tokens if before_tokens > 0 else 0

    return {
        'before': before_tokens,
        'after': after_tokens,
        'diff': diff,
        'reduction_ratio': 1 - ratio,
        'saved_tokens': diff
    }
```

#### ステップ4: Kitchen-Sink / Lost-in-the-Middle 検出

```python
# 閾値設定
KITCHEN_SINK_THRESHOLD = 167000  # tokens
LOST_IN_MIDDLE_THRESHOLD = 100000  # tokens

def detect_issues(session_data):
    """
    Kitchen-Sink/Lost-in-the-Middle問題を検出
    """
    total_tokens = session_data['total_tokens']
    duration_minutes = session_data['duration_ms'] / 60000

    issues = []

    # Kitchen-Sink検出（高トークン使用）
    if total_tokens > KITCHEN_SINK_THRESHOLD:
        issues.append({
            'type': 'kitchen_sink',
            'tokens': total_tokens,
            'severity': 'high' if total_tokens > 200000 else 'medium'
        })

    # Lost-in-the-Middle検出（長時間 + 中程度のトークン）
    if total_tokens > LOST_IN_MIDDLE_THRESHOLD and duration_minutes > 30:
        issues.append({
            'type': 'lost_in_middle',
            'tokens': total_tokens,
            'duration_minutes': duration_minutes,
            'severity': 'medium'
        })

    return issues
```

#### ステップ5: レポート生成

```markdown
## Compact分析レポート

### セッション: 2026-02-16_07-19-30Z-context-manager

**Compactイベント検出**: ✅ 検出

**トークン推移**:
- Compact前: 167,340 tokens
- Compact後: 81,340 tokens
- 削減量: 86,000 tokens (51.4%削減)

**失われた可能性のある情報**:
- ツール実行結果の詳細
- 中間的な会話の文脈
- デバッグ出力

**推奨アクション**:
- 重要な情報は早めにドキュメント化
- 長時間セッションは分割を検討
```

### エラーハンドリング

| エラー | 原因 | 対処 |
|--------|------|------|
| `SpecStory directory not found` | `.specstory/`なし | `specstory sync`実行を案内 |
| `No compact events detected` | compactイベントなし | 正常（エラーではない） |
| `Invalid Markdown format` | フォーマット不正 | SpecStoryバージョン確認 |

---

## Skill #3: /codex 設計

### 概要

OpenAI Codex CLIを使用したコードベース分析（オプション機能）。

### YAMLフロントマター

```yaml
---
name: codex
description: Analyze codebase using OpenAI Codex CLI (requires OpenAI API key)
tools: Bash, Read
model: sonnet
---
```

### ワークフロー設計

#### ステップ1: 認証確認

```bash
# ログイン状態確認
codex login status

# 未ログインの場合
if [[ $? -ne 0 ]]; then
    echo "❌ Codex CLI is not authenticated"
    echo "Run: codex login"
    exit 1
fi
```

#### ステップ2: コードベース分析

```bash
# 非インタラクティブ実行
codex exec "Analyze this codebase and suggest improvements for token efficiency"

# コードレビュー
codex review --files "src/**/*.py"
```

#### ステップ3: 結果統合

```
Codex分析結果とccusageデータを統合:
1. ccusageで高コストセッションを特定
2. Codexでそのセッションのコード品質を分析
3. 最適化提案を生成
```

### エラーハンドリング

| エラー | 原因 | 対処 |
|--------|------|------|
| `401 Unauthorized` | 未ログイン | `codex login`を案内 |
| `API rate limit exceeded` | レート制限 | 待機時間を案内 |
| `Budget exceeded` | 予算超過 | 使用停止を推奨 |

---

## SpecStory統合設計

### ファイル発見戦略

```bash
# プロジェクトルートから.specstory/を検索
SPECSTORY_DIR=".specstory/history"

if [[ ! -d "$SPECSTORY_DIR" ]]; then
    echo "⚠️ SpecStory directory not found"
    echo "Run: specstory sync"
    exit 1
fi

# 最新のMarkdownファイルを取得
LATEST_MD=$(find "$SPECSTORY_DIR" -name "*.md" -type f | sort -r | head -1)
```

### 解析戦略

**Markdown解析**:
```python
import re

def parse_specstory_markdown(md_file):
    """
    SpecStory Markdownファイルを解析
    """
    with open(md_file) as f:
        content = f.read()

    # メタデータ抽出
    session_id = re.search(r'<!-- Claude Code Session ([\w-]+)', content)
    compact_detected = re.search(r'compact_detected:\s*true', content)

    # トークン情報抽出
    tokens = re.findall(r'total_tokens:\s*(\d+)', content)

    return {
        'session_id': session_id.group(1) if session_id else None,
        'compact_detected': bool(compact_detected),
        'token_history': [int(t) for t in tokens]
    }
```

**JSONL解析**（代替手段）:
```python
import json

def parse_claude_session_jsonl(jsonl_file):
    """
    Claude Code公式のJSONLファイルを解析
    """
    events = []
    with open(jsonl_file) as f:
        for line in f:
            event = json.loads(line)
            events.append(event)

    # compactイベントを検出
    compacts = [e for e in events if e.get('type') == 'compact']

    return {
        'events': events,
        'compacts': compacts,
        'total_tokens': sum(e.get('usage', {}).get('total_tokens', 0) for e in events)
    }
```

### compactマーカー検出

**検出パターン**:
1. **SpecStory Markdown**: `compact_detected: true`
2. **JSONL**: `{"type": "compact", ...}`
3. **トークン推移**: 急激な減少（30%以上）

### compact前後の差分計算

```python
def calculate_compact_impact(events):
    """
    compactイベント前後の差分を計算
    """
    compact_indices = [i for i, e in enumerate(events) if e.get('type') == 'compact']

    impacts = []
    for idx in compact_indices:
        before_tokens = sum(e.get('usage', {}).get('total_tokens', 0)
                          for e in events[:idx])
        after_tokens = sum(e.get('usage', {}).get('total_tokens', 0)
                         for e in events[idx+1:])

        impacts.append({
            'index': idx,
            'before': before_tokens,
            'after': after_tokens,
            'diff': before_tokens - after_tokens,
            'reduction_ratio': (before_tokens - after_tokens) / before_tokens
        })

    return impacts
```

---

## エラーハンドリング戦略

### 階層的エラーハンドリング

```
Level 1: 事前チェック（Pre-flight checks）
    ↓
Level 2: 実行時エラー（Runtime errors）
    ↓
Level 3: PITFALLS.md検索（Known issues）
    ↓
Level 4: リトライ・代替手段（Fallback）
    ↓
Level 5: ユーザー報告（User notification）
```

### PITFALLS.md統合

**エラー検出時**:
```bash
# PITFALLS.mdから既知のエラーを検索
error_id=$(grep -l "$error_message" .claude/PITFALLS.md | \
           grep -o 'ERROR-[0-9]*' | head -1)

if [[ -n "$error_id" ]]; then
    echo "✅ Known issue: $error_id"
    # 解決策を表示
    grep -A 10 "^## $error_id" .claude/PITFALLS.md
fi
```

### リトライポリシー

```yaml
retry_policy:
  max_attempts: 3
  backoff: exponential
  retry_on:
    - network_error
    - rate_limit
    - temporary_failure
  no_retry_on:
    - authentication_error
    - invalid_input
    - permission_denied
```

---

## 出力フォーマット設計

### JSON出力フォーマット

```json
{
  "summary": {
    "tool": "ccusage",
    "version": "18.0.5",
    "timestamp": "2026-02-17T00:35:00Z",
    "analysis_type": "daily",
    "period": {
      "start": "2026-02-01",
      "end": "2026-02-17"
    }
  },
  "metrics": {
    "total_cost": 107.09,
    "total_tokens": 215257240,
    "input_tokens": 56777,
    "output_tokens": 21135,
    "cache_create_tokens": 9873205,
    "cache_read_tokens": 205306123
  },
  "high_cost_sessions": [
    {
      "session_id": "context-manager-main",
      "cost": 60.74,
      "tokens": 139814000,
      "compact_detected": true,
      "recommendation": "Consider breaking into smaller sessions"
    }
  ],
  "compact_events": [
    {
      "session_id": "60789946-5bac-4335-8861-9579b29b6bfa",
      "timestamp": "2026-02-16T07:19:30Z",
      "before_tokens": 167340,
      "after_tokens": 81340,
      "reduction": 86000,
      "reduction_ratio": 0.514
    }
  ]
}
```

### Markdown出力フォーマット

```markdown
# Claude Code セッション分析レポート

**生成日時**: 2026-02-17 00:35:00
**分析期間**: 2026-02-01 〜 2026-02-17
**ツール**: ccusage v18.0.5

---

## 📊 サマリー

| 指標 | 値 |
|------|-----|
| 総コスト | $107.09 |
| 総トークン | 215,257,240 |
| 入力トークン | 56,777 |
| 出力トークン | 21,135 |
| Cache Create | 9,873,205 |
| Cache Read | 205,306,123 |

---

## 🔥 高コストセッション

### 1. context-manager-main
- **コスト**: $60.74
- **トークン**: 139,814,000
- **Compact検出**: ✅ あり
- **推奨**: セッションを小さく分割

---

## 📉 Compactイベント

### セッション: 60789946-5bac...
- **日時**: 2026-02-16 07:19:30Z
- **Compact前**: 167,340 tokens
- **Compact後**: 81,340 tokens
- **削減量**: 86,000 tokens (51.4%)

---

## 💡 最適化提案

1. ✅ Cache Read使用率が高い（95%）→ 良好
2. ⚠️ 長時間セッションはcompactリスク → 分割を検討
3. 💰 高コストセッションの内容を確認 → SpecStoryで調査
```

---

## 実装への引き継ぎ事項

### Phase 3: Codex Skill実装

**ファイル構成**:
```
.claude/skills/codex/
├── SKILL.md           # 本設計に基づく実装
└── references/
    └── examples.md    # 使用例
```

**実装優先度**: 低（オプション機能）

**注意事項**:
- OpenAI APIキー必須
- 予算制限（$0-20/月）の実装
- エラー時のフォールバック

---

### Phase 4: ccusage Skill実装

**ファイル構成**:
```
.claude/skills/ccusage/
├── SKILL.md
└── references/
    └── command-reference.md
```

**実装優先度**: 高（必須機能）

**実装要件**:
1. グローバルインストールチェック
2. 日次/月次/セッション別レポート
3. JSON出力対応
4. jq統合
5. 高コストセッション検出（閾値: $5）
6. SpecStory連携（オプション）

---

### compact-analyzer Skill実装

**ファイル構成**:
```
.claude/skills/compact-analyzer/
├── SKILL.md
├── scripts/
│   └── analyze_compact.py    # Python実装
└── references/
    └── algorithm.md
```

**実装優先度**: 中（推奨機能）

**実装要件**:
1. SpecStory Markdown解析
2. compact検出（`compact_detected: true`）
3. トークン差分計算
4. Kitchen-Sink検出（閾値: 167K tokens）
5. Lost-in-the-middle検出

---

## 設計完了チェックリスト

- [x] アーキテクチャ決定（ハイブリッドアプローチ）
- [x] Skill #1（/ccusage）設計完了
- [x] Skill #2（/compact-analyzer）設計完了
- [x] Skill #3（/codex）設計完了
- [x] SpecStory統合戦略決定
- [x] エラーハンドリング戦略定義
- [x] 出力フォーマット設計完了
- [x] 実装への引き継ぎ事項文書化

---

**次のフェーズ**: Phase 3（Codex Skill実装）、Phase 4（ccusage Skill実装）

**設計完了日**: 2026-02-17
**見積時間**: 2-3時間
