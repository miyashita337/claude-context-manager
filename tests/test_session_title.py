#!/usr/bin/env python3
"""Tests for session title management system (Issue #109).

Test strategy:
  - importlib.util for hyphenated filenames (same pattern as test_user_prompt_submit.py)
  - monkeypatch TITLES_DIR to tmp_path for isolation
  - unittest.mock.patch for /dev/tty, subprocess.run
"""

import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── module loaders ───────────────────────────────────────────────────────────
SESSION_TITLE_DIR = Path(__file__).parent.parent / "src" / "session-title"


def _load_utils():
    spec = importlib.util.spec_from_file_location(
        "session_title_utils",
        SESSION_TITLE_DIR / "session_title_utils.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_session_start():
    spec = importlib.util.spec_from_file_location(
        "session_start_title",
        SESSION_TITLE_DIR / "session-start-title.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_prompt_check():
    spec = importlib.util.spec_from_file_location(
        "prompt_title_check",
        SESSION_TITLE_DIR / "prompt-title-check.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_statusline():
    spec = importlib.util.spec_from_file_location(
        "statusline",
        SESSION_TITLE_DIR / "statusline.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


utils = _load_utils()


# =============================================================================
# A. session_title_utils.py (4 tests)
# =============================================================================


class TestSessionTitleUtils:
    """Tests for shared utility functions."""

    def test_write_and_read_title(self, tmp_path, monkeypatch):
        """Write title then read it back — title and source must match."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)
        utils.write_title("sess-001", "Fix Auth Bug", "branch")
        title, source = utils.read_title("sess-001")
        assert title == "Fix Auth Bug"
        assert source == "branch"

    def test_read_title_missing_file(self, tmp_path, monkeypatch):
        """Non-existent session file returns (None, None)."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)
        title, source = utils.read_title("nonexistent")
        assert title is None
        assert source is None

    def test_set_iterm2_tab_no_tty(self):
        """OSError on /dev/tty open is silently caught."""
        with patch("builtins.open", side_effect=OSError("no tty")):
            # Should not raise
            utils.set_iterm2_tab("test title")

    def test_get_branch_name(self):
        """Mocked subprocess returns branch name."""
        mock_result = MagicMock()
        mock_result.stdout = "feature/session-title\n"
        with patch("subprocess.run", return_value=mock_result):
            branch = utils.get_branch_name("/some/dir")
        assert branch == "feature/session-title"


# =============================================================================
# B. session-start-title.py (3 tests)
# =============================================================================


class TestSessionStartTitle:
    """Tests for SessionStart hook."""

    def test_new_session_sets_branch_title(self, tmp_path, monkeypatch):
        """New session with no existing title sets branch name as title."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)

        start_mod = _load_session_start()
        monkeypatch.setattr(start_mod, "read_title", utils.read_title)
        monkeypatch.setattr(start_mod, "write_title", utils.write_title)
        monkeypatch.setattr(start_mod, "set_iterm2_tab", lambda t: None)
        monkeypatch.setattr(
            start_mod,
            "get_branch_name",
            lambda cwd: "feat/login",
        )

        stdin_data = json.dumps({"session_id": "s1", "cwd": "/project"})
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        start_mod.main()

        output = json.loads(stdout_capture.getvalue())
        assert "feat/login" in output["hookSpecificOutput"]["additionalContext"]

        # Verify title was written
        title, source = utils.read_title("s1")
        assert title == "feat/login"
        assert source == "branch"

    def test_resume_session_keeps_existing_title(self, tmp_path, monkeypatch):
        """Existing title is not overwritten on resume."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)
        utils.write_title("s2", "Custom Title", "ai")

        start_mod = _load_session_start()
        monkeypatch.setattr(start_mod, "read_title", utils.read_title)
        monkeypatch.setattr(start_mod, "write_title", utils.write_title)
        monkeypatch.setattr(start_mod, "set_iterm2_tab", lambda t: None)

        stdin_data = json.dumps({"session_id": "s2", "cwd": "/project"})
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        start_mod.main()

        output = json.loads(stdout_capture.getvalue())
        assert "Custom Title" in output["hookSpecificOutput"]["additionalContext"]
        assert "source: ai" in output["hookSpecificOutput"]["additionalContext"]

        # Verify title was NOT overwritten
        title, source = utils.read_title("s2")
        assert title == "Custom Title"
        assert source == "ai"

    def test_empty_session_id_no_output(self, monkeypatch):
        """Empty session_id produces no output."""
        start_mod = _load_session_start()

        stdin_data = json.dumps({"session_id": "", "cwd": "/project"})
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        start_mod.main()

        assert stdout_capture.getvalue() == ""


# =============================================================================
# C. prompt-title-check.py (3 tests)
# =============================================================================


class TestPromptTitleCheck:
    """Tests for UserPromptSubmit title injection hook."""

    def test_skips_ai_source(self, tmp_path, monkeypatch):
        """Source=ai skips immediately with no output."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)
        utils.write_title("s3", "AI Title", "ai")

        check_mod = _load_prompt_check()
        monkeypatch.setattr(check_mod, "read_title", utils.read_title)

        stdin_data = json.dumps(
            {"session_id": "s3", "transcript_path": "/fake/path"}
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        check_mod.main()

        assert stdout_capture.getvalue() == ""

    def test_skips_fewer_than_2_messages(self, tmp_path, monkeypatch):
        """Only 1 user message — skips title injection."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)
        utils.write_title("s4", "branch-title", "branch")

        # Create transcript with 1 message
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text(json.dumps({"type": "human", "message": "hello"}))

        check_mod = _load_prompt_check()
        monkeypatch.setattr(check_mod, "read_title", utils.read_title)

        stdin_data = json.dumps(
            {"session_id": "s4", "transcript_path": str(transcript)}
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        check_mod.main()

        assert stdout_capture.getvalue() == ""

    def test_injects_title_instruction(self, tmp_path, monkeypatch):
        """2+ messages with branch source triggers title injection."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)
        utils.write_title("s5", "main", "branch")

        # Create transcript with 2 messages
        transcript = tmp_path / "transcript.jsonl"
        lines = [
            json.dumps({"type": "human", "message": "fix the bug"}),
            json.dumps({"type": "human", "message": "add tests"}),
        ]
        transcript.write_text("\n".join(lines))

        check_mod = _load_prompt_check()
        monkeypatch.setattr(check_mod, "read_title", utils.read_title)

        stdin_data = json.dumps(
            {"session_id": "s5", "transcript_path": str(transcript)}
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        check_mod.main()

        output = json.loads(stdout_capture.getvalue())
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Session Title Request" in ctx
        assert "s5" in ctx


# =============================================================================
# D. statusline.py (2 tests)
# =============================================================================


class TestStatusLine:
    """Tests for StatusLine display script."""

    def test_displays_title_with_model_and_context(self, tmp_path, monkeypatch):
        """Title + model + context percentage in output."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)
        utils.write_title("s6", "Debug Auth Flow", "ai")

        sl_mod = _load_statusline()
        monkeypatch.setattr(sl_mod, "read_title", utils.read_title)
        monkeypatch.setattr(sl_mod, "set_iterm2_tab", lambda t: None)

        stdin_data = json.dumps(
            {
                "session_id": "s6",
                "cwd": "/project",
                "model": {"display_name": "Opus"},
                "context_window": {"used_percentage": 42},
            }
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        sl_mod.main()

        line = stdout_capture.getvalue().strip()
        assert "[Debug Auth Flow]" in line
        assert "Opus" in line
        assert "42%" in line

    def test_fallback_to_branch_name(self, tmp_path, monkeypatch):
        """No title file — falls back to branch name."""
        monkeypatch.setattr(utils, "TITLES_DIR", tmp_path)

        sl_mod = _load_statusline()
        monkeypatch.setattr(sl_mod, "read_title", utils.read_title)
        monkeypatch.setattr(sl_mod, "set_iterm2_tab", lambda t: None)
        monkeypatch.setattr(sl_mod, "get_branch_name", lambda cwd: "develop")

        stdin_data = json.dumps(
            {
                "session_id": "s7",
                "cwd": "/project",
                "model": {"display_name": "Sonnet"},
                "context_window": {"used_percentage": 10},
            }
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin_data))

        stdout_capture = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout_capture)

        sl_mod.main()

        line = stdout_capture.getvalue().strip()
        assert "[develop]" in line
        assert "Sonnet" in line
