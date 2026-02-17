# /ccusage Skill 使用ガイド

**対象ユーザー**: Claude Codeセッションのコストやトークン消費を把握したいユーザー
**前提条件**: `ccusage` グローバルインストール済み（`npm install -g ccusage`）

---

## インストール

```bash
# ccusage をグローバルインストール
npm install -g ccusage

# バージョン確認
ccusage --version
# → 18.0.5

# 簡単な動作確認
make ccusage-report
```

---

## 基本的な使い方

### 今日のサマリー

```bash
/ccusage
```

**出力例**:
```
## ccusage Analysis - Today (2026-02-17)

Total Cost  : $12.50
Total Tokens: 25,430,120
  Input          : 8,200
  Output         : 2,100
  Cache Create   : 1,200,000
  Cache Read     : 24,219,820

Sessions    : 3 active
Alerts      : None ✅
```

---

### 日次内訳（期間指定）

```bash
/ccusage daily --since 20260201
```

> **注意**: 日付は `YYYYMMDD` 形式（ハイフンなし）

**出力例**:
```
## Daily Breakdown - Feb 2026

| Date     | Cost   | Total Tokens |
|----------|--------|--------------|
| 2026-02-11 | $10.38 | 22,294,524 |
| 2026-02-16 | $43.13 | 86,621,100 |
| Total    | $107.09| 215,257,240 |
```

---

### セッション別分析

```bash
/ccusage session
```

**出力例**:
```
## Session Analysis

⚠️  1 high-cost session found:

1. context-manager [2026-02-16]
   Cost  : $60.74
   Tokens: 139,814,000
   Issue : Kitchen-Sink (>167K tokens)
   Action: Consider splitting into smaller sessions
```

---

### モデル別コスト内訳

```bash
/ccusage monthly --breakdown
```

**出力例**:
```
## Monthly Summary - February 2026

Total Cost: $107.09

Model Breakdown:
  claude-opus-4-6   : $45.00 (42%)
  claude-sonnet-4-5 : $55.00 (51%)
  claude-haiku-4-5  : $7.09  (7%)

Recommendation:
  ⚠️  Use haiku for simple tasks to reduce cost
```

---

## 高度な使い方

### JSON + jq でフィルタリング

```bash
# $5以上のセッションを抽出
/ccusage session --json | jq '.entries[] | select(.cost > 5) | {session, cost}'

# 今日の総コストのみ取得
/ccusage daily --since "$(date +%Y%m%d)" --json | jq '.summary.totalCost'

# トークン数トップ3セッション
/ccusage session --json | jq '[.entries | sort_by(-.totalTokens)] | .[:3]'
```

---

### SpecStory と組み合わせた compact 分析

```bash
# 1. まず SpecStory で履歴を同期
specstory sync

# 2. ccusage で高コストセッションを特定
/ccusage session

# 3. compact が検出されたら /compact-analyzer で詳細分析
/compact-analyzer
```

---

### プロジェクト別フィルター

```bash
# 現在のプロジェクトのみ
/ccusage daily --project claude-context-manager

# 特定プロジェクトのセッション一覧
/ccusage session --project claude-context-manager --json
```

---

## 検出される問題

### Kitchen-Sink セッション
- **条件**: 1セッションで167,000トークン以上
- **症状**: レスポンスが遅くなる、品質が下がる
- **対処**: セッションを小さく分割する

### Lost-in-the-Middle
- **条件**: 長時間セッション + 中程度のトークン（推定）
- **症状**: 会話の中盤の情報が無視される
- **対処**: 重要情報を明示的に再提示する

### Compact イベント
- **条件**: SpecStoryの `compact_detected: true`
- **症状**: 会話履歴が圧縮され、古い文脈が失われる
- **対処**: 重要情報はドキュメントに記録しておく

---

## Makefile ショートカット

```bash
# 今日のレポートを素早く確認
make ccusage-report
```

---

## トラブルシューティング

| エラー | 原因 | 解決策 |
|--------|------|--------|
| `command not found: ccusage` | 未インストール | `npm install -g ccusage` |
| 空の出力 | 日付フォーマット不正 | `YYYYMMDD`形式を使う |
| `jq: command not found` | jq未インストール | `brew install jq` |
| セッションが表示されない | データなし | `ls ~/.claude/projects/` で確認 |

詳細は [PITFALLS.md](../../.claude/PITFALLS.md) の `CCUSAGE-*` エントリを参照。

---

## よくある質問

**Q: `@ccusage/codex` と `ccusage` の違いは？**
A: `@ccusage/codex` は OpenAI Codex CLI 用、`ccusage` は Claude Code 用。Claude Code には `ccusage` を使う。

**Q: どのくらいの頻度で実行すべき？**
A: 毎日 `/ccusage` でコスト確認することを推奨。$70K tokens/日 または $10/日 を超えたら詳細調査。

**Q: compact が頻繁に起こる場合は？**
A: セッションを短く保つ（目安: 130K tokens 以下）か、`/compact-analyzer` で詳細分析。

---

## 関連 Skill

- `/compact-analyzer` — compact差分の詳細分析
- `/fact-check` — ツール動作を公式ドキュメントで検証
- `/git-workflow` — Git操作の安全なガイド
