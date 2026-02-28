#!/usr/bin/env python3
"""Tests for GIT_DIR contamination detection (Issue #89).

Verifies that:
- git remote points to the correct repository (not a vault or other external repo)
- GIT_DIR contamination warning is emitted when vault path is in GIT_DIR
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# ── module loader ──────────────────────────────────────────────────────────────
HOOKS_DIR = Path(__file__).parent.parent / "src" / "hooks"
sys.path.insert(0, str(HOOKS_DIR / "shared"))


def _load_ups():
    spec = importlib.util.spec_from_file_location(
        "user_prompt_submit",
        HOOKS_DIR / "user-prompt-submit.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── git environment tests ──────────────────────────────────────────────────────


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


def test_git_dir_vault_contamination_warning(capsys):
    """vault パスが GIT_DIR に混入した場合に警告が出ることを確認"""
    vault_path = "/Users/test/obsidian-vault/.git"
    with patch.dict(os.environ, {"GIT_DIR": vault_path}):
        # モジュールをリロードして汚染チェックを再実行
        spec = importlib.util.spec_from_file_location(
            "user_prompt_submit_contaminated",
            HOOKS_DIR / "user-prompt-submit.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    captured = capsys.readouterr()
    assert "GIT_DIR汚染検出" in captured.err, (
        f"汚染検出の警告が出力されていません。stderr: {captured.err!r}"
    )
    assert vault_path in captured.err


def test_git_dir_clean_no_warning(capsys):
    """GIT_DIR が空（またはvaultでない）場合は警告が出ないことを確認"""
    with patch.dict(os.environ, {"GIT_DIR": ""}):
        spec = importlib.util.spec_from_file_location(
            "user_prompt_submit_clean",
            HOOKS_DIR / "user-prompt-submit.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    captured = capsys.readouterr()
    assert "GIT_DIR汚染検出" not in captured.err, (
        f"誤検知が発生しています。stderr: {captured.err!r}"
    )
