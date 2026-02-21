---
name: antipatterns
description: Official Claude Code anti-patterns from code.claude.com/docs/en/best-practices. Use for session review anti-pattern matching and /fact-check verification.
---

# Claude Code 公式アンチパターン

**ソース**: https://code.claude.com/docs/en/best-practices#avoid-common-failure-patterns
**最終確認**: 2026-02-18
**更新方法**: `/fact-check "Verify antipatterns still match official docs at code.claude.com/docs/en/best-practices"`

---

## AP-1: The kitchen sink session

**問題**: 1つのタスクを始め、無関係なことを質問し、また最初のタスクに戻る。コンテキストが無関係な情報で溢れる。

**公式 Fix**: `/clear` between unrelated tasks.

**セッションデータ照合ルール**:
- `anomalies` に `kitchen_sink` type が存在する → **該当**
- `total_tokens > 167,000` かつ `tool_counts` に多種のツールが混在 → **要確認**

---

## AP-2: Correcting over and over

**問題**: Claude が間違い → 修正 → まだ間違い → 修正を繰り返す。コンテキストが失敗したアプローチで汚染される。

**公式 Fix**: After two failed corrections, `/clear` and write a better initial prompt incorporating what you learned.

**セッションデータ照合ルール**:
- `bottleneck_report.issues` に `tool_loop` が存在し、同一ツールの連続回数 ≥ 3 → **該当**
- 特に Bash が連続している場合は CI エラーループの可能性

---

## AP-3: The over-specified CLAUDE.md

**問題**: CLAUDE.md が長すぎると Claude が半分を無視し、重要なルールが埋もれる。

**公式 Fix**: Ruthlessly prune. "For each line, ask: Would removing this cause Claude to make mistakes? If not, cut it."

**セッションデータ照合ルール**:
- セッションデータ単体では判定不可（CLAUDE.md の内容が必要）→ **N/A**

---

## AP-4: The trust-then-verify gap

**問題**: Claude がもっともらしい実装を出すが、エッジケースを処理していない。検証なしで出荷してしまう。

**公式 Fix**: Always provide verification (tests, scripts, screenshots). "If you can't verify it, don't ship it."

**セッションデータ照合ルール**:
- `tool_counts` に `Bash` がほぼなく、`Edit` / `Write` が多数 → **該当の可能性**
- `tool_counts.Bash` が存在し、pytest / npm test / make test などが実行されていれば → **非該当**

---

## AP-5: The infinite exploration

**問題**: "investigate X" のような曖昧な指示で Claude が数百ファイルを読み込み、コンテキストを消費する。

**公式 Fix**: Scope investigations narrowly, or use subagents so exploration doesn't consume your main context.

**セッションデータ照合ルール**:
- `bottleneck_report.issue_counts.repeated_file_read ≥ 3` → **該当**
- `bottleneck_report.issue_counts.large_tool_result ≥ 3` → **該当**
- `bottleneck_report.issues` に `large_tool_result` で chars > 10,000 のものがある → **該当**

---

## 照合結果テンプレート（review.md 用）

```markdown
| パターン | 該当 | 根拠 |
|---------|------|------|
| AP-1: kitchen sink session | ✅/❌ | {anomaly type or total_tokens} |
| AP-2: correcting over and over | ✅/❌ | {tool_loop count, tool名, msg_indices} |
| AP-3: over-specified CLAUDE.md | N/A | セッションから判定不可 |
| AP-4: trust-then-verify gap | ✅/❌ | {Bash usage or lack thereof} |
| AP-5: infinite exploration | ✅/❌ | {repeated_file_read or large_tool_result count} |
```
