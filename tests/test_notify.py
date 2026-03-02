#!/usr/bin/env python3
"""Tests for notify.py - notification auto-dismiss functionality."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Setup path to import notify module
HOOKS_DIR = Path(__file__).parent.parent / "src" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import notify


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_popen():
    """Mock subprocess.Popen for notification tests."""
    with patch("notify.subprocess.Popen") as mock:
        mock.return_value = MagicMock()
        yield mock


# ============================================================================
# make_group_id tests
# ============================================================================


class TestMakeGroupId:
    """Tests for make_group_id()."""

    def test_returns_string_with_claude_prefix(self):
        group_id = notify.make_group_id()
        assert group_id.startswith("claude-")

    def test_contains_timestamp(self):
        before = int(time.time() * 1000)
        group_id = notify.make_group_id()
        after = int(time.time() * 1000)

        ts = int(group_id.split("-", 1)[1])
        assert before <= ts <= after

    def test_unique_ids(self):
        """Consecutive calls produce different IDs."""
        id1 = notify.make_group_id()
        # Small delay to ensure different millisecond timestamps
        time.sleep(0.002)
        id2 = notify.make_group_id()
        assert id1 != id2


# ============================================================================
# send_notification tests
# ============================================================================


class TestSendNotification:
    """Tests for send_notification() with auto-dismiss."""

    def test_sends_notification_with_group_id(self, mock_popen):
        """Notification command includes -group option."""
        notify.send_notification(
            title="test-project",
            subtitle="完了",
            message="テスト完了",
            sound="Glass",
            open_url="file:///test",
            group_id="claude-test-123",
        )

        # First call: terminal-notifier with -group
        first_call = mock_popen.call_args_list[0]
        cmd = first_call[0][0]
        assert "terminal-notifier" in cmd
        assert "-group" in cmd
        assert "claude-test-123" in cmd

    def test_spawns_remove_process(self, mock_popen):
        """After sending, spawns a detached process to remove notification."""
        notify.send_notification(
            title="test-project",
            subtitle="完了",
            message="テスト完了",
            sound="Glass",
            open_url="file:///test",
            timeout=30,
            group_id="claude-test-456",
        )

        # Should have 2 Popen calls: notification + removal
        assert mock_popen.call_count == 2

        # Second call: bash sleep + remove
        second_call = mock_popen.call_args_list[1]
        cmd = second_call[0][0]
        assert cmd[0] == "bash"
        assert cmd[1] == "-c"
        assert "sleep 30" in cmd[2]
        assert "terminal-notifier -remove 'claude-test-456'" in cmd[2]

    def test_remove_process_is_detached(self, mock_popen):
        """Remove process uses start_new_session=True to detach from parent."""
        notify.send_notification(
            title="test",
            subtitle="test",
            message="test",
            sound="Glass",
            open_url="file:///test",
            group_id="claude-detach-test",
        )

        second_call = mock_popen.call_args_list[1]
        assert second_call[1].get("start_new_session") is True

    def test_timeout_zero_skips_removal(self, mock_popen):
        """When timeout=0, no removal process is spawned."""
        notify.send_notification(
            title="test",
            subtitle="test",
            message="test",
            sound="Glass",
            open_url="file:///test",
            timeout=0,
            group_id="claude-no-remove",
        )

        # Only 1 Popen call (notification only, no removal)
        assert mock_popen.call_count == 1

    def test_custom_timeout(self, mock_popen):
        """Custom timeout value is used in sleep command."""
        notify.send_notification(
            title="test",
            subtitle="test",
            message="test",
            sound="Glass",
            open_url="file:///test",
            timeout=60,
            group_id="claude-custom-timeout",
        )

        second_call = mock_popen.call_args_list[1]
        assert "sleep 60" in second_call[0][0][2]

    def test_auto_generates_group_id_when_none(self, mock_popen):
        """When group_id is None, auto-generates one."""
        notify.send_notification(
            title="test",
            subtitle="test",
            message="test",
            sound="Glass",
            open_url="file:///test",
        )

        first_call = mock_popen.call_args_list[0]
        cmd = first_call[0][0]
        assert "-group" in cmd
        # Find the group_id value (after -group flag)
        group_idx = cmd.index("-group")
        generated_id = cmd[group_idx + 1]
        assert generated_id.startswith("claude-")

    def test_notification_command_structure(self, mock_popen):
        """Full notification command has all expected arguments."""
        notify.send_notification(
            title="my-project",
            subtitle="ビルド成功",
            message="テストがすべてパスしました",
            sound="Hero",
            open_url="file:///Users/test/project",
            group_id="claude-struct-test",
        )

        cmd = mock_popen.call_args_list[0][0][0]
        assert cmd == [
            "terminal-notifier",
            "-title", "my-project",
            "-subtitle", "ビルド成功",
            "-message", "テストがすべてパスしました",
            "-sound", "Hero",
            "-open", "file:///Users/test/project",
            "-group", "claude-struct-test",
        ]

    def test_default_timeout_is_30(self, mock_popen):
        """Default timeout uses NOTIFICATION_TIMEOUT_SECONDS (30)."""
        notify.send_notification(
            title="test",
            subtitle="test",
            message="test",
            sound="Glass",
            open_url="file:///test",
            group_id="claude-default-timeout",
        )

        second_call = mock_popen.call_args_list[1]
        assert f"sleep {notify.NOTIFICATION_TIMEOUT_SECONDS}" in second_call[0][0][2]


# ============================================================================
# get_project_title tests
# ============================================================================


class TestGetProjectTitle:
    """Tests for get_project_title()."""

    def test_worktree_path(self):
        title = notify.get_project_title("/Users/foo/proj/.claude/worktrees/my-feature")
        assert title == "my-feature"

    def test_regular_project_path(self):
        title = notify.get_project_title("/Users/foo/my-project")
        assert title == "my-project"

    def test_empty_path_fallback(self):
        title = notify.get_project_title("")
        assert title == "Claude Code"


# ============================================================================
# Constants tests
# ============================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_notification_timeout_is_30(self):
        assert notify.NOTIFICATION_TIMEOUT_SECONDS == 30

    def test_sounds_list_not_empty(self):
        assert len(notify.SOUNDS) > 0
        assert "Glass" in notify.SOUNDS
