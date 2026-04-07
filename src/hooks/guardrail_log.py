#!/usr/bin/env python3
"""Guardrail violation JSONL logger with size-based rotation.

Writes violations to ~/.claude/guardrails/violations.jsonl.
Rotates to violations-YYYYMMDD-HHMMSS.jsonl when > 10MB.
Fail-open: all errors are swallowed so hooks never break.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

GUARDRAIL_DIR = Path.home() / ".claude" / "guardrails"
VIOLATIONS_FILE = GUARDRAIL_DIR / "violations.jsonl"
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def _rotate_if_needed(path: Path, max_size: int | None = None) -> None:
    if max_size is None:
        max_size = MAX_SIZE_BYTES
    try:
        if path.exists() and path.stat().st_size >= max_size:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            rotated = path.with_name(f"violations-{ts}.jsonl")
            path.rename(rotated)
    except OSError:
        pass


def write_violation(
    rule_id: str,
    severity: str,
    ctx: dict[str, Any],
    *,
    session_id: str = "unknown",
    project: str = "unknown",
    action: str = "logged",
    path: Path = VIOLATIONS_FILE,
) -> bool:
    """Append a violation record to the JSONL file.

    Returns True on success, False on any error (fail-open).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed(path)
        record = {
            "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
            "session_id": session_id,
            "project": project,
            "rule_id": rule_id,
            "severity": severity,
            "ctx": ctx,
            "action": action,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False
