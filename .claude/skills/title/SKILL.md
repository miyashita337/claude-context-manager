---
name: title
description: Generate or update session title for iTerm2 tab and status line
tools: Bash
model: haiku
---

# /title - Session Title Management

## Usage
- `/title` — AI generates a title from conversation context
- `/title My Custom Title` — Set a specific title manually

## Behavior

1. If an argument is provided, use it as the title directly (source: `manual`)
2. If no argument, generate a concise title (English, max 6 words) from conversation context (source: `manual`)
3. Update the title file and iTerm2 tab:

```bash
TITLE="YOUR_TITLE_HERE"
SESSION_ID="$CLAUDE_SESSION_ID"
printf '\033]1;%s\007' "$TITLE" > /dev/tty 2>/dev/null
mkdir -p ~/.claude/session-titles
printf '%s\nmanual\n' "$TITLE" > ~/.claude/session-titles/${SESSION_ID}.txt
```

4. Confirm the title was set

## Rules
- Title must be concise: max 6 words, English
- Always set source as `manual` (this is a user-initiated override)
- Do not ask for confirmation — just set the title
- If `CLAUDE_SESSION_ID` is not available, read session_id from the most recent title file or skip title file update
