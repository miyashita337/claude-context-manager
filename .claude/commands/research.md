---
name: "research"
description: "Perform web research with citations using ChatGPT or Gemini"
author: "Claude AI Assistant"
version: "2.0"
---

# Web Research Tool (Multi-Model)

Performs comprehensive web research on a topic using **ChatGPT** or **Gemini** and saves structured results with citations.

```bash
# Parse arguments
QUERY=""
MODEL="openai"
GROUNDING_FLAG=""

# Parse all arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --grounding)
            GROUNDING_FLAG="--grounding"
            shift
            ;;
        *)
            QUERY="$QUERY $1"
            shift
            ;;
    esac
done

# Trim leading/trailing spaces
QUERY=$(echo "$QUERY" | xargs)

if [ -z "$QUERY" ]; then
    echo "❌ **Usage:** /research <topic> [--model openai|gemini] [--grounding]"
    echo ""
    echo "**Examples:**"
    echo "  /research TypeScript generics --model openai"
    echo "  /research 量子コンピュータの市場規模 --model gemini --grounding"
    echo ""
    echo "**Models:**"
    echo "  openai  - ChatGPT (knowledge base only)"
    echo "  gemini  - Gemini with optional Google Search grounding"
    exit 1
fi

echo "🔍 **Researching:** $QUERY"
echo "🤖 **Model:** $MODEL"
if [ -n "$GROUNDING_FLAG" ]; then
    echo "🌐 **Grounding:** Enabled (Google Search)"
fi
echo ""

# Execute research tool (claude-context-managerプロジェクト用パス)
RESEARCH_OUTPUT=$(node /Users/harieshokunin/claude-context-manager/mcp-chatgpt-server/build/cli/research.js "$QUERY" --model "$MODEL" $GROUNDING_FLAG 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "$RESEARCH_OUTPUT"
else
    echo "❌ **Research Failed**"
    echo ""
    echo "$RESEARCH_OUTPUT"
    exit $EXIT_CODE
fi
```

---

## Usage

`/research <topic> [--model openai|gemini] [--grounding]`

### Basic Examples
- `/research TypeScript generics`
- `/research LoRA学習の市場規模 --model gemini`
- `/research React vs Vue performance 2026 --model gemini --grounding`

### Model Options
- `--model openai` (default): ChatGPT knowledge base
- `--model gemini`: Gemini knowledge base
- `--grounding`: Enable Google Search (Gemini only)

## What this does

1. 🔍 Executes comprehensive research via ChatGPT or Gemini API
2. 📄 Generates structured markdown with:
   - Key findings with evidence
   - Source citations (when available from grounding)
   - Reliability scores for information
3. 💾 Saves to `~/.claude/research/YYYY-MM-DD_topic.md`
4. 📊 Shows model, token usage, and file location

## Models Comparison

| Feature | ChatGPT (OpenAI) | Gemini | Gemini + Grounding |
|---------|------------------|--------|-------------------|
| Knowledge cutoff | 2023-10 | 2024-08 | Real-time |
| Web search | ❌ | ❌ | ✅ (Google Search) |
| Speed | Fast | Very fast | Medium |
| Cost | Low | Very low | Medium |

## Output Format

The research results are saved in structured markdown:

```markdown
# 調査結果: [Topic]

## メタ情報
- 調査日時: ...
- 調査ツール: ChatGPT/Gemini + Knowledge Base
- トークン使用: XXX tokens

## 主要な発見

### 1. [Finding Title]
- **主張**: [Claim]
- **根拠**: [Evidence]
- **出典**: [Sources if available]
- **信頼性**: ⭐⭐⭐⭐ (4/5)

## 参考文献
...
```

## Requirements

- **For ChatGPT**: `OPENAI_API_KEY` in `mcp-chatgpt-server/.env`
- **For Gemini**: `GEMINI_API_KEY` in `mcp-chatgpt-server/.env`
- Research tool built at `/Users/harieshokunin/claude-context-manager/mcp-chatgpt-server/build/cli/research.js`

## Notes

- Research results are saved to `~/.claude/research/` for reuse
- Token usage is displayed for cost tracking
- Files are automatically named with date and topic
- **Grounding** enables real-time Google Search (Gemini only)

## Troubleshooting

**Error: "OPENAI_API_KEY not set"**
- Set environment variable: `export OPENAI_API_KEY="sk-proj-..."`
- Or add to `mcp-chatgpt-server/.env`

**Error: "GEMINI_API_KEY not set"**
- Set environment variable: `export GEMINI_API_KEY="..."`
- Or add to `mcp-chatgpt-server/.env`

**Error: "research.js not found"**
- Build the project: `cd mcp-chatgpt-server && npm run build`

## Parallel Execution Example

Run multiple research queries in parallel:

```bash
/research "TypeScript latest features" --model openai &
/research "TypeScript latest features" --model gemini --grounding &
wait
```
