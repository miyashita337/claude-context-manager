# Context Check - コンテキスト効率分析

引数: `/context-check` （引数なし、現在のセッションを分析）

## 実行手順

### Step 1: セッションtranscript取得

最新のセッションJSONLを特定する:
```bash
TRANSCRIPT=$(ls -t ~/.claude/sessions/*.jsonl 2>/dev/null | head -1)
echo "Transcript: $TRANSCRIPT"
```

### Step 2: ボトルネック分析

engine.pyでセッションを分析する:
```bash
cd $CLAUDE_PROJECT_DIR
python3 -c "
import json, sys
sys.path.insert(0, '.')
sys.path.insert(0, '.claude/analytics')
from engine import analyze_bottlenecks
events = []
with open('$TRANSCRIPT') as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
result = analyze_bottlenecks(events)
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

### Step 3: 質問密度計算

ユーザーメッセージの質問密度を計算する:
```bash
python3 -c "
import json
events = []
with open('$TRANSCRIPT') as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
user_msgs = [e for e in events if e.get('type') == 'user']
q_counts = []
for e in user_msgs:
    content = e.get('message', {}).get('content', '')
    if isinstance(content, list):
        text = ' '.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
    else:
        text = str(content)
    q_counts.append(text.count('\uff1f') + text.count('?'))
avg = sum(q_counts) / len(q_counts) if q_counts else 0
print(f'User messages: {len(q_counts)}')
print(f'Avg questions/msg: {avg:.2f}')
print(f'Total questions: {sum(q_counts)}')
"
```

### Step 4: レポート生成

Step 2, 3 の結果を以下のフォーマットで出力する:

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
- [Anti-patterns](.claude/skills/antipatterns/SKILL.md) - AP-1〜AP-6
- [Workflow Guide](.claude/docs/workflow-guide.md) - 改善手法
