---
name: context-check
description: Analyze current session context efficiency in real-time
tools: Bash, Read, Grep
model: sonnet
---

# /context-check - コンテキスト効率分析

## 概要
現在のセッションのコンテキスト効率をリアルタイムで分析し、改善提案を行う。

## ワークフロー

### Step 1: セッションtranscript取得
```bash
# 最新のセッションJSONLを特定
TRANSCRIPT=$(ls -t ~/.claude/sessions/*.jsonl 2>/dev/null | head -1)
```

### Step 2: メトリクス計算
- トークン使用量（total, user, assistant）
- 質問密度（疑問符/メッセージ平均）
- 散弾イベント数

### Step 3: ボトルネック分析
```bash
cd $CLAUDE_PROJECT_DIR
python3 -c "
import json, sys
sys.path.insert(0, '.')
from .claude.analytics.engine import analyze_bottlenecks
events = [json.loads(l) for l in open('$TRANSCRIPT') if l.strip()]
result = analyze_bottlenecks(events)
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

### Step 4: レポート生成

出力フォーマット:
```
Context Efficiency Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Session tokens: XX,XXX (OK/Warning/Critical)
  - OK: <100K | Warning: 100K-167K | Critical: >167K
- Question density: X.X/msg
  - OK: <2.5 | Warning: 2.5-3.0 | Critical: >3.0
- Scatter events: N detected
- Bottleneck score: XX/100
  - OK: <30 | Warning: 30-60 | Critical: >60

Recommendations:
- [改善提案をスコアに基づいて生成]

未整理の質問: N件
- [issue化されていない独立した質問をリスト]
- → issue化を提案（gh issue create）
```

## 判定基準

| メトリクス | OK | Warning | Critical |
|-----------|-----|---------|----------|
| Session tokens | <100K | 100K-167K | >167K |
| Question density | <2.5 | 2.5-3.0 | >3.0 |
| Bottleneck score | <30 | 30-60 | >60 |

## 参考
- [Anti-patterns](../antipatterns/SKILL.md) - AP-1〜AP-6
- [Workflow Guide](../../docs/workflow-guide.md) - 改善手法
