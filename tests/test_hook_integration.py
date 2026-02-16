#!/usr/bin/env python3
"""Integration tests for Hook end-to-end workflow.

These tests verify that hooks correctly log session data and that the
complete lifecycle works: user prompt -> tool use -> session finalization.

Created in response to a bug where hook settings were deleted, causing
session logs to stop being recorded.
"""

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# === Constants ===

PROJECT_ROOT = Path(__file__).parent.parent
HOOKS_DIR = PROJECT_ROOT / "src" / "hooks"
SHARED_DIR = HOOKS_DIR / "shared"

# Ensure shared modules are importable
sys.path.insert(0, str(SHARED_DIR))

from config import estimate_tokens
from logger import SessionLogger


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_context_dir(tmp_path, monkeypatch):
    """Create a temporary context-history directory tree."""
    context_dir = tmp_path / ".claude" / "context-history"

    # Patch config module paths
    monkeypatch.setattr("config.CONTEXT_HISTORY_DIR", context_dir)
    monkeypatch.setattr("config.TMP_DIR", context_dir / ".tmp")
    monkeypatch.setattr("config.SESSIONS_DIR", context_dir / "sessions")
    monkeypatch.setattr("config.ARCHIVES_DIR", context_dir / "archives")
    monkeypatch.setattr("config.METADATA_DIR", context_dir / ".metadata")

    # Also patch the logger module's imported TMP_DIR
    import logger as logger_module
    logger_module.TMP_DIR = context_dir / ".tmp"

    return context_dir


@pytest.fixture
def unique_session_id():
    """Generate a unique session ID for each test."""
    return f"integration-{uuid.uuid4().hex[:12]}"


# ============================================================================
# Integration Test: User Prompt Submit Hook
# ============================================================================


class TestUserPromptSubmitIntegration:
    """Test that user-prompt-submit hook logs user prompts correctly."""

    def test_user_prompt_creates_log_file(self, temp_context_dir, unique_session_id):
        """A user prompt should create a log file in .tmp/."""
        logger = SessionLogger(unique_session_id)
        logger.add_entry("user", "Hello, Claude!")

        log_file = temp_context_dir / ".tmp" / f"session-{unique_session_id}.json"
        assert log_file.exists(), "Log file should be created after first user prompt"

    def test_user_prompt_content_recorded(self, temp_context_dir, unique_session_id):
        """User prompt content must be recorded accurately."""
        prompt = "Please explain Python decorators"
        logger = SessionLogger(unique_session_id)
        logger.add_entry("user", prompt)

        logs = logger._load_logs()
        assert len(logs) == 1
        assert logs[0]["type"] == "user"
        assert logs[0]["content"] == prompt

    def test_user_prompt_has_timestamp(self, temp_context_dir, unique_session_id):
        """Each logged entry must have a timestamp."""
        logger = SessionLogger(unique_session_id)
        logger.add_entry("user", "Test prompt")

        logs = logger._load_logs()
        assert "timestamp" in logs[0], "Entry must have a timestamp"
        # Verify ISO format
        from datetime import datetime
        datetime.fromisoformat(logs[0]["timestamp"])

    def test_user_prompt_has_token_estimate(self, temp_context_dir, unique_session_id):
        """Each logged entry must have a token estimate."""
        prompt = "a" * 100  # ~25 tokens
        logger = SessionLogger(unique_session_id)
        logger.add_entry("user", prompt)

        logs = logger._load_logs()
        assert "tokens_estimate" in logs[0]
        assert logs[0]["tokens_estimate"] == 25

    def test_multiple_user_prompts_appended(self, temp_context_dir, unique_session_id):
        """Multiple user prompts should be appended in order."""
        logger = SessionLogger(unique_session_id)
        prompts = ["First question", "Second question", "Third question"]

        for prompt in prompts:
            logger.add_entry("user", prompt)

        logs = logger._load_logs()
        assert len(logs) == 3
        for i, prompt in enumerate(prompts):
            assert logs[i]["content"] == prompt
            assert logs[i]["type"] == "user"


# ============================================================================
# Integration Test: Post Tool Use Hook
# ============================================================================


class TestPostToolUseIntegration:
    """Test that post-tool-use hook logs tool usage correctly."""

    def test_tool_use_logged_as_assistant(self, temp_context_dir, unique_session_id):
        """Tool usage should be logged as an assistant entry."""
        logger = SessionLogger(unique_session_id)
        logger.add_entry(
            "assistant",
            "Tool: Read\nInput: /test.txt\nResult: file content",
            tool_name="Read",
        )

        logs = logger._load_logs()
        assert len(logs) == 1
        assert logs[0]["type"] == "assistant"

    def test_tool_metadata_preserved(self, temp_context_dir, unique_session_id):
        """Tool name and input should be preserved in metadata."""
        tool_input = {"file_path": "/Users/test/file.py"}
        logger = SessionLogger(unique_session_id)
        logger.add_entry(
            "assistant",
            "Tool: Read\nResult: content",
            tool_name="Read",
            tool_input=tool_input,
        )

        logs = logger._load_logs()
        assert logs[0]["tool_name"] == "Read"
        assert logs[0]["tool_input"] == tool_input

    def test_tool_use_after_user_prompt(self, temp_context_dir, unique_session_id):
        """Tool use entry appended after user prompt maintains order."""
        logger = SessionLogger(unique_session_id)

        # User asks a question
        logger.add_entry("user", "Read the file test.py")

        # Claude uses a tool
        logger.add_entry(
            "assistant",
            "Tool: Read\nResult: def hello(): pass",
            tool_name="Read",
            tool_input={"file_path": "test.py"},
        )

        logs = logger._load_logs()
        assert len(logs) == 2
        assert logs[0]["type"] == "user"
        assert logs[1]["type"] == "assistant"
        assert logs[1]["tool_name"] == "Read"


# ============================================================================
# Integration Test: Full Session Lifecycle
# ============================================================================


class TestSessionLifecycle:
    """Test the complete session lifecycle: prompts -> tool use -> finalization."""

    def test_full_session_recording(self, temp_context_dir, unique_session_id):
        """Simulate a complete session and verify all entries are recorded."""
        logger = SessionLogger(unique_session_id)

        # Step 1: User sends a prompt
        logger.add_entry("user", "Please read config.py")

        # Step 2: Claude uses the Read tool
        logger.add_entry(
            "assistant",
            "Tool: Read\nInput: config.py\nResult: import os...",
            tool_name="Read",
            tool_input={"file_path": "config.py"},
        )

        # Step 3: User sends another prompt
        logger.add_entry("user", "Now modify line 10")

        # Step 4: Claude uses the Edit tool
        logger.add_entry(
            "assistant",
            "Tool: Edit\nInput: config.py\nResult: Edit applied",
            tool_name="Edit",
            tool_input={"file_path": "config.py", "old_string": "x", "new_string": "y"},
        )

        # Step 5: User confirms
        logger.add_entry("user", "Looks good, thanks!")

        # Verify all entries
        logs = logger._load_logs()
        assert len(logs) == 5, f"Expected 5 log entries, got {len(logs)}"

        # Verify types alternate correctly
        expected_types = ["user", "assistant", "user", "assistant", "user"]
        actual_types = [log["type"] for log in logs]
        assert actual_types == expected_types

        # Verify tool entries have metadata
        tool_entries = [log for log in logs if log["type"] == "assistant"]
        assert len(tool_entries) == 2
        assert tool_entries[0]["tool_name"] == "Read"
        assert tool_entries[1]["tool_name"] == "Edit"

    def test_session_stats_accuracy(self, temp_context_dir, unique_session_id):
        """Session stats must accurately reflect the logged data."""
        logger = SessionLogger(unique_session_id)

        # Add entries with known sizes
        user_text = "a" * 40   # 10 tokens
        tool_text = "b" * 80   # 20 tokens

        logger.add_entry("user", user_text)
        logger.add_entry("assistant", tool_text, tool_name="Bash")
        logger.add_entry("user", user_text)

        stats = logger.get_session_stats()

        assert stats["entry_count"] == 3
        assert stats["user_tokens"] == 20   # 10 + 10
        assert stats["assistant_tokens"] == 20
        assert stats["total_tokens"] == 40

    def test_log_file_is_json_lines_format(self, temp_context_dir, unique_session_id):
        """Log file must use JSON Lines format (one JSON object per line)."""
        logger = SessionLogger(unique_session_id)
        logger.add_entry("user", "First")
        logger.add_entry("assistant", "Second", tool_name="Bash")
        logger.add_entry("user", "Third")

        log_file = temp_context_dir / ".tmp" / f"session-{unique_session_id}.json"

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Each non-empty line should be valid JSON
        json_entries = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
                json_entries.append(entry)
            except json.JSONDecodeError:
                pytest.fail(f"Line {i+1} is not valid JSON: {stripped[:100]}")

        assert len(json_entries) == 3, "Should have 3 JSON Lines entries"

    def test_session_isolation(self, temp_context_dir):
        """Different session IDs should create separate log files."""
        session_a = f"session-a-{uuid.uuid4().hex[:8]}"
        session_b = f"session-b-{uuid.uuid4().hex[:8]}"

        logger_a = SessionLogger(session_a)
        logger_b = SessionLogger(session_b)

        logger_a.add_entry("user", "Message for session A")
        logger_b.add_entry("user", "Message for session B")

        logs_a = logger_a._load_logs()
        logs_b = logger_b._load_logs()

        assert len(logs_a) == 1
        assert len(logs_b) == 1
        assert logs_a[0]["content"] == "Message for session A"
        assert logs_b[0]["content"] == "Message for session B"


# ============================================================================
# Integration Test: Hook Script Execution
# ============================================================================


class TestHookScriptExecution:
    """Test that hook scripts can be executed as subprocesses."""

    def test_user_prompt_submit_script_runs(self, temp_context_dir, unique_session_id):
        """user-prompt-submit.py should execute and return valid JSON."""
        script = HOOKS_DIR / "user-prompt-submit.py"
        input_data = json.dumps({
            "session_id": unique_session_id,
            "prompt": "Test from integration test",
        })

        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, str(script)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )

        assert result.returncode == 0, (
            f"user-prompt-submit.py failed with code {result.returncode}\n"
            f"stderr: {result.stderr}"
        )

        # Parse output
        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["status"] == "logged"

    def test_post_tool_use_script_runs(self, temp_context_dir, unique_session_id):
        """post-tool-use.py should execute and return valid JSON."""
        script = HOOKS_DIR / "post-tool-use.py"
        input_data = json.dumps({
            "session_id": unique_session_id,
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": "file1.txt\nfile2.txt",
        })

        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, str(script)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )

        assert result.returncode == 0, (
            f"post-tool-use.py failed with code {result.returncode}\n"
            f"stderr: {result.stderr}"
        )

        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["status"] == "logged"

    def test_user_prompt_then_tool_use_sequence(self, temp_context_dir, unique_session_id):
        """Execute both hooks in sequence and verify combined logs."""
        env = os.environ.copy()

        # Step 1: User prompt
        prompt_script = HOOKS_DIR / "user-prompt-submit.py"
        prompt_input = json.dumps({
            "session_id": unique_session_id,
            "prompt": "Read a file",
        })
        result1 = subprocess.run(
            [sys.executable, str(prompt_script)],
            input=prompt_input,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result1.returncode == 0

        # Step 2: Tool use
        tool_script = HOOKS_DIR / "post-tool-use.py"
        tool_input = json.dumps({
            "session_id": unique_session_id,
            "tool_name": "Read",
            "tool_input": {"file_path": "/test.py"},
            "tool_response": "def main(): pass",
        })
        result2 = subprocess.run(
            [sys.executable, str(tool_script)],
            input=tool_input,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        assert result2.returncode == 0

        # Verify both entries exist in the same log file
        # Note: uses real home dir since scripts run without monkeypatch
        from pathlib import Path as RealPath
        log_file = RealPath.home() / ".claude" / "context-history" / ".tmp" / f"session-{unique_session_id}.json"

        assert log_file.exists(), f"Combined log file should exist at {log_file}"

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            logs = [json.loads(line) for line in lines if line.strip()]

        assert len(logs) == 2, f"Expected 2 entries, got {len(logs)}"
        assert logs[0]["type"] == "user"
        assert logs[0]["content"] == "Read a file"
        assert logs[1]["type"] == "assistant"
        assert "Tool: Read" in logs[1]["content"]

        # Cleanup
        if log_file.exists():
            log_file.unlink()


# ============================================================================
# Integration Test: Error Resilience
# ============================================================================


class TestErrorResilience:
    """Test that hooks handle errors gracefully without blocking Claude."""

    def test_hook_with_empty_stdin(self):
        """Hooks should handle empty stdin gracefully (exit 0)."""
        script = HOOKS_DIR / "user-prompt-submit.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, "Hook must not fail on empty stdin"

        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["status"] in ("skipped", "ok")

    def test_hook_with_invalid_json(self):
        """Hooks should handle invalid JSON gracefully (exit 0)."""
        script = HOOKS_DIR / "user-prompt-submit.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            input="not valid json {{{{",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, "Hook must not fail on invalid JSON"

        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["status"] in ("error", "skipped")

    def test_hook_with_missing_fields(self):
        """Hooks should handle JSON with missing fields gracefully."""
        script = HOOKS_DIR / "user-prompt-submit.py"
        # Valid JSON but missing expected fields
        input_data = json.dumps({"unexpected_field": "value"})
        result = subprocess.run(
            [sys.executable, str(script)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, "Hook must not fail on missing fields"

        output = json.loads(result.stdout)
        # Should either log with defaults or return logged status
        assert "hookSpecificOutput" in output

    def test_hook_with_unicode_content(self):
        """Hooks should handle Unicode content correctly."""
        script = HOOKS_DIR / "user-prompt-submit.py"
        session_id = f"unicode-{uuid.uuid4().hex[:8]}"
        input_data = json.dumps({
            "session_id": session_id,
            "prompt": "日本語テスト: Unicode content handling",
        })
        result = subprocess.run(
            [sys.executable, str(script)],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["hookSpecificOutput"]["status"] == "logged"

        # Cleanup
        from pathlib import Path as RealPath
        log_file = RealPath.home() / ".claude" / "context-history" / ".tmp" / f"session-{session_id}.json"
        if log_file.exists():
            log_file.unlink()


# ============================================================================
# Integration Test: Stop Hook (Mocked)
# ============================================================================


class TestStopHookIntegration:
    """Test stop hook behavior (subprocess call is mocked to avoid npx dependency)."""

    def test_stop_hook_calls_finalize_script(self):
        """Stop hook should call the TypeScript finalization script."""
        script = HOOKS_DIR / "stop.py"
        session_id = f"stop-test-{uuid.uuid4().hex[:8]}"
        input_data = json.dumps({"session_id": session_id})

        # Mock subprocess.run to avoid actual npx/tsx execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Finalized"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            # Run the stop hook script in a subprocess, but we need to
            # intercept its subprocess.run call, so we test the module directly
            sys.path.insert(0, str(HOOKS_DIR))
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                f"stop_{uuid.uuid4().hex[:8]}",
                script,
            )
            stop_module = importlib.util.module_from_spec(spec)

            mock_stdin = MagicMock()
            mock_stdin.read.return_value = json.dumps({"session_id": session_id})
            with patch("sys.stdin", mock_stdin):
                spec.loader.exec_module(stop_module)
                with pytest.raises(SystemExit) as exc_info:
                    stop_module.main()
                assert exc_info.value.code == 0

            # Verify subprocess.run was called
            assert mock_run.called, "Stop hook must call subprocess.run"
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert "npx" in cmd, f"Command should include 'npx', got: {cmd}"
            assert session_id in cmd, f"Command should include session_id, got: {cmd}"
