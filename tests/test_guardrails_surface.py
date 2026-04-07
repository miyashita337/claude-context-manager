"""AC tests for #131 Phase 3: B サーフェス."""

from __future__ import annotations

import gzip
import importlib.util
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / ".claude" / "scripts"
HOOK_SH = ROOT / ".claude" / "hooks" / "session-start-guardrails.sh"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


report = _load("guardrails_report")
archive_mod = _load("archive_violations")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _rec(
    rule_id: str, days_ago: float = 0, project: str = "claude-context-manager"
) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "ts": ts.isoformat(timespec="seconds"),
        "session_id": "test",
        "project": project,
        "rule_id": rule_id,
        "severity": "warn",
        "ctx": {"cmd": f"git commit ({rule_id})"},
        "action": "logged",
    }


def test_ac1_summary_with_5_records(tmp_path, monkeypatch):
    """AC-1: 5件の violations で SessionStart 集計が正しく表示される."""
    src = tmp_path / "violations.jsonl"
    recs = [_rec("R-007", 0.5)] * 5
    _write_jsonl(src, recs)
    monkeypatch.setattr(report, "VIOLATIONS_FILE", src)
    monkeypatch.setattr(report, "ARCHIVE_DIR", tmp_path / "archive")
    out = report.load(
        7, "claude-context-manager", None, src=src, archive_dir=tmp_path / "archive"
    )
    assert len(out) == 5


def test_ac2_zero_records_silent(tmp_path, monkeypatch, capsys):
    """AC-2: 0件のとき何も出力しない."""
    src = tmp_path / "violations.jsonl"
    src.touch()
    monkeypatch.setattr(report, "VIOLATIONS_FILE", src)
    monkeypatch.setattr(report, "ARCHIVE_DIR", tmp_path / "archive")
    rc = report.main(["summary", "--days", "7", "--project", "claude-context-manager"])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""


def test_ac3_report_markdown(tmp_path, monkeypatch, capsys):
    """AC-3: /guardrails:report が Markdown サマリーを返す."""
    src = tmp_path / "violations.jsonl"
    _write_jsonl(src, [_rec("R-002"), _rec("R-007"), _rec("R-007")])
    monkeypatch.setattr(report, "VIOLATIONS_FILE", src)
    monkeypatch.setattr(report, "ARCHIVE_DIR", tmp_path / "archive")
    rc = report.main(["report", "--days", "7", "--project", "claude-context-manager"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "## Guardrails Report" in out
    assert "| Rule | Count" in out
    assert "R-007" in out


def test_ac4_report_rule_detail(tmp_path, monkeypatch, capsys):
    """AC-4: --rule R-007 で該当ルールの詳細リストが返る."""
    src = tmp_path / "violations.jsonl"
    _write_jsonl(src, [_rec("R-007", i * 0.1) for i in range(3)] + [_rec("R-002")])
    monkeypatch.setattr(report, "VIOLATIONS_FILE", src)
    monkeypatch.setattr(report, "ARCHIVE_DIR", tmp_path / "archive")
    rc = report.main(
        [
            "report",
            "--days",
            "7",
            "--rule",
            "R-007",
            "--project",
            "claude-context-manager",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Top violations (R-007)" in out
    assert out.count("git commit (R-007)") == 3


def test_ac5_archive_moves_old_entries(tmp_path):
    """AC-5: 30日経過 entries が archive/ に移動、元ファイルから削除."""
    src = tmp_path / "violations.jsonl"
    recent = _rec("R-002", days_ago=1)
    old = _rec("R-007", days_ago=45)
    _write_jsonl(src, [recent, old])
    archive_dir = tmp_path / "archive"
    archived, kept = archive_mod.archive(
        src=src, archive_dir=archive_dir, retention_days=30
    )
    assert archived == 1
    assert kept == 1
    remaining = src.read_text(encoding="utf-8").strip().splitlines()
    assert len(remaining) == 1
    assert "R-002" in remaining[0]


def test_ac6_archive_is_gzipped(tmp_path):
    """AC-6: アーカイブファイルが .gz 圧縮されている."""
    src = tmp_path / "violations.jsonl"
    _write_jsonl(src, [_rec("R-007", days_ago=60)])
    archive_dir = tmp_path / "archive"
    archive_mod.archive(src=src, archive_dir=archive_dir, retention_days=30)
    files = list(archive_dir.glob("violations-*.jsonl.gz"))
    assert len(files) == 1
    with gzip.open(files[0], "rt", encoding="utf-8") as f:
        line = f.readline()
    assert "R-007" in line


def test_ac7_hook_under_300ms(tmp_path, monkeypatch):
    """AC-7: SessionStart hook 実行時間 < 300ms (空ファイル想定)."""
    fake_home = tmp_path / "home"
    (fake_home / ".claude" / "guardrails").mkdir(parents=True)
    (fake_home / ".claude" / "guardrails" / "violations.jsonl").touch()
    env = {"HOME": str(fake_home), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    # Warm-up to avoid measuring python first-import jitter
    subprocess.run(["bash", str(HOOK_SH)], env=env, capture_output=True, check=False)
    start = time.perf_counter()
    subprocess.run(["bash", str(HOOK_SH)], env=env, capture_output=True, check=False)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 300, f"hook took {elapsed_ms:.0f}ms"


def test_archive_handles_missing_file(tmp_path):
    """Fail-open: missing source file → (0,0)."""
    archived, kept = archive_mod.archive(
        src=tmp_path / "nope.jsonl", archive_dir=tmp_path / "a", retention_days=30
    )
    assert (archived, kept) == (0, 0)
