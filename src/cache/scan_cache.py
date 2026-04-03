from __future__ import annotations

import json
from pathlib import Path


class ScanCache:
    """Track file mtimes to enable incremental scanning."""

    def __init__(self, cache_file: Path) -> None:
        self.cache_file = cache_file
        self._entries: dict[str, float] = {}
        self._current: dict[str, float] = {}
        if cache_file.is_file():
            with open(cache_file) as f:
                self._entries = json.load(f)

    def get_changed_files(self, directory: Path, pattern: str) -> list[Path]:
        """Return files that are new or modified since last scan."""
        changed: list[Path] = []
        for filepath in sorted(directory.glob(pattern)):
            if not filepath.is_file():
                continue
            mtime = filepath.stat().st_mtime
            key = str(filepath)
            self._current[key] = mtime
            if key not in self._entries or self._entries[key] < mtime:
                changed.append(filepath)
        return changed

    def save(self) -> None:
        """Persist current scan state."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self._current, f)
