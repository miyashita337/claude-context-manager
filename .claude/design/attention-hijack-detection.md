# Design: 注意横取り検知システム（Attention Hijack Detection）

- **Status**: Draft（Epic 着手前のスケルトン）
- **Date**: 2026-04-15
- **Scope**: Epic Issue で管理。本ドキュメントは Phase 1（調査）着手時点の骨子。

## 背景

セッション中に「注意が横取りされる」ことで作業品質が劣化するが、既存の P0/P1/P2（UserPromptSubmit）では「話題逸脱」「質問散弾」までしか扱えていない。より広い意味での attention hijacking（タスク中の割り込み、サブスレッド深堀りによる本筋喪失、tool 連鎖の脱線など）を検知し、**セッション内で指摘できる仕組み**が必要。

ADR-001 で SpecStory を非採用と決定したため、検知エンジン・レポート生成ともに自作する。

## 「注意の横取り」operational definition（Draft）

**定義候補（Phase 1 で確定）**：

> あるタスク T の実行中に、T の完了前に T とは意味的に独立な別タスク T' に切り替わり、かつ元のタスク T の完了状況が確認されないまま進行する現象。

派生パターン：
1. **サブスレッド深堀り**：脇道の調査が本来の目的を超える規模に拡大
2. **Tool連鎖逸脱**：tool_use の連続が当初の意図から離れていく
3. **割り込み質問**：進行中タスクに関係ない質問で作業が中断される
4. **過去履歴フォーカス劣化**：古い文脈への依存が増え、新しい指示が劣後する

## 検知シグナル（JSONL から抽出可能なもの）

| # | シグナル | 抽出方法 | 備考 |
|---|---|---|---|
| S1 | ユーザー発言の意味ベクトル距離 | 直前N件との埋め込み類似度（topic-server 活用） | P1 既実装の転用 |
| S2 | tool_use 連鎖の方向性 | tool名系列のトピッククラスタリング | 新規実装 |
| S3 | メッセージ時間間隔 | `timestamp` の diff | 長時間空白 = コンテキストロス |
| S4 | task-level タグ | TaskCreate/TaskUpdate イベント（将来） | 現状未記録 |
| S5 | 質問散弾マーカー | `?` 数、keyword markers | P0 既実装転用 |
| S6 | コンテキスト長推移 | usage.total_tokens の時系列 | kitchen sink 判定と連動 |
| S7 | 発言者交替頻度 | user/assistant 交互パターン | 深堀り検出に使える |

## アーキテクチャ方針

```
[検知層]           [記録層]            [レポート層]
JSONL (tail)  →  violations.jsonl  →  自作 exporter
  ↓                                     ↓
PostToolUse hook                       Markdown (匿名化済)
  ↓                                     ↓
signal aggregator                      GitHub Issue貼付
  ↓                                     ↓
score > threshold → warn/block         人間レビュー
```

## Markdown 出力フォーマット（指摘UIの逆算）

```markdown
# Attention Hijack Report — <session-id>

## Summary
- Session: <session-id>
- Detected: N events
- Score: X.X / 10

## Events

### Event #1 [JSONL line 127, 2026-04-15T01:23:45Z]
**Type**: サブスレッド深堀り
**Score**: 0.82

**Before (line 120)**:
> [ユーザー発言: 本来タスクの文脈]

**Hijack (line 127)**:
> [ユーザー発言: 脇道に入った質問]

**Evidence**:
- S1 semantic distance: 0.73 (threshold 0.5)
- S6 token increase: +15k in 3 turns
- S2 tool chain shift: filesystem → web_fetch

**Suggestion**: 元タスクに戻すか、サブタスクとして Issue 化を提案
```

**設計意図**：
- JSONL の行番号・timestamp を**引用可能な形で保持** → 事後検証が再現可能
- 匿名化後もイベント構造は保持 → 他者共有時も評価軸がブレない
- 各シグナルの数値を表示 → 閾値調整のフィードバックループを作れる

## Phase 構成（Epic サブ issue）

| Phase | Issue | 主成果物 |
|---|---|---|
| 1 | 調査 | operational definition 確定、類似研究レビュー、既存P0/P1/P2との関係整理 |
| 2 | 設計 | 検知アルゴリズム、閾値方針、Markdown仕様確定 |
| 3 | テスト設計 | 陽性/陰性サンプル収集、評価指標（precision/recall/F1） |
| 4 | AC定義 | 決定的検証コマンド、PASS条件、結果レポート形式 |
| 5 | 実装 | Phase 1-4 の成果物に沿って実装。AC全PASS で完了 |

## 未解決論点

- 「タスク境界」をどう機械的に判定するか（S4 TaskCreate 未記録の現状）
- ブロッキング vs 指摘のみ、の境界線
- 閾値チューニングのフィードバックループ（どこで測定、誰が調整）
- マルチエージェント（Codex/Gemini）へ展開する際のスキーマ正規化層
