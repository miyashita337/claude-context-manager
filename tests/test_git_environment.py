#!/usr/bin/env python3
"""Git environment contamination tests.

Issue #89: 並列tmuxセッション間のGIT_DIR汚染 - Claude Codeが誤ったgitリポジトリを操作する

Root cause:
  Obsidian vault uses bare-repo + separate-worktree pattern, requiring:
    export GIT_DIR=/Users/harieshokunin/git-repos/my-vault-git
    export GIT_WORK_TREE=...iCloud.../my-vault

  When Claude Code is launched from a tmux session with these vars set,
  ALL git commands inside Claude redirect to the vault repo instead of
  claude-context-manager. This causes:
    - git remote -v → my-vault.git (wrong)
    - git log → vault backup commits (wrong)
    - CI monitoring hook → wrong repo
    - TestHookPathBoundary → iCloud path (fail)

These tests act as a regression guard: they FAIL if GIT_DIR is contaminated,
giving a clear signal that the environment is tainted.
"""

import os
import subprocess
from pathlib import Path

import pytest

# The expected remote URL for this project
EXPECTED_REMOTE = "claude-context-manager"
VAULT_REMOTE = "my-vault"

# Markers for known contamination signatures
VAULT_SIGNATURES = [
    "my-vault",
    "iCloud~md~obsidian",
    "vault backup",
    "git-repos/my-vault",
]


# =============================================================================
# Helpers
# =============================================================================

def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _is_vault_contaminated() -> tuple[bool, str]:
    """Check if GIT_DIR/GIT_WORK_TREE point to vault.

    Returns:
        (contaminated: bool, reason: str)
    """
    git_dir = os.environ.get("GIT_DIR", "")
    git_work_tree = os.environ.get("GIT_WORK_TREE", "")

    for sig in VAULT_SIGNATURES:
        if sig in git_dir:
            return True, f"GIT_DIR contains '{sig}': {git_dir}"
        if sig in git_work_tree:
            return True, f"GIT_WORK_TREE contains '{sig}': {git_work_tree}"

    return False, ""


# =============================================================================
# Tests
# =============================================================================

class TestGitEnvironmentContamination:
    """Guard against GIT_DIR/GIT_WORK_TREE vault contamination (Issue #89).

    These tests fail fast with a clear diagnostic message when the shell
    environment has vault-related GIT_DIR/GIT_WORK_TREE set.

    HOW TO FIX if these tests fail:
        # Option A: unset for current session
        unset GIT_DIR
        unset GIT_WORK_TREE

        # Option B (permanent): change vault git workflow to use alias
        # Add to ~/.zshrc:
        alias vault-git='git --git-dir="/Users/harieshokunin/git-repos/my-vault-git" \\
          --work-tree="$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/my-vault"'
        # Never export GIT_DIR/GIT_WORK_TREE globally again.
    """

    def test_git_dir_not_pointing_to_vault(self):
        """GIT_DIR env var must NOT contain vault signatures.

        Failure means: Claude Code was launched from a tmux session that had
        'export GIT_DIR=.../my-vault-git' set (Issue #89).
        """
        git_dir = os.environ.get("GIT_DIR", "")
        if not git_dir:
            pytest.skip("GIT_DIR not set — no contamination risk")

        contaminated, reason = _is_vault_contaminated()
        assert not contaminated, (
            f"\n\n"
            f"🚨 GIT_DIR汚染検出 (Issue #89)\n"
            f"理由: {reason}\n\n"
            f"修正方法:\n"
            f"  # 一時的な解消:\n"
            f"  unset GIT_DIR\n"
            f"  unset GIT_WORK_TREE\n\n"
            f"  # 恒久的な解消 (~/.zshrc に追加):\n"
            f"  alias vault-git='git --git-dir=\"/Users/harieshokunin/git-repos/my-vault-git\" "
            f"--work-tree=\"$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/my-vault\"'\n"
            f"  # GIT_DIR/GIT_WORK_TREE の export は削除してください。"
        )

    def test_git_work_tree_not_pointing_to_vault(self):
        """GIT_WORK_TREE env var must NOT contain vault/iCloud paths."""
        git_work_tree = os.environ.get("GIT_WORK_TREE", "")
        if not git_work_tree:
            pytest.skip("GIT_WORK_TREE not set — no contamination risk")

        for sig in VAULT_SIGNATURES:
            assert sig not in git_work_tree, (
                f"\n\n"
                f"🚨 GIT_WORK_TREE汚染検出 (Issue #89)\n"
                f"GIT_WORK_TREE='{git_work_tree}' に '{sig}' を検出。\n"
                f"修正: unset GIT_DIR && unset GIT_WORK_TREE"
            )

    def test_git_remote_is_claude_context_manager(self):
        """git remote origin must point to claude-context-manager, not my-vault.

        This is the definitive check: even if GIT_DIR looks clean,
        the actual remote URL confirms which repo git is operating on.
        """
        result = _git("remote", "get-url", "origin", check=False)
        if result.returncode != 0:
            pytest.skip(f"git remote failed (may be offline): {result.stderr}")

        remote_url = result.stdout.strip()

        assert VAULT_REMOTE not in remote_url, (
            f"\n\n"
            f"🚨 git remote が vault を指しています (Issue #89)\n"
            f"実際のremote: {remote_url}\n"
            f"期待するremote: *{EXPECTED_REMOTE}*\n\n"
            f"原因: GIT_DIR={os.environ.get('GIT_DIR', '(未設定)')}\n"
            f"修正: unset GIT_DIR && unset GIT_WORK_TREE"
        )

        assert EXPECTED_REMOTE in remote_url, (
            f"git remote が予期しないリポジトリを指しています: {remote_url}"
        )

    def test_git_toplevel_is_project_root(self):
        """git rev-parse --show-toplevel must return project root, not iCloud vault.

        This was the exact failure in Issue #89:
          Expected: /Users/harieshokunin/claude-context-manager (or worktree path)
          Got:      /Users/harieshokunin/Library/Mobile Documents/iCloud~md~obsidian/...
        """
        result = _git("rev-parse", "--show-toplevel", check=False)
        if result.returncode != 0:
            pytest.skip(f"git rev-parse failed: {result.stderr}")

        toplevel = result.stdout.strip()

        for sig in VAULT_SIGNATURES:
            assert sig not in toplevel, (
                f"\n\n"
                f"🚨 git toplevel が vault を指しています (Issue #89)\n"
                f"git rev-parse --show-toplevel = '{toplevel}'\n"
                f"'{sig}' を検出。\n"
                f"修正: unset GIT_DIR && unset GIT_WORK_TREE"
            )

    def test_no_vault_backup_in_recent_log(self):
        """git log must NOT show 'vault backup' commits.

        Vault backup commits look like: 'vault backup: 2026-02-28 16:04:09'
        If these appear, git is operating on the vault repo.
        """
        result = _git("log", "--oneline", "-5", check=False)
        if result.returncode != 0:
            pytest.skip(f"git log failed: {result.stderr}")

        log_output = result.stdout.strip()

        assert "vault backup" not in log_output, (
            f"\n\n"
            f"🚨 git log が vault のコミットを表示しています (Issue #89)\n"
            f"git log --oneline -5:\n{log_output}\n\n"
            f"修正: unset GIT_DIR && unset GIT_WORK_TREE"
        )
