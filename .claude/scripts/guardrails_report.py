#!/usr/bin/env python3
"""Aggregate and report guardrail violations from violations.jsonl.

Used by:
- .claude/hooks/session-start-guardrails.sh (--summary)
- .claude/skills/guardrails-report (--report)

Fail-open: any error → exit 0 with no output.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

GUARDRAIL_DIR = Path.home() / ".claude" / "guardrails"
VIOLATIONS_FILE = GUARDRAIL_DIR / "violations.jsonl"
ARCHIVE_DIR = GUARDRAIL_DIR / "archive"

# Known rules (R-001..R-007). Used so summary lists all rules even when 0.
KNOWN_RULES: list[tuple[str, str, str]] = [
    ("R-001", "secrets", "block"),
    ("R-002", "git-add-wild", "warn"),
    ("R-003", "error-loop", "warn"),
    ("R-004", "pre-git-check", "warn"),
    ("R-005", "git-force", "block"),
    ("R-006", "todo-commit", "warn"),
    ("R-007", "test-skip", "warn"),
]
RULE_NAME = {rid: name for rid, name, _ in KNOWN_RULES}
RULE_SEV = {rid: sev for rid, _, sev in KNOWN_RULES}


def _parse_ts(s: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iter_records(path: Path) -> Iterable[dict]:
    if not path.exists():
        return
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def _iter_archive(archive_dir: Path) -> Iterable[dict]:
    if not archive_dir.exists():
        return
    try:
        files = sorted(archive_dir.glob("violations-*.jsonl.gz"))
    except OSError:
        return
    for fp in files:
        try:
            with gzip.open(fp, "rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue


def _current_project() -> str:
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(cwd).name


def load(
    days: int,
    project: str | None,
    rule: str | None,
    *,
    include_archive: bool = False,
    src: Path | None = None,
    archive_dir: Path | None = None,
    now: datetime | None = None,
) -> list[dict]:
    if src is None:
        src = VIOLATIONS_FILE
    if archive_dir is None:
        archive_dir = ARCHIVE_DIR
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    out: list[dict] = []
    sources: list[Iterable[dict]] = [_iter_records(src)]
    if include_archive:
        sources.append(_iter_archive(archive_dir))
    for it in sources:
        for rec in it:
            ts = _parse_ts(rec.get("ts", ""))
            if ts is None or ts < cutoff:
                continue
            if project and project != "*" and rec.get("project") != project:
                continue
            if rule and rec.get("rule_id") != rule:
                continue
            out.append(rec)
    return out


def cmd_summary(args: argparse.Namespace) -> int:
    project = None if args.all_projects else (args.project or _current_project())
    records = load(args.days, project, None)
    if not records:
        return 0
    counts: Counter[str] = Counter(r.get("rule_id", "?") for r in records)
    proj_label = "all projects" if args.all_projects else (project or "current")
    lines = [f"[Guardrails] Last {args.days} days in {proj_label}:"]
    threshold = args.warn_threshold
    for rid, name, _ in KNOWN_RULES:
        n = counts.get(rid, 0)
        marker = "  ← 要注意" if n >= threshold and n > 0 else ""
        lines.append(f"  {rid} {name:<14} {n}{marker}")
    extras = sorted(set(counts) - set(RULE_NAME))
    for rid in extras:
        n = counts[rid]
        marker = "  ← 要注意" if n >= threshold else ""
        lines.append(f"  {rid} (unknown)     {n}{marker}")
    lines.append("")
    lines.append("詳細: /guardrails:report")
    print("\n".join(lines))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    project = None if args.all_projects else (args.project or _current_project())
    records = load(args.days, project, args.rule, include_archive=True)
    proj_label = "all projects" if args.all_projects else (project or "current")
    print(f"## Guardrails Report (last {args.days} days)")
    print(f"Project: {proj_label}")
    print()

    if not records:
        print("No violations.")
        return 0

    # Trend: compare to previous window of same length
    prev_records = load(
        args.days * 2,
        project,
        args.rule,
        include_archive=True,
    )
    cutoff_recent = datetime.now(timezone.utc) - timedelta(days=args.days)
    prev_only = [
        r
        for r in prev_records
        if (_parse_ts(r.get("ts", "")) or datetime.now(timezone.utc)) < cutoff_recent
    ]
    prev_counts: Counter[str] = Counter(r.get("rule_id", "?") for r in prev_only)

    counts: Counter[str] = Counter(r.get("rule_id", "?") for r in records)

    print("### Summary")
    print("| Rule | Count | Severity | Trend |")
    print("|------|-------|----------|-------|")
    for rid, _, sev in KNOWN_RULES:
        n = counts.get(rid, 0)
        if n == 0 and not args.rule:
            continue
        if args.rule and rid != args.rule:
            continue
        prev = prev_counts.get(rid, 0)
        trend = _trend(n, prev)
        print(f"| {rid} | {n} | {sev} | {trend} |")
    print()

    if args.rule:
        print(f"### Top violations ({args.rule})")
        recs_sorted = sorted(
            records,
            key=lambda r: _parse_ts(r.get("ts", ""))
            or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        for i, rec in enumerate(recs_sorted[:20], 1):
            ts = rec.get("ts", "?")
            ctx = rec.get("ctx", {})
            ctx_str = json.dumps(ctx, ensure_ascii=False) if ctx else ""
            print(f"{i}. {ts} — {ctx_str}")
        print()

    print("### Recommendations")
    by_rule = defaultdict(int)
    for r in records:
        by_rule[r.get("rule_id", "?")] += 1
    recs = []
    for rid, n in sorted(by_rule.items(), key=lambda x: -x[1]):
        if n >= 5 and rid in RULE_NAME:
            recs.append(
                f"- {rid} ({RULE_NAME[rid]}) が {n}件発生。"
                "再発防止のため自動チェック強化を検討。"
            )
    if not recs:
        recs.append("- 大きな問題は検出されていません。")
    print("\n".join(recs))
    return 0


def _trend(curr: int, prev: int) -> str:
    if prev == 0 and curr == 0:
        return "→"
    if prev == 0:
        return "↑↑" if curr >= 3 else "↑"
    ratio = curr / prev
    if ratio >= 2.0:
        return "↑↑"
    if ratio >= 1.2:
        return "↑"
    if ratio <= 0.5:
        return "↓↓"
    if ratio <= 0.8:
        return "↓"
    return "→"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="guardrails_report")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("summary", help="SessionStart-style summary")
    s.add_argument("--days", type=int, default=7)
    s.add_argument("--project", default=None)
    s.add_argument("--all-projects", action="store_true")
    s.add_argument("--warn-threshold", type=int, default=2)
    s.set_defaults(func=cmd_summary)

    r = sub.add_parser("report", help="/guardrails:report markdown report")
    r.add_argument("--days", type=int, default=7)
    r.add_argument("--rule", default=None)
    r.add_argument("--project", default=None)
    r.add_argument("--all-projects", action="store_true")
    r.set_defaults(func=cmd_report)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
