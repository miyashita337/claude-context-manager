#!/usr/bin/env python3
"""Archive violations.jsonl entries older than 30 days.

Moves old entries into ~/.claude/guardrails/archive/violations-YYYY-MM.jsonl.gz
and rewrites the source file with only recent entries. Fail-open.
"""

from __future__ import annotations

import contextlib
import fcntl
import gzip
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

GUARDRAIL_DIR = Path.home() / ".claude" / "guardrails"
VIOLATIONS_FILE = GUARDRAIL_DIR / "violations.jsonl"
ARCHIVE_DIR = GUARDRAIL_DIR / "archive"
RETENTION_DAYS = 30


@contextlib.contextmanager
def _exclusive_lock(target: Path):
    """Acquire an exclusive cross-process lock on target.lock.

    Shared with src/hooks/guardrail_log.py writer to prevent lost appends
    while the archiver rewrites the source file. Fail-open: yields even if
    locking is unavailable.
    """
    lock_path = target.with_suffix(target.suffix + ".lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        yield
        return
    fh = None
    try:
        fh = open(lock_path, "w")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except OSError:
            pass
        yield
    except OSError:
        yield
    finally:
        if fh is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            fh.close()


def _parse_ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def archive(
    src: Path = VIOLATIONS_FILE,
    archive_dir: Path = ARCHIVE_DIR,
    retention_days: int = RETENTION_DAYS,
    now: datetime | None = None,
) -> tuple[int, int]:
    """Return (archived_count, kept_count). Fail-open: returns (0,0) on error.

    Holds an exclusive lock on src for the entire read/process/write cycle so
    that concurrent appenders (guardrail_log.py) don't lose lines.
    """
    if not src.exists():
        return (0, 0)
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days)

    with _exclusive_lock(src):
        kept: list[str] = []
        by_month: dict[str, list[str]] = {}
        try:
            with open(src, encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        kept.append(line)
                        continue
                    ts = _parse_ts(rec.get("ts", ""))
                    if ts is None:
                        kept.append(line)
                        continue
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        kept.append(line)
                    else:
                        key = ts.strftime("%Y-%m")
                        by_month.setdefault(key, []).append(line)
        except OSError:
            return (0, 0)

        archived = 0
        failed_lines: list[str] = []
        if by_month:
            try:
                archive_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                return (0, len(kept))
            for month, lines in by_month.items():
                out = archive_dir / f"violations-{month}.jsonl.gz"
                try:
                    with gzip.open(out, "at", encoding="utf-8") as gz:
                        for line in lines:
                            gz.write(line + "\n")
                    archived += len(lines)
                except OSError:
                    # Re-add failed-month lines so they are not lost.
                    failed_lines.extend(lines)

        if archived > 0:
            try:
                tmp = src.with_suffix(".jsonl.tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    for line in [*kept, *failed_lines]:
                        f.write(line + "\n")
                tmp.replace(src)
            except OSError:
                pass

        return (archived, len(kept) + len(failed_lines))


def main() -> int:
    archived, kept = archive()
    if archived > 0:
        print(f"[archive] {archived} entries archived, {kept} kept", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
