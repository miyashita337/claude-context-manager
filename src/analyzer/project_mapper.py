from __future__ import annotations

import os
from pathlib import Path


class ProjectMapper:
    """Map ccusage sessionIds and JSONL directory names to project names."""

    WORKTREE_SEPARATOR = "--claude-worktrees-"

    def __init__(
        self,
        username: str | None = None,
        projects_dir: Path | None = None,
    ) -> None:
        self.username = username or os.environ.get("USER", "unknown")
        self.projects_dir = projects_dir or Path.home() / ".claude" / "projects"
        self._prefix = f"-Users-{self.username}-"

    def extract_project_name(self, session_id: str) -> str:
        """Extract human-readable project name from sessionId.
        Handles worktree sessions by mapping to parent project."""
        name = session_id
        if self.WORKTREE_SEPARATOR in name:
            name = name.split(self.WORKTREE_SEPARATOR)[0]
        if name == f"-Users-{self.username}":
            return "home"
        if name.startswith(self._prefix):
            return name[len(self._prefix) :]
        return name

    def list_project_dirs(self) -> list[Path]:
        """List project directories, excluding non-user dirs."""
        if not self.projects_dir.is_dir():
            return []
        return [
            d
            for d in sorted(self.projects_dir.iterdir())
            if d.is_dir() and d.name.startswith(self._prefix)
        ]

    def group_by_parent(self, session_ids: list[str]) -> dict[str, list[str]]:
        """Group session IDs by parent project name."""
        groups: dict[str, list[str]] = {}
        for sid in session_ids:
            parent = self.extract_project_name(sid)
            groups.setdefault(parent, []).append(sid)
        return groups
