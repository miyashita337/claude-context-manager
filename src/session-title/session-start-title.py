#!/usr/bin/env python3
"""SessionStart hook: Set initial session title from branch name."""

import json
import sys

# Allow importing sibling module
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from session_title_utils import get_branch_name, read_title, set_iterm2_tab, write_title


def main():
    data = json.load(sys.stdin)
    session_id = data.get("session_id", "")
    cwd = data.get("cwd", "")

    if not session_id:
        return

    # Check for existing title (resume case)
    title, source = read_title(session_id)
    if title:
        set_iterm2_tab(title)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    f"[Session Title: {title} (source: {source}) "
                    f"| Session ID: {session_id}]"
                ),
            }
        }
        json.dump(output, sys.stdout)
        return

    # New session: use branch name as initial title
    branch = get_branch_name(cwd)
    title = branch if branch else __import__("os").path.basename(cwd)

    write_title(session_id, title, "branch")
    set_iterm2_tab(title)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                f"[Session Title: {title} (source: branch) "
                f"| Session ID: {session_id}]"
            ),
        }
    }
    json.dump(output, sys.stdout)


if __name__ == "__main__":
    main()
