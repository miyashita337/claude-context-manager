#!/usr/bin/env python3
"""StatusLine script: Display session title in Claude Code status bar."""

import json
import os
import sys

# Allow importing sibling module
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from session_title_utils import get_branch_name, read_title, set_iterm2_tab


def main():
    data = json.load(sys.stdin)
    session_id = data.get("session_id", "")
    cwd = data.get("cwd", "")
    model = data.get("model", {})
    model_name = model.get("display_name", "?") if isinstance(model, dict) else "?"
    ctx = data.get("context_window", {})
    used_pct = ctx.get("used_percentage")
    pct_str = f"{used_pct}%" if used_pct is not None else "..."

    # Read title
    title = None
    if session_id:
        title, _ = read_title(session_id)

    # Fallback: branch name or directory name
    if not title:
        title = get_branch_name(cwd) or os.path.basename(cwd or "")

    # Refresh iTerm2 tab title on every statusline update (ensures persistence)
    if title:
        set_iterm2_tab(title)

    # Output status line
    print(f"[{title}] | {model_name} | {pct_str} ctx")


if __name__ == "__main__":
    main()
