#!/usr/bin/env python3
"""UserPromptSubmit hook: Inject AI title generation after 2+ user messages."""

import json
import sys

# Allow importing sibling module
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from session_title_utils import read_title


def count_user_messages(transcript_path: str) -> int:
    """Count user messages in transcript JSONL file."""
    count = 0
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "human":
                        count += 1
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, PermissionError):
        pass
    return count


def main():
    data = json.load(sys.stdin)
    session_id = data.get("session_id", "")
    transcript_path = data.get("transcript_path", "")

    if not session_id:
        return

    # Fast path: already has AI or manual title
    _, source = read_title(session_id)
    if source in ("ai", "manual"):
        return

    # Check user message count
    if not transcript_path:
        return

    user_msg_count = count_user_messages(transcript_path)
    if user_msg_count < 2:
        return

    # Inject title generation instruction
    instruction = (
        f"[Session Title Request] This session still has a branch-based title. "
        f"Based on the conversation so far, generate a concise session title "
        f"(English, max 6 words) that captures the main topic. Then run this command:\n"
        f"printf '\\033]1;%s\\007' \"YOUR_TITLE\" > /dev/tty 2>/dev/null && "
        f"mkdir -p ~/.claude/session-titles && "
        f"printf '%s\\nai\\n' \"YOUR_TITLE\" > ~/.claude/session-titles/{session_id}.txt\n"
        f"Replace YOUR_TITLE with the generated title. No confirmation needed. "
        f"After setting the title, respond to the user's message normally."
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": instruction,
        }
    }
    json.dump(output, sys.stdout)


if __name__ == "__main__":
    main()
