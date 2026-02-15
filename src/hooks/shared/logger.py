#!/usr/bin/env python3
"""Logging utilities for Claude Context Manager hooks."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Import from config module (avoid relative imports for hook compatibility)
try:
    from .config import TMP_DIR, ensure_directories, estimate_tokens
except ImportError:
    from config import TMP_DIR, ensure_directories, estimate_tokens


class SessionLogger:
    """Manages logging of session entries to temporary JSON files."""

    def __init__(self, session_id: str):
        """Initialize logger for a specific session."""
        self.session_id = session_id
        ensure_directories()
        self.log_file = TMP_DIR / f'session-{session_id}.json'

    def add_entry(self, entry_type: str, content: str, **kwargs) -> None:
        """Add a log entry to the session file (JSON Lines format)."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': entry_type,
            'content': content,
            'tokens_estimate': estimate_tokens(content),
            **kwargs
        }

        # Append to file in JSON Lines format (one JSON per line)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def _load_logs(self) -> List[Dict[str, Any]]:
        """Load existing logs from file (JSON Lines format)."""
        if not self.log_file.exists():
            return []

        logs = []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    logs.append(json.loads(line))
        return logs

    def _save_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Save logs to file."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics."""
        logs = self._load_logs()

        if not logs:
            return {
                'total_tokens': 0,
                'user_tokens': 0,
                'assistant_tokens': 0,
                'entry_count': 0
            }

        user_tokens = sum(
            log['tokens_estimate']
            for log in logs
            if log['type'] == 'user'
        )

        assistant_tokens = sum(
            log['tokens_estimate']
            for log in logs
            if log['type'] == 'assistant'
        )

        return {
            'total_tokens': user_tokens + assistant_tokens,
            'user_tokens': user_tokens,
            'assistant_tokens': assistant_tokens,
            'entry_count': len(logs)
        }
