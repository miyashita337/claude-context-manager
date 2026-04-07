---
name: guardrails-report
description: Display guardrail violations summary from ~/.claude/guardrails/violations.jsonl
global: false
tools: Bash
model: sonnet
---

# /guardrails:report - ガードレール違反レポート

## 概要
Phase 2 で蓄積された `~/.claude/guardrails/violations.jsonl` を集計し、Markdown レポートとして表示します。

## 引数
- `--days N` 集計期間（デフォルト 7）
- `--rule R-XXX` 特定ルールの詳細表示
- `--project NAME` プロジェクト指定（デフォルト カレント）
- `--all-projects` 全プロジェクト集計

## 実行

```bash
python3 "$CLAUDE_PROJECT_DIR/.claude/scripts/guardrails_report.py" report "$@"
```

引数なしの場合は直近7日のサマリーをカレントプロジェクトで表示します。

## 出力例

```
## Guardrails Report (last 7 days)
Project: claude-context-manager

### Summary
| Rule | Count | Severity | Trend |
|------|-------|----------|-------|
| R-002 | 2 | warn | ↑ |
| R-006 | 3 | warn | → |
| R-007 | 5 | warn | ↑↑ |

### Recommendations
- R-007 (test-skip) が 5件発生。再発防止のため自動チェック強化を検討。
```

`--rule R-007` 指定時は該当ルールの直近20件の詳細リストも表示されます。

アーカイブ済み（30日超）のデータも自動的に集計対象に含まれます。
