"""Shared utilities for session title management."""

import os
import subprocess
from pathlib import Path

TITLES_DIR = Path.home() / ".claude" / "session-titles"


def read_title(session_id: str) -> tuple[str | None, str | None]:
    """Read title and source from title file. Returns (title, source) or (None, None)."""
    path = TITLES_DIR / f"{session_id}.txt"
    try:
        lines = path.read_text().splitlines()
        title = lines[0] if len(lines) > 0 else None
        source = lines[1] if len(lines) > 1 else None
        return title, source
    except (FileNotFoundError, IndexError):
        return None, None


def write_title(session_id: str, title: str, source: str) -> None:
    """Write title and source to title file."""
    TITLES_DIR.mkdir(parents=True, exist_ok=True)
    path = TITLES_DIR / f"{session_id}.txt"
    path.write_text(f"{title}\n{source}\n")


def set_iterm2_tab(title: str) -> None:
    """Set iTerm2 tab title via /dev/tty to bypass stdout capture."""
    try:
        with open("/dev/tty", "w") as tty:
            tty.write(f"\033]1;{title}\007")
    except OSError:
        pass


def get_branch_name(cwd: str | None = None) -> str | None:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=3,
            cwd=cwd,
        )
        branch = result.stdout.strip()
        return branch if branch else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
