from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SessionStats:
    """Aggregated statistics from a single JSONL session file."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    models_used: set[str] = field(default_factory=set)
    user_message_count: int = 0
    assistant_message_count: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )


class JsonlParser:
    """Stream-parse Claude Code JSONL session files."""

    def parse_file(self, filepath: Path) -> SessionStats:
        """Parse a single JSONL file and return aggregated stats."""
        stats = SessionStats()
        if not filepath.is_file():
            return stats
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    logger.debug("Skipping malformed line in %s", filepath)
                    continue
                record_type = record.get("type", "")
                if record_type == "assistant":
                    self._process_assistant(record, stats)
                elif record_type == "user":
                    stats.user_message_count += 1
        return stats

    def _process_assistant(self, record: dict, stats: SessionStats) -> None:
        """Extract token usage from an assistant record."""
        stats.assistant_message_count += 1
        message = record.get("message", {})
        if not isinstance(message, dict):
            return
        model = message.get("model", "")
        if model:
            stats.models_used.add(model)
        usage = message.get("usage", {})
        if not isinstance(usage, dict):
            return
        stats.input_tokens += usage.get("input_tokens", 0)
        stats.output_tokens += usage.get("output_tokens", 0)
        stats.cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
        stats.cache_read_tokens += usage.get("cache_read_input_tokens", 0)
