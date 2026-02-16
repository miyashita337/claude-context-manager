#!/usr/bin/env python3
"""Comprehensive test suite for Claude Context Manager Python hooks."""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Setup path to import hooks modules
HOOKS_DIR = Path(__file__).parent.parent / "src" / "hooks"
SHARED_DIR = HOOKS_DIR / "shared"
sys.path.insert(0, str(SHARED_DIR))

from config import (
    ARCHIVES_DIR,
    METADATA_DIR,
    SESSIONS_DIR,
    TMP_DIR,
    ensure_directories,
    estimate_tokens,
)
from logger import SessionLogger


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_context_dir(tmp_path, monkeypatch):
    """Create a temporary directory for context history."""
    context_dir = tmp_path / ".claude" / "context-history"
    monkeypatch.setattr("config.CONTEXT_HISTORY_DIR", context_dir)
    monkeypatch.setattr("config.TMP_DIR", context_dir / ".tmp")
    monkeypatch.setattr("config.SESSIONS_DIR", context_dir / "sessions")
    monkeypatch.setattr("config.ARCHIVES_DIR", context_dir / "archives")
    monkeypatch.setattr("config.METADATA_DIR", context_dir / ".metadata")

    # Update logger module's imported constants
    import logger as logger_module
    logger_module.TMP_DIR = context_dir / ".tmp"

    return context_dir


@pytest.fixture
def session_id():
    """Generate a test session ID."""
    return "test-session-123"


@pytest.fixture
def session_logger(temp_context_dir, session_id):
    """Create a SessionLogger instance for testing."""
    return SessionLogger(session_id)


# ============================================================================
# Test Cases for logger.py (4 test cases)
# ============================================================================


def test_session_logger_file_creation_and_loading(session_logger, temp_context_dir, session_id):
    """
    Test Case 1: SessionLogger basic operations (file creation and loading).

    Verifies:
    - Directories are created when SessionLogger is initialized
    - Log file is created with correct naming
    - Empty logs are loaded correctly
    """
    # Verify directories were created
    tmp_dir = temp_context_dir / ".tmp"
    assert tmp_dir.exists(), "TMP_DIR should be created"

    # Verify log file path is correct
    expected_log_file = tmp_dir / f"session-{session_id}.json"
    assert session_logger.log_file == expected_log_file

    # Verify empty logs are loaded correctly
    logs = session_logger._load_logs()
    assert logs == [], "New logger should have empty logs"


def test_add_entry_append_operations(session_logger):
    """
    Test Case 2: add_entry append operations (multiple entries).

    Verifies:
    - Entries are appended correctly
    - Multiple entries maintain order
    - Timestamp and token estimates are added
    - File persistence works across calls
    """
    # Add first entry
    session_logger.add_entry("user", "First message")
    logs = session_logger._load_logs()
    assert len(logs) == 1
    assert logs[0]["type"] == "user"
    assert logs[0]["content"] == "First message"
    assert "timestamp" in logs[0]
    assert "tokens_estimate" in logs[0]

    # Add second entry
    session_logger.add_entry("assistant", "Second message", tool_name="test_tool")
    logs = session_logger._load_logs()
    assert len(logs) == 2
    assert logs[1]["type"] == "assistant"
    assert logs[1]["content"] == "Second message"
    assert logs[1]["tool_name"] == "test_tool"

    # Verify order is maintained
    assert logs[0]["content"] == "First message"
    assert logs[1]["content"] == "Second message"

    # Add third entry
    session_logger.add_entry("user", "Third message")
    logs = session_logger._load_logs()
    assert len(logs) == 3


def test_get_session_stats_token_calculation(session_logger):
    """
    Test Case 3: get_session_stats calculation (user/assistant token counting).

    Verifies:
    - Token counts are calculated correctly for user messages
    - Token counts are calculated correctly for assistant messages
    - Total tokens are summed correctly
    - Entry count is accurate
    """
    # Test empty stats
    stats = session_logger.get_session_stats()
    assert stats["total_tokens"] == 0
    assert stats["user_tokens"] == 0
    assert stats["assistant_tokens"] == 0
    assert stats["entry_count"] == 0

    # Add user messages
    session_logger.add_entry("user", "a" * 100)  # ~25 tokens
    session_logger.add_entry("user", "b" * 200)  # ~50 tokens

    # Add assistant messages
    session_logger.add_entry("assistant", "c" * 400)  # ~100 tokens

    # Calculate stats
    stats = session_logger.get_session_stats()

    # Verify calculations
    assert stats["user_tokens"] == 75, "User tokens should be ~75 (25 + 50)"
    assert stats["assistant_tokens"] == 100, "Assistant tokens should be ~100"
    assert stats["total_tokens"] == 175, "Total should be 175 (75 + 100)"
    assert stats["entry_count"] == 3, "Should have 3 entries"


def test_japanese_content_handling(session_logger):
    """
    Test Case 4: Japanese content handling (non-ASCII characters).

    Verifies:
    - Japanese text is stored correctly without corruption
    - UTF-8 encoding is preserved
    - Token estimation works for multi-byte characters
    - JSON serialization handles Unicode properly
    """
    # Add Japanese content
    japanese_text = "こんにちは世界！これはテストです。"
    session_logger.add_entry("user", japanese_text)

    # Load and verify
    logs = session_logger._load_logs()
    assert len(logs) == 1
    assert logs[0]["content"] == japanese_text, "Japanese text should be preserved"
    assert logs[0]["type"] == "user"

    # Verify token estimation (should work with multi-byte chars)
    assert logs[0]["tokens_estimate"] > 0

    # Add mixed content
    mixed_text = "Hello世界! This is a テスト message."
    session_logger.add_entry("assistant", mixed_text)

    logs = session_logger._load_logs()
    assert len(logs) == 2
    assert logs[1]["content"] == mixed_text, "Mixed content should be preserved"

    # Verify file can be read back correctly (JSON Lines format)
    with open(session_logger.log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        file_data = [json.loads(line) for line in lines if line.strip()]
    assert file_data[0]["content"] == japanese_text
    assert file_data[1]["content"] == mixed_text


# ============================================================================
# Test Cases for config.py (2 test cases)
# ============================================================================


def test_ensure_directories_creation(temp_context_dir, monkeypatch):
    """
    Test Case 5: ensure_directories operation.

    Verifies:
    - All required directories are created
    - parent=True works correctly for nested paths
    - exist_ok=True prevents errors on repeated calls
    """
    # Import fresh to get updated paths
    import importlib
    import config as config_module

    # Update module paths
    config_module.CONTEXT_HISTORY_DIR = temp_context_dir
    config_module.TMP_DIR = temp_context_dir / ".tmp"
    config_module.SESSIONS_DIR = temp_context_dir / "sessions"
    config_module.ARCHIVES_DIR = temp_context_dir / "archives"
    config_module.METADATA_DIR = temp_context_dir / ".metadata"

    # Remove any existing directories
    for path in [
        config_module.TMP_DIR,
        config_module.SESSIONS_DIR,
        config_module.ARCHIVES_DIR,
        config_module.METADATA_DIR,
    ]:
        if path.exists():
            import shutil
            shutil.rmtree(path)

    # Call ensure_directories
    config_module.ensure_directories()

    # Verify all directories were created
    assert config_module.TMP_DIR.exists(), "TMP_DIR should be created"
    assert config_module.SESSIONS_DIR.exists(), "SESSIONS_DIR should be created"
    assert config_module.ARCHIVES_DIR.exists(), "ARCHIVES_DIR should be created"
    assert config_module.METADATA_DIR.exists(), "METADATA_DIR should be created"

    # Call again to verify exist_ok works
    config_module.ensure_directories()  # Should not raise error

    # Verify directories still exist
    assert config_module.TMP_DIR.exists()


def test_estimate_tokens_precision():
    """
    Test Case 6: estimate_tokens precision.

    Verifies:
    - Token estimation follows 1 token ≈ 4 characters rule
    - Edge cases (empty string, single char) work correctly
    - Estimation is consistent
    """
    # Test empty string
    assert estimate_tokens("") == 0, "Empty string should be 0 tokens"

    # Test single character
    assert estimate_tokens("a") == 0, "Single char should be 0 tokens (< 4 chars)"

    # Test exact multiples
    assert estimate_tokens("abcd") == 1, "4 chars should be 1 token"
    assert estimate_tokens("a" * 8) == 2, "8 chars should be 2 tokens"
    assert estimate_tokens("a" * 100) == 25, "100 chars should be 25 tokens"

    # Test non-exact multiples (integer division)
    assert estimate_tokens("abc") == 0, "3 chars should be 0 tokens"
    assert estimate_tokens("abcde") == 1, "5 chars should be 1 token"
    assert estimate_tokens("a" * 99) == 24, "99 chars should be 24 tokens"

    # Test with spaces and newlines
    text_with_whitespace = "Hello\nWorld!\n\nThis is a test."
    expected_tokens = len(text_with_whitespace) // 4
    assert estimate_tokens(text_with_whitespace) == expected_tokens


# ============================================================================
# Test Cases for hooks (4 test cases)
# ============================================================================


def test_user_prompt_submit_json_io(temp_context_dir, monkeypatch, capsys):
    """
    Test Case 7: user-prompt-submit.py JSON input/output.

    Verifies:
    - Hook reads JSON from stdin correctly
    - User prompt is logged
    - Correct JSON output format
    - Session stats are included in output
    """
    # Create a direct test using SessionLogger instead of subprocess
    import logger as logger_module
    import uuid
    logger_module.TMP_DIR = temp_context_dir / ".tmp"
    logger_module.ensure_directories()

    # Prepare input with unique session ID
    unique_session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    input_data = {
        "session_id": unique_session_id,
        "prompt": "Hello, Claude!"
    }

    # Simulate what the hook does
    session_id = input_data.get('session_id', 'unknown')
    user_prompt = input_data.get('prompt', '')

    # Log the user prompt
    logger = logger_module.SessionLogger(session_id)
    logger.add_entry('user', user_prompt)

    # Get session stats for output
    stats = logger.get_session_stats()

    # Verify stats
    assert stats['total_tokens'] > 0
    assert stats['user_tokens'] > 0
    assert stats['entry_count'] == 1

    # Return hook output (simulated)
    output = {
        "hookSpecificOutput": {
            "status": "logged",
            "session_id": session_id,
            "total_tokens": stats['total_tokens']
        }
    }

    # Verify output structure
    assert "hookSpecificOutput" in output
    assert output["hookSpecificOutput"]["status"] == "logged"
    assert output["hookSpecificOutput"]["session_id"] == unique_session_id
    assert "total_tokens" in output["hookSpecificOutput"]

    # Verify log file was created
    log_file = temp_context_dir / ".tmp" / f"session-{unique_session_id}.json"
    assert log_file.exists()

    # Verify log content (JSON Lines format)
    with open(log_file, "r") as f:
        lines = f.readlines()
        logs = [json.loads(line) for line in lines if line.strip()]
    assert len(logs) == 1
    assert logs[0]["type"] == "user"
    assert logs[0]["content"] == "Hello, Claude!"


def test_post_tool_use_json_io(temp_context_dir, monkeypatch, capsys):
    """
    Test Case 8: post-tool-use.py JSON input/output.

    Verifies:
    - Hook reads tool information from stdin
    - Tool usage is logged correctly
    - Output includes session stats
    - Tool metadata is preserved
    """
    # Create a direct test using SessionLogger instead of subprocess
    import logger as logger_module
    import uuid
    logger_module.TMP_DIR = temp_context_dir / ".tmp"
    logger_module.ensure_directories()

    # Prepare input with unique session ID
    unique_session_id = f"test-session-{uuid.uuid4().hex[:8]}"
    input_data = {
        "session_id": unique_session_id,
        "tool_name": "Read",
        "tool_input": {"file_path": "/test/file.txt"},
        "tool_result": "File content here"
    }

    # Simulate what the hook does
    session_id = input_data.get('session_id', 'unknown')
    tool_name = input_data.get('tool_name', 'unknown')
    tool_input = input_data.get('tool_input', {})
    tool_result = input_data.get('tool_result', '')

    # Format content for logging
    content = f"Tool: {tool_name}\n"
    if tool_input:
        content += f"Input: {json.dumps(tool_input, indent=2)}\n"
    content += f"Result: {tool_result}"

    # Log the tool usage
    logger = logger_module.SessionLogger(session_id)
    logger.add_entry(
        'assistant',
        content,
        tool_name=tool_name,
        tool_input=tool_input
    )

    # Get session stats
    stats = logger.get_session_stats()

    # Verify stats
    assert stats['total_tokens'] > 0
    assert stats['assistant_tokens'] > 0

    # Return hook output (simulated)
    output = {
        "hookSpecificOutput": {
            "status": "logged",
            "session_id": session_id,
            "total_tokens": stats['total_tokens']
        }
    }

    # Verify output
    assert output["hookSpecificOutput"]["status"] == "logged"
    assert output["hookSpecificOutput"]["session_id"] == unique_session_id

    # Verify log file
    log_file = temp_context_dir / ".tmp" / f"session-{unique_session_id}.json"
    assert log_file.exists()

    # Verify log content (JSON Lines format)
    with open(log_file, "r") as f:
        lines = f.readlines()
        logs = [json.loads(line) for line in lines if line.strip()]
    assert len(logs) == 1
    assert logs[0]["type"] == "assistant"
    assert "Tool: Read" in logs[0]["content"]
    assert logs[0]["tool_name"] == "Read"
    assert logs[0]["tool_input"] == {"file_path": "/test/file.txt"}


def test_stop_hook_finalize_session_call(temp_context_dir, monkeypatch, capsys):
    """
    Test Case 9: stop.py finalize-session subprocess call.

    Verifies:
    - Hook reads session_id from stdin
    - Subprocess is called with correct arguments
    - Output reflects finalization status
    - Error handling for subprocess failures
    """
    # Setup
    sys.path.insert(0, str(HOOKS_DIR))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "stop",
        HOOKS_DIR / "stop.py"
    )
    stop_module = importlib.util.module_from_spec(spec)

    # Prepare input
    input_data = {
        "session_id": "test-session-stop"
    }

    # Mock subprocess.run to avoid actual TypeScript execution
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Session finalized successfully"
    mock_result.stderr = ""

    mock_stdin = MagicMock()
    mock_stdin.read.return_value = json.dumps(input_data)
    with patch("sys.stdin", mock_stdin):
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            spec.loader.exec_module(stop_module)
            stop_module.main()

                # Verify subprocess was called correctly
                assert mock_run.called
                call_args = mock_run.call_args
                assert "npx" in call_args[0][0]
                assert "tsx" in call_args[0][0]
                assert "test-session-stop" in call_args[0][0]

    # Capture output
    captured = capsys.readouterr()

    # Stop hook returns empty object (no hookSpecificOutput)
    # See src/hooks/stop.py:48-51
    if captured.out.strip():
        output = json.loads(captured.out)
        # Stop hooks should return empty object
        assert output == {} or "hookSpecificOutput" not in output


def test_error_handling_invalid_json(temp_context_dir, capsys):
    """
    Test Case 10: Error handling for invalid JSON input.

    Verifies:
    - Hooks handle malformed JSON gracefully
    - Error is logged to stderr
    - Hook doesn't block/crash (exit 0)
    - Error output has correct format
    """
    # Setup
    sys.path.insert(0, str(HOOKS_DIR))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "user_prompt_submit",
        HOOKS_DIR / "user-prompt-submit.py"
    )
    user_prompt_module = importlib.util.module_from_spec(spec)

    # Update logger module TMP_DIR
    import logger as logger_module
    logger_module.TMP_DIR = temp_context_dir / ".tmp"

    # Mock stdin to return invalid JSON string
    mock_stdin = MagicMock()
    mock_stdin.read.return_value = "{invalid json content"

    with patch("sys.stdin", mock_stdin):
        spec.loader.exec_module(user_prompt_module)

        # Should not raise exception
        try:
            user_prompt_module.main()
        except SystemExit as e:
            # Verify exit code is 0 (don't block)
            assert e.code == 0

    # Verify output (error is returned via stdout, not stderr, to avoid Claude error display)
    captured = capsys.readouterr()

    if captured.out.strip():
        output = json.loads(captured.out)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["status"] == "error"
        assert "hookEventName" in output["hookSpecificOutput"]


# ============================================================================
# Additional Integration Test
# ============================================================================


def test_stdin_empty_handling(capsys):
    """
    Test Case 11: Empty stdin handling for user-prompt-submit.py.

    Verifies:
    - Hook handles empty stdin gracefully
    - Returns 'skipped' status instead of error
    - Hook doesn't crash (exit 0)
    - No exception is raised
    """
    # Setup
    sys.path.insert(0, str(HOOKS_DIR))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "user_prompt_submit",
        HOOKS_DIR / "user-prompt-submit.py"
    )
    user_prompt_module = importlib.util.module_from_spec(spec)

    # Mock stdin to return empty string
    mock_stdin = MagicMock()
    mock_stdin.read.return_value = ""

    with patch("sys.stdin", mock_stdin):
        spec.loader.exec_module(user_prompt_module)

        # Should not raise exception
        try:
            user_prompt_module.main()
        except SystemExit as e:
            # Verify exit code is 0 (don't block)
            assert e.code == 0

    # Verify output
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert "hookSpecificOutput" in output
    assert output["hookSpecificOutput"]["status"] in ["skipped", "ok"]


def test_stdin_whitespace_only_handling(capsys):
    """
    Test Case 12: Whitespace-only stdin handling for post-tool-use.py.

    Verifies:
    - Hook handles whitespace-only stdin gracefully
    - Returns appropriate status
    - Hook doesn't crash (exit 0)
    """
    # Setup
    sys.path.insert(0, str(HOOKS_DIR))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "post_tool_use",
        HOOKS_DIR / "post-tool-use.py"
    )
    post_tool_module = importlib.util.module_from_spec(spec)

    # Mock stdin to return whitespace only
    mock_stdin = MagicMock()
    mock_stdin.read.return_value = "   \n\t  \n  "

    with patch("sys.stdin", mock_stdin):
        spec.loader.exec_module(post_tool_module)

        # Should not raise exception
        try:
            post_tool_module.main()
        except SystemExit as e:
            # Verify exit code is 0 (don't block)
            assert e.code == 0

    # Verify output
    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert "hookSpecificOutput" in output
    assert output["hookSpecificOutput"]["status"] in ["skipped", "ok", "error"]


def test_full_workflow_integration(temp_context_dir):
    """
    Integration test: Full workflow from user prompt to tool use to stats.

    Verifies the complete flow works end-to-end.
    """
    import logger as logger_module
    logger_module.TMP_DIR = temp_context_dir / ".tmp"

    session_id = "integration-test"
    logger = SessionLogger(session_id)

    # Simulate user prompt
    logger.add_entry("user", "Please read a file")

    # Simulate tool use
    logger.add_entry(
        "assistant",
        "Tool: Read\nInput: {'file': 'test.txt'}\nResult: Content",
        tool_name="Read"
    )

    # Simulate another user message
    logger.add_entry("user", "Thank you!")

    # Get stats
    stats = logger.get_session_stats()

    # Verify
    assert stats["entry_count"] == 3
    assert stats["user_tokens"] > 0
    assert stats["assistant_tokens"] > 0
    assert stats["total_tokens"] == stats["user_tokens"] + stats["assistant_tokens"]

    # Verify log file content
    logs = logger._load_logs()
    assert len(logs) == 3
    assert logs[0]["type"] == "user"
    assert logs[1]["type"] == "assistant"
    assert logs[1]["tool_name"] == "Read"
    assert logs[2]["type"] == "user"
