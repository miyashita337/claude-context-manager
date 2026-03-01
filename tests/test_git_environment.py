#!/usr/bin/env python3
"""Tests for GIT_DIR contamination prevention (Issue #89).

Verifies that git remote points to the correct repository,
not a vault or other external repo contaminated via GIT_DIR.
"""

import os
import subprocess
from pathlib import Path

import pytest


def test_git_remote_is_correct_repo():
    """git remote が claude-context-manager を向いていることを確認（汚染チェック）"""
    # GIT_DIR を環境から除外して実行（空文字設定ではなくunset）
    clean_env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        env=clean_env,
        cwd=Path(__file__).parent.parent,  # プロジェクトルートで実行
    )
    assert "claude-context-manager" in result.stdout, (
        f"GIT_DIR汚染の可能性。git remote: {result.stdout.strip()!r}"
    )
