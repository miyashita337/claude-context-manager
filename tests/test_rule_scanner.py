"""Tests for the rule_scanner guardrail engine (R-001..R-007)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "hooks"))

import guardrail_log  # noqa: E402
import rule_scanner  # noqa: E402


@pytest.fixture
def rules():
    return rule_scanner.load_rules(REPO_ROOT / "src" / "hooks" / "rules")


def _ids(matches):
    return [r.id for r, _ in matches]


# -------- load_rules --------


def test_load_rules_loads_all_seven(rules):
    ids = {r.id for r in rules}
    assert {"R-001", "R-002", "R-003", "R-004", "R-005", "R-006", "R-007"} <= ids


def test_load_rules_fail_open_on_bad_yaml(tmp_path):
    (tmp_path / "bad.yml").write_text("::not valid yaml::\n  - [", encoding="utf-8")
    (tmp_path / "good.yml").write_text(
        "id: R-X\nname: x\nseverity: warn\ntrigger:\n  event: post_tool_use\n"
        "  tool: [Bash]\nmatch:\n  command_regex: 'foo'\n",
        encoding="utf-8",
    )
    loaded = rule_scanner.load_rules(tmp_path)
    assert [r.id for r in loaded] == ["R-X"]


# -------- R-001 secrets --------


def test_r001_fires_on_env_file(rules):
    m = rule_scanner.scan_post_tool_use("Read", {"file_path": "/tmp/.env"}, rules)
    assert "R-001" in _ids(m)


def test_r001_skips_normal_file(rules):
    m = rule_scanner.scan_post_tool_use("Read", {"file_path": "/tmp/README.md"}, rules)
    assert "R-001" not in _ids(m)


# -------- R-002 git add wildcard --------


@pytest.mark.parametrize(
    "cmd",
    ["git add .", "git add -A", "git add -u", "git add --all", "git add src/*.py"],
)
def test_r002_fires_on_wildcards(rules, cmd):
    m = rule_scanner.scan_post_tool_use("Bash", {"command": cmd}, rules)
    assert "R-002" in _ids(m)


def test_r002_skips_specific_file(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash", {"command": "git add src/hooks/rule_scanner.py"}, rules
    )
    assert "R-002" not in _ids(m)


def test_r002_false_positive_on_epic_body_text(rules):
    """AC-2: writing Epic body containing 'git add .' text should not fire."""
    m = rule_scanner.scan_post_tool_use(
        "Write",
        {"file_path": "/tmp/epic.md", "content": "禁止: git add ."},
        rules,
    )
    assert "R-002" not in _ids(m)  # Write tool has no command field


# -------- R-003 error loop (stop) --------


def test_r003_fires_on_repeated_errors(rules):
    lines = [
        "panic: runtime error: nil pointer",
        "panic: runtime error: nil pointer",
        "panic: runtime error: nil pointer",
        "some other log",
    ]
    m = rule_scanner.scan_stop(lines, rules)
    assert "R-003" in _ids(m)


def test_r003_skips_single_error(rules):
    m = rule_scanner.scan_stop(["Error: one off"], rules)
    assert "R-003" not in _ids(m)


# -------- R-004 git push without pre-git-check --------


def test_r004_fires_without_history(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash", {"command": "git push origin main"}, rules, recent_commands=[]
    )
    assert "R-004" in _ids(m)


def test_r004_skips_when_history_has_check(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash",
        {"command": "git push origin main"},
        rules,
        recent_commands=["make pre-git-check"],
    )
    assert "R-004" not in _ids(m)


# -------- R-005 git force / no-verify --------


@pytest.mark.parametrize(
    "cmd",
    [
        "git push --force origin main",
        "git commit --no-verify -m x",
        "git push -f origin main",
    ],
)
def test_r005_fires_on_dangerous_flags(rules, cmd):
    m = rule_scanner.scan_post_tool_use("Bash", {"command": cmd}, rules)
    assert "R-005" in _ids(m)


def test_r005_allows_force_with_lease(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash", {"command": "git push --force-with-lease origin main"}, rules
    )
    assert "R-005" not in _ids(m)


# -------- R-006 todo in staged commit --------


def test_r006_fires_when_staged_has_todo(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash",
        {"command": "git commit -m 'wip'"},
        rules,
        recent_commands=["make test-all"],
        staged_diff_provider=lambda: "+def f():\n+    # TODO: fix\n",
    )
    assert "R-006" in _ids(m)


def test_r006_skips_when_no_todo(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash",
        {"command": "git commit -m x"},
        rules,
        recent_commands=["make test-all"],
        staged_diff_provider=lambda: "+ok\n",
    )
    assert "R-006" not in _ids(m)


# -------- R-007 commit without test-all --------


def test_r007_fires_without_history(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash",
        {"command": "git commit -m x"},
        rules,
        recent_commands=[],
        staged_diff_provider=lambda: "",
    )
    assert "R-007" in _ids(m)


def test_r007_skips_when_history_has_tests(rules):
    m = rule_scanner.scan_post_tool_use(
        "Bash",
        {"command": "git commit -m x"},
        rules,
        recent_commands=["make test-all"],
        staged_diff_provider=lambda: "",
    )
    assert "R-007" not in _ids(m)


# -------- guardrail_log --------


def test_write_violation_creates_jsonl(tmp_path):
    path = tmp_path / "v.jsonl"
    ok = guardrail_log.write_violation(
        "R-001",
        "warn",
        {"tool": "Read", "file_path": "/x/.env"},
        session_id="s1",
        project="p1",
        path=path,
    )
    assert ok is True
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["rule_id"] == "R-001"
    assert rec["severity"] == "warn"
    assert rec["ctx"]["file_path"] == "/x/.env"
    assert rec["action"] == "logged"
    assert "ts" in rec


def test_write_violation_rotates_at_threshold(tmp_path):
    path = tmp_path / "v.jsonl"
    # Pre-fill with dummy data
    path.write_text("x" * 50, encoding="utf-8")
    guardrail_log.write_violation(
        "R-001", "warn", {}, path=path, session_id="s", project="p"
    )
    # With max_size hacked via monkey: simulate rotation
    # Instead use internal threshold patch
    import guardrail_log as gl

    old = gl.MAX_SIZE_BYTES
    try:
        gl.MAX_SIZE_BYTES = 10
        gl.write_violation("R-002", "warn", {}, path=path, session_id="s", project="p")
        rotated = list(tmp_path.glob("violations-*.jsonl"))
        assert len(rotated) == 1
    finally:
        gl.MAX_SIZE_BYTES = old


def test_write_violation_fail_open_on_bad_path(tmp_path):
    # Non-serializable ctx (set) → TypeError → returns False, no raise
    path = tmp_path / "v.jsonl"
    ok = guardrail_log.write_violation("R-001", "warn", {"bad": {1, 2}}, path=path)
    assert ok is False
