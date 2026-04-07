"""Tests for src/hooks/dep_guard.py (Issue #129)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.hooks import dep_guard  # noqa: E402


# ---------- extract_packages ----------


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("npm install lodash", ("npm", ["lodash"])),
        ("npm i -g typescript", ("npm", ["typescript"])),
        ("npm install lodash@4.17.21 axios", ("npm", ["lodash", "axios"])),
        ("pnpm add react react-dom", ("npm", ["react", "react-dom"])),
        ("yarn add --dev jest", ("npm", ["jest"])),
        ("pip install requests", ("pypi", ["requests"])),
        ("pip3 install 'flask>=2.0'", ("pypi", ["flask"])),
        ("uv add httpx", ("pypi", ["httpx"])),
        ("cargo add serde", ("cargo", ["serde"])),
        ("go get github.com/foo/bar", ("go", ["github.com/foo/bar"])),
    ],
)
def test_extract_packages_positive(cmd, expected):
    assert dep_guard.extract_packages(cmd) == expected


@pytest.mark.parametrize(
    "cmd",
    [
        "npm install",  # bare = lockfile install
        "pip install",
        "ls -la",
        "echo hi",
        "npm run build",
    ],
)
def test_extract_packages_negative(cmd):
    assert dep_guard.extract_packages(cmd) is None


# ---------- evaluate / allowlist ----------


def test_allowlist_bypasses_check():
    allow = {"npm": ["sketchy"]}
    with patch.object(dep_guard, "check_npm") as m:
        blocked = dep_guard.evaluate("npm", ["sketchy"], allow)
        assert blocked == []
        m.assert_not_called()


def test_block_on_low_downloads():
    with patch.object(
        dep_guard, "check_npm", return_value=(False, "weekly DL: 3,200 (< 10,000)")
    ):
        blocked = dep_guard.evaluate("npm", ["badpkg"], {})
        assert blocked == [("badpkg", "weekly DL: 3,200 (< 10,000)")]


def test_pass_on_good_package():
    with patch.object(dep_guard, "check_npm", return_value=(True, "ok")):
        assert dep_guard.evaluate("npm", ["lodash"], {}) == []


def test_fail_open_on_api_error():
    import urllib.error

    def boom(_pkg):
        raise urllib.error.URLError("timeout")

    with patch.object(dep_guard, "check_npm", side_effect=boom):
        assert dep_guard.evaluate("npm", ["whatever"], {}) == []


# ---------- main (end-to-end via stdin) ----------


def _run(stdin: str, env: dict | None = None) -> subprocess.CompletedProcess:
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, str(ROOT / "src/hooks/dep_guard.py")],
        input=stdin,
        capture_output=True,
        text=True,
        env=e,
        cwd=str(ROOT),
    )


def test_main_non_bash_tool_passes():
    p = _run(json.dumps({"tool_name": "Read", "tool_input": {}}))
    assert p.returncode == 0


def test_main_non_dep_bash_passes():
    p = _run(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}))
    assert p.returncode == 0


def test_main_approve_deps_bypass():
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "npm install sketchy"}}
    )
    p = _run(payload, env={"APPROVE_DEPS": "1"})
    assert p.returncode == 0


def test_main_malformed_stdin_fail_open():
    p = _run("not-json")
    assert p.returncode == 0


def test_main_block_path(monkeypatch):
    """Integration: force check_npm to fail and ensure exit 2."""
    # We run in-process here to inject the mock.
    monkeypatch.setenv("APPROVE_DEPS", "")
    monkeypatch.delenv("APPROVE_DEPS", raising=False)
    payload = {"tool_name": "Bash", "tool_input": {"command": "npm install badpkg"}}
    with patch.object(
        dep_guard, "check_npm", return_value=(False, "weekly DL: 5 (< 10,000)")
    ):
        with patch("sys.stdin.read", return_value=json.dumps(payload)):
            rc = dep_guard.main()
    assert rc == 2


def test_main_pass_path(monkeypatch):
    monkeypatch.delenv("APPROVE_DEPS", raising=False)
    payload = {"tool_name": "Bash", "tool_input": {"command": "npm install lodash"}}
    with patch.object(dep_guard, "check_npm", return_value=(True, "ok")):
        with patch("sys.stdin.read", return_value=json.dumps(payload)):
            rc = dep_guard.main()
    assert rc == 0


def test_extract_packages_shell_separator():
    # `;`/`|`/`&&` must terminate package extraction
    assert dep_guard.extract_packages("echo hi; npm install lodash") == (
        "npm",
        ["lodash"],
    )
    assert dep_guard.extract_packages("npm install lodash | tee log") == (
        "npm",
        ["lodash"],
    )
    assert dep_guard.extract_packages("npm install lodash && echo done") == (
        "npm",
        ["lodash"],
    )


# ---------- check_* (network mocked) ----------


def _mock_fetch(mapping):
    def fake(url):
        for key, val in mapping.items():
            if key in url:
                return val
        raise KeyError(url)

    return fake


def test_check_npm_pass(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "downloads/point": {"downloads": 50_000_000},
                "registry.npmjs.org": {
                    "dist-tags": {"latest": "1.0.0"},
                    "versions": {
                        "1.0.0": {
                            "license": "MIT",
                            "repository": {"url": "https://github.com/foo/bar"},
                        }
                    },
                },
                "api.github.com": {"pushed_at": "2026-04-01T00:00:00Z"},
            }
        ),
    )
    ok, _ = dep_guard.check_npm("lodash")
    assert ok


def test_check_npm_low_downloads(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "downloads/point": {"downloads": 100},
            }
        ),
    )
    ok, reason = dep_guard.check_npm("badpkg")
    assert not ok and "weekly DL" in reason


def test_check_npm_bad_license(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "downloads/point": {"downloads": 50_000_000},
                "registry.npmjs.org": {
                    "dist-tags": {"latest": "1.0.0"},
                    "versions": {"1.0.0": {"license": "GPL-3.0"}},
                },
            }
        ),
    )
    ok, reason = dep_guard.check_npm("gplpkg")
    assert not ok and "license" in reason


def test_check_npm_stale_repo(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "downloads/point": {"downloads": 50_000_000},
                "registry.npmjs.org": {
                    "dist-tags": {"latest": "1.0.0"},
                    "versions": {
                        "1.0.0": {
                            "license": "MIT",
                            "repository": {"url": "https://github.com/foo/bar"},
                        }
                    },
                },
                "api.github.com": {"pushed_at": "2020-01-01T00:00:00Z"},
            }
        ),
    )
    ok, reason = dep_guard.check_npm("stale")
    assert not ok and "last commit" in reason


def test_check_pypi_pass(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "pypi.org/pypi": {"info": {"license": "MIT", "project_urls": {}}},
                "pypistats.org": {"data": {"last_week": 5_000_000}},
            }
        ),
    )
    ok, _ = dep_guard.check_pypi("requests")
    assert ok


def test_check_pypi_bad_license(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "pypi.org/pypi": {"info": {"license": "GPL", "classifiers": []}},
            }
        ),
    )
    ok, reason = dep_guard.check_pypi("gpl")
    assert not ok and "license" in reason


def test_check_cargo_pass(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "crates.io": {
                    "crate": {"recent_downloads": 5_000_000, "repository": ""},
                    "versions": [{"license": "MIT"}],
                },
            }
        ),
    )
    ok, _ = dep_guard.check_cargo("serde")
    assert ok


def test_check_go_non_github_passes(monkeypatch):
    ok, _ = dep_guard.check_go("golang.org/x/net")
    assert ok


def test_check_go_stale(monkeypatch):
    monkeypatch.setattr(
        dep_guard,
        "_fetch_json",
        _mock_fetch(
            {
                "api.github.com": {"pushed_at": "2018-01-01T00:00:00Z"},
            }
        ),
    )
    ok, reason = dep_guard.check_go("github.com/foo/bar")
    assert not ok and "last commit" in reason


def test_main_allowlist_integration(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".claude/hooks").mkdir(parents=True)
    (tmp_path / ".claude/hooks/dep-guard-allowlist.json").write_text(
        json.dumps({"npm": ["sketchy"]})
    )
    payload = {"tool_name": "Bash", "tool_input": {"command": "npm install sketchy"}}
    with patch.object(dep_guard, "check_npm") as m:
        with patch("sys.stdin.read", return_value=json.dumps(payload)):
            rc = dep_guard.main()
    assert rc == 0
    m.assert_not_called()
