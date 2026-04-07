#!/usr/bin/env python3
"""Rule scanner engine for guardrail violations (R-001 to R-007).

Loads YAML rule definitions from ./rules/ and evaluates them against
Claude Code hook events. warn-only: never blocks, always returns matches.
Fail-open on YAML errors (rule is skipped, scan continues).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

RULES_DIR = Path(__file__).parent / "rules"


@dataclass
class Rule:
    id: str
    name: str
    severity: str
    event: str
    tools: list[str]
    file_regex: re.Pattern[str] | None
    command_regex: re.Pattern[str] | None
    absent_in_history: str | None
    staged_diff_regex: re.Pattern[str] | None
    message: str


def load_rules(rules_dir: Path = RULES_DIR) -> list[Rule]:
    """Load all rule YAML files. Invalid YAML is skipped (fail-open)."""
    rules: list[Rule] = []
    if not rules_dir.exists():
        return rules
    for path in sorted(rules_dir.glob("*.yml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            trigger = data.get("trigger", {}) or {}
            match = data.get("match", {}) or {}
            file_re = match.get("file_path_regex")
            cmd_re = match.get("command_regex")
            staged_re = match.get("staged_diff_regex")
            rules.append(
                Rule(
                    id=str(data.get("id", path.stem)),
                    name=str(data.get("name", "")),
                    severity=str(data.get("severity", "warn")),
                    event=str(trigger.get("event", "")),
                    tools=list(trigger.get("tool", []) or []),
                    file_regex=re.compile(file_re) if file_re else None,
                    command_regex=re.compile(cmd_re) if cmd_re else None,
                    absent_in_history=match.get("absent_in_history"),
                    staged_diff_regex=(re.compile(staged_re) if staged_re else None),
                    message=str(data.get("message", "")),
                )
            )
        except (OSError, yaml.YAMLError, re.error, TypeError):
            continue
    return rules


def _get_staged_diff() -> str:
    """Return git diff --cached output, or empty string on any failure."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def scan_post_tool_use(
    tool_name: str,
    tool_input: dict[str, Any],
    rules: list[Rule],
    *,
    recent_commands: list[str] | None = None,
    staged_diff_provider: Any = _get_staged_diff,
) -> list[tuple[Rule, dict[str, Any]]]:
    """Return list of (rule, ctx) for rules that match this event.

    recent_commands: list of recent Bash commands for absent_in_history check.
    staged_diff_provider: callable returning staged diff text (for R-006).
    """
    matches: list[tuple[Rule, dict[str, Any]]] = []
    recent = recent_commands or []

    for rule in rules:
        if rule.event != "post_tool_use":
            continue
        if rule.tools and tool_name not in rule.tools:
            continue

        # File-based match (R-001)
        if rule.file_regex is not None:
            file_path = str(tool_input.get("file_path", ""))
            if file_path and rule.file_regex.search(file_path):
                matches.append((rule, {"tool": tool_name, "file_path": file_path}))
            continue

        # Command-based match (R-002, R-004, R-005, R-006, R-007)
        if rule.command_regex is not None:
            command = str(tool_input.get("command", ""))
            if not command or not rule.command_regex.search(command):
                continue

            # absent_in_history: skip if history contains the marker
            if rule.absent_in_history:
                if any(rule.absent_in_history in c for c in recent):
                    continue

            # staged_diff_regex: require match in staged diff
            if rule.staged_diff_regex is not None:
                diff_text = ""
                try:
                    diff_text = staged_diff_provider()
                except Exception:  # pragma: no cover - fail-open
                    diff_text = ""
                if not diff_text or not rule.staged_diff_regex.search(diff_text):
                    continue

            matches.append((rule, {"tool": tool_name, "command": command}))

    return matches


def scan_stop(
    transcript_lines: list[str],
    rules: list[Rule],
    *,
    error_loop_threshold: int = 3,
) -> list[tuple[Rule, dict[str, Any]]]:
    """Detect stop-time violations (R-003 error loop).

    transcript_lines: recent Bash tool_result lines from session.
    """
    matches: list[tuple[Rule, dict[str, Any]]] = []
    error_pattern = re.compile(r"(error|panic|exception|fatal|failed)", re.IGNORECASE)
    counts: dict[str, int] = {}
    for line in transcript_lines:
        stripped = line.strip()
        if not stripped or not error_pattern.search(stripped):
            continue
        counts[stripped] = counts.get(stripped, 0) + 1

    for rule in rules:
        if rule.event != "stop" or rule.id != "R-003":
            continue
        for err_line, count in counts.items():
            if count >= error_loop_threshold:
                matches.append(
                    (rule, {"error_excerpt": err_line[:200], "count": count})
                )
                break
    return matches
