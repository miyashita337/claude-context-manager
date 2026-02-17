# Session Review

引数: `/review [SESSION_ID]` ← 省略時は最新セッション

## 実行手順

### Step 1: SESSION_ID を特定する

引数が渡された場合（例: `/review 7d37850d`）はそのIDを使用する。

省略された場合は以下を実行して最新のセッションIDを取得する:
```bash
python3 .claude/analytics/engine.py --sessions 1 --output /tmp/review-latest.json 2>/dev/null && \
  python3 -c "import json; d=json.load(open('/tmp/review-latest.json')); print(d['sessions'][0]['session_id'])"
```

### Step 2: キャッシュを確認する

`~/.claude/reviews/.cache/{SESSION_ID}.json` が存在するか確認する。

存在する場合 → そのJSONを読み込む。
存在しない場合 → 以下を実行してデータを生成する:
```bash
python3 .claude/analytics/engine.py \
  --session-id {SESSION_ID} \
  --output ~/.claude/reviews/.cache/{SESSION_ID}.json
```

### Step 3: AgentTeam を起動して並行分析する

TeamCreate で "session-review" チームを作成し、以下の2エージェントを **同一メッセージ内で並行起動** する（TaskCreate + 複数Taskツール呼び出し）。

---

**data-agent** (Task/general-purpose):

キャッシュJSONを読み込み、以下の **必要フィールドのみ** を抽出する（生JSONを転送しない）:
- 基本情報: session_id, start, end, duration_minutes, total_tokens, total_cost, message_count
- anomalies: [{type, severity, detail, value}]
- bottleneck: bottleneck_score, issue_counts, issues（全件・type/detail/value/msg_indexのみ）, top_wasteful_messages
- tool_counts: 上位10ツール

加えて、`.claude/skills/antipatterns/SKILL.md` を Read して、公式5アンチパターンの照合ルールを確認する。セッションデータと照合し、各パターンの 該当/非該当/N/A と根拠を判定する。

**報告は簡潔に（コンパクトな構造体のみ。生のJSONやログは不要）**。

---

**research-agent** (Task/general-purpose):

`.claude/skills/antipatterns/SKILL.md` を Read して公式5アンチパターン（問題・Fix）を把握する。

WebFetch は基本不要（Skillに最新内容が保存済み）。ただし以下の場合のみ WebSearch を実行する:
- Skill の「最終確認」から30日以上経過している場合
- data-agent の結果で、Skillに記載のない新しいパターンが検出された場合

もし WebSearch を実行する場合は:
- `Claude Code best practices 2026 avoid common pitfalls`
- 上位3件の URL と要点（1-2行）のみ報告（全文転送しない）

**報告形式**: 公式5パターンのサマリー（各パターン3行以内）+ 追加情報（あれば）。

---

### Step 4: 2エージェントの結果を統合してレポートを生成する

以下のテンプレートに従って `~/.claude/reviews/{SESSION_ID_SHORT}-{YYYYMMDD}.md` を Write する:

```markdown
# Session Review: {session_id[:8]}
**日時**: {date} | **Score**: {bottleneck_score}/100 | **Issues**: {issue_count}件 | **コスト**: ${total_cost}

## TL;DR
{3行以内の要約。最大の問題1つと即実践できる推奨1つ}

---

## ⚠️ 公式アンチパターン照合（code.claude.com/docs/en/best-practices）

| パターン | 該当 | 根拠 |
|---------|------|------|
| AP-1: kitchen sink session | ✅/❌ | {具体的な根拠} |
| AP-2: correcting over and over | ✅/❌ | {具体的な根拠} |
| AP-3: over-specified CLAUDE.md | N/A | セッションから判定不可 |
| AP-4: trust-then-verify gap | ✅/❌ | {具体的な根拠} |
| AP-5: infinite exploration | ✅/❌ | {具体的な根拠} |

### 公式 Fix（該当パターンのみ）

**{該当パターン名}**
> {Skill から引用した公式の Fix}
> — [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)

---

## 🔴 検出パターン詳細 ({bottleneck_score}点)

### {issue_type} × {count}件
{各issueのdetail（表またはリスト）}

---

## 📚 追加改善提案

### 🥇 最優先
**問題**: {具体的に何が起きたか}
**推奨**: {具体的なアクション}
**根拠**: [{ソース名}]({URL})

---

## 🔍 レビュー自己診断
**このレビューセッション自体のトークン消費**: {Step 5 で取得}

---

## 参考資料
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [Lost in the Middle (Liu et al. TACL 2024)](https://arxiv.org/abs/2307.03172)
```

### Step 5: セルフチェック → シャットダウン → ユーザー表示

#### 5-1. レビューセッション自体のトークン消費をチェック

以下を実行してこのレビューセッション自体のコストを確認する:
```bash
ccusage session --limit 1 2>/dev/null || echo "ccusage not available"
```

取得した数値をレポートの「レビュー自己診断」欄に記入する。
- **< 30K tokens**: 軽量 ✅
- **30-100K tokens**: 普通（Skill 活用でさらに削減可能）
- **> 100K tokens**: ⚠️ レビュー自体が重い（研究・統合フェーズを見直す）

#### 5-2. チームをシャットダウン

SendMessage で全エージェントに shutdown_request を送る。

#### 5-3. ユーザーに結果を表示

1. 生成されたレポートのパスを表示する
2. TL;DR（3行）を直接表示する
3. **公式アンチパターン照合結果の表** を直接表示する
4. レビューセッション自体のトークン消費を表示する
5. `make analytics` でダッシュボードの Reviews タブに反映されることを案内する
