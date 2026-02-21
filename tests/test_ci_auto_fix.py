#!/usr/bin/env python3
"""TDD tests for CI auto-fix loop (Issue #40).

Design contract for src/hooks/ci_auto_fix.py:
  - get_ci_status(pr_num)      -> (pending: list, failed: list) | (None, None)
  - get_failure_logs(pr_num)   -> str
  - attempt_lint_fix(repo_root) -> bool  (True if changes were made)
  - commit_and_push(repo_root, attempt_num) -> bool
  - run_ci_auto_fix(pr_num, repo_root, max_retries=3) -> int
      0 = success, 1 = max retries exhausted, 2 = push failed
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ============================================================================
# Setup path
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
HOOKS_DIR = PROJECT_ROOT / "src" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fake_pr_num():
    return "42"


@pytest.fixture
def fake_repo_root(tmp_path):
    """Minimal git repo skeleton."""
    (tmp_path / ".git").mkdir()
    return str(tmp_path)


# ============================================================================
# get_ci_status
# ============================================================================


class TestGetCiStatus:
    def test_all_passed(self, fake_pr_num):
        """全チェックが passed の場合 pending=[], failed=[] を返す。"""
        from ci_auto_fix import get_ci_status

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {"bucket": "pass", "name": "lint"},
            {"bucket": "pass", "name": "test"},
        ])

        with patch("ci_auto_fix.run", return_value=mock_result):
            pending, failed = get_ci_status(fake_pr_num)

        assert pending == []
        assert failed == []

    def test_pending_checks(self, fake_pr_num):
        """pending チェックがある場合 pending リストに含まれる。"""
        from ci_auto_fix import get_ci_status

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {"bucket": "pending", "name": "lint"},
            {"bucket": "pass",    "name": "test"},
        ])

        with patch("ci_auto_fix.run", return_value=mock_result):
            pending, failed = get_ci_status(fake_pr_num)

        assert len(pending) == 1
        assert pending[0]["name"] == "lint"
        assert failed == []

    def test_failed_checks(self, fake_pr_num):
        """failed チェックがある場合 failed リストに含まれる。"""
        from ci_auto_fix import get_ci_status

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {"bucket": "fail", "name": "lint"},
            {"bucket": "pass", "name": "test"},
        ])

        with patch("ci_auto_fix.run", return_value=mock_result):
            pending, failed = get_ci_status(fake_pr_num)

        assert failed[0]["name"] == "lint"
        assert pending == []

    def test_gh_command_fails(self, fake_pr_num):
        """gh コマンドが失敗した場合 (None, None) を返す。"""
        from ci_auto_fix import get_ci_status

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("ci_auto_fix.run", return_value=mock_result):
            pending, failed = get_ci_status(fake_pr_num)

        assert pending is None
        assert failed is None

    def test_invalid_json_returns_none(self, fake_pr_num):
        """gh が JSON でない出力を返した場合 (None, None) を返す。"""
        from ci_auto_fix import get_ci_status

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not json"

        with patch("ci_auto_fix.run", return_value=mock_result):
            pending, failed = get_ci_status(fake_pr_num)

        assert pending is None
        assert failed is None


# ============================================================================
# get_failure_logs
# ============================================================================


class TestGetFailureLogs:
    def test_returns_log_text(self, fake_pr_num):
        """失敗ランのログを返す。"""
        from ci_auto_fix import get_failure_logs

        run_list_result = MagicMock()
        run_list_result.returncode = 0
        run_list_result.stdout = "99999\n"

        log_result = MagicMock()
        log_result.returncode = 0
        log_result.stdout = "Error: lint failed on line 5\n"

        with patch("ci_auto_fix.run", side_effect=[run_list_result, log_result]):
            logs = get_failure_logs(fake_pr_num)

        assert "lint failed" in logs

    def test_no_failed_runs_returns_empty(self, fake_pr_num):
        """失敗ランがない場合は空文字列を返す。"""
        from ci_auto_fix import get_failure_logs

        run_list_result = MagicMock()
        run_list_result.returncode = 0
        run_list_result.stdout = ""  # no failed run ID

        with patch("ci_auto_fix.run", return_value=run_list_result):
            logs = get_failure_logs(fake_pr_num)

        assert logs == ""

    def test_logs_truncated_to_limit(self, fake_pr_num):
        """ログが長すぎる場合は 3000 文字以内に切り詰める。"""
        from ci_auto_fix import get_failure_logs

        run_list_result = MagicMock()
        run_list_result.returncode = 0
        run_list_result.stdout = "99999\n"

        log_result = MagicMock()
        log_result.returncode = 0
        log_result.stdout = "x" * 10000

        with patch("ci_auto_fix.run", side_effect=[run_list_result, log_result]):
            logs = get_failure_logs(fake_pr_num)

        assert len(logs) <= 3000


# ============================================================================
# attempt_lint_fix
# ============================================================================


class TestAttemptLintFix:
    def test_ruff_fixes_and_returns_true(self, fake_repo_root):
        """ruff が変更を加えた場合 True を返す。"""
        from ci_auto_fix import attempt_lint_fix

        ruff_fix    = MagicMock(returncode=0)
        ruff_format = MagicMock(returncode=0)
        git_status  = MagicMock(returncode=0, stdout="M  src/foo.py\n")

        with patch("ci_auto_fix.run", side_effect=[ruff_fix, ruff_format, git_status]):
            result = attempt_lint_fix(fake_repo_root)

        assert result is True

    def test_no_changes_returns_false(self, fake_repo_root):
        """ruff 実行後に git の変更がなければ False を返す。"""
        from ci_auto_fix import attempt_lint_fix

        ruff_fix    = MagicMock(returncode=0)
        ruff_format = MagicMock(returncode=0)
        git_status  = MagicMock(returncode=0, stdout="")

        with patch("ci_auto_fix.run", side_effect=[ruff_fix, ruff_format, git_status]):
            result = attempt_lint_fix(fake_repo_root)

        assert result is False

    def test_ruff_not_found_falls_back_to_make(self, fake_repo_root):
        """ruff が存在しない場合 make lint-fix にフォールバックする。"""
        from ci_auto_fix import attempt_lint_fix

        # ruff --fix が "command not found" 相当の returncode=127
        ruff_fix    = MagicMock(returncode=127)
        make_fix    = MagicMock(returncode=0)
        git_status  = MagicMock(returncode=0, stdout="M  src/foo.py\n")

        with patch("ci_auto_fix.run", side_effect=[ruff_fix, make_fix, git_status]):
            result = attempt_lint_fix(fake_repo_root)

        assert result is True


# ============================================================================
# commit_and_push
# ============================================================================


class TestCommitAndPush:
    def test_success(self, fake_repo_root):
        """変更があればコミット・プッシュして True を返す。"""
        from ci_auto_fix import commit_and_push

        git_add    = MagicMock(returncode=0)
        git_commit = MagicMock(returncode=0)
        git_push   = MagicMock(returncode=0)

        with patch("ci_auto_fix.run", side_effect=[git_add, git_commit, git_push]):
            result = commit_and_push(fake_repo_root, attempt_num=1)

        assert result is True

    def test_nothing_to_commit_returns_false(self, fake_repo_root):
        """コミットするものがない場合 False を返す（exit code 1 = nothing to commit）。"""
        from ci_auto_fix import commit_and_push

        git_add    = MagicMock(returncode=0)
        git_commit = MagicMock(returncode=1)  # nothing to commit

        with patch("ci_auto_fix.run", side_effect=[git_add, git_commit]):
            result = commit_and_push(fake_repo_root, attempt_num=1)

        assert result is False

    def test_push_fails_returns_false(self, fake_repo_root):
        """push が失敗した場合 False を返す。"""
        from ci_auto_fix import commit_and_push

        git_add    = MagicMock(returncode=0)
        git_commit = MagicMock(returncode=0)
        git_push   = MagicMock(returncode=1, stderr="rejected")

        with patch("ci_auto_fix.run", side_effect=[git_add, git_commit, git_push]):
            result = commit_and_push(fake_repo_root, attempt_num=1)

        assert result is False

    def test_commit_message_includes_attempt_num(self, fake_repo_root):
        """コミットメッセージに attempt 番号が含まれる。"""
        from ci_auto_fix import commit_and_push

        calls = []

        def capture_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0)

        with patch("ci_auto_fix.run", side_effect=capture_run):
            commit_and_push(fake_repo_root, attempt_num=2)

        commit_cmd = next(c for c in calls if "commit" in c)
        assert "2" in commit_cmd


# ============================================================================
# run_ci_auto_fix (main loop)
# ============================================================================


class TestRunCiAutoFix:
    def test_ci_passes_immediately_returns_0(self, fake_pr_num, fake_repo_root):
        """最初のチェックで CI が通れば 0 を返す。"""
        from ci_auto_fix import run_ci_auto_fix

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", return_value=([], [])),
        ):
            result = run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        assert result == 0

    def test_pending_then_pass_returns_0(self, fake_pr_num, fake_repo_root):
        """pending → pass の遷移を正しく処理して 0 を返す。"""
        from ci_auto_fix import run_ci_auto_fix

        pending_check = [{"bucket": "pending", "name": "lint"}]
        # 1回目: pending, 2回目: all clear
        statuses = [
            (pending_check, []),
            ([], []),
        ]

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", side_effect=statuses),
        ):
            result = run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        assert result == 0

    def test_fix_and_pass_on_retry_returns_0(self, fake_pr_num, fake_repo_root):
        """CI 失敗 → 自動修正 → 2回目で CI 通過 → 0 を返す。"""
        from ci_auto_fix import run_ci_auto_fix

        failed_check = [{"bucket": "fail", "name": "lint"}]
        statuses = [
            ([], failed_check),  # 1回目: 失敗
            ([], []),             # 2回目: 成功
        ]

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", side_effect=statuses),
            patch("ci_auto_fix.get_failure_logs", return_value="lint error"),
            patch("ci_auto_fix.attempt_lint_fix", return_value=True),
            patch("ci_auto_fix.commit_and_push", return_value=True),
        ):
            result = run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        assert result == 0

    def test_max_retries_exhausted_returns_1(self, fake_pr_num, fake_repo_root):
        """3回リトライしても CI が通らなければ 1 を返す。"""
        from ci_auto_fix import run_ci_auto_fix

        failed_check = [{"bucket": "fail", "name": "lint"}]

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", return_value=([], failed_check)),
            patch("ci_auto_fix.get_failure_logs", return_value="lint error"),
            patch("ci_auto_fix.attempt_lint_fix", return_value=True),
            patch("ci_auto_fix.commit_and_push", return_value=True),
        ):
            result = run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        assert result == 1

    def test_push_fails_returns_2(self, fake_pr_num, fake_repo_root):
        """push に失敗した場合 2 を返す。"""
        from ci_auto_fix import run_ci_auto_fix

        failed_check = [{"bucket": "fail", "name": "lint"}]

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", return_value=([], failed_check)),
            patch("ci_auto_fix.get_failure_logs", return_value="lint error"),
            patch("ci_auto_fix.attempt_lint_fix", return_value=True),
            patch("ci_auto_fix.commit_and_push", return_value=False),
        ):
            result = run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        assert result == 2

    def test_retry_count_respected(self, fake_pr_num, fake_repo_root):
        """get_ci_status の呼び出し回数が max_retries + 1 以内に収まる。"""
        from ci_auto_fix import run_ci_auto_fix

        failed_check = [{"bucket": "fail", "name": "lint"}]
        status_mock = MagicMock(return_value=([], failed_check))

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", status_mock),
            patch("ci_auto_fix.get_failure_logs", return_value="err"),
            patch("ci_auto_fix.attempt_lint_fix", return_value=True),
            patch("ci_auto_fix.commit_and_push", return_value=True),
        ):
            run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        # 初回チェック + リトライ3回 = 4回まで
        assert status_mock.call_count <= 4

    def test_log_file_written(self, fake_pr_num, fake_repo_root, tmp_path):
        """実行ログが ~/.claude/ci-watch.log に書き込まれる。"""
        from ci_auto_fix import run_ci_auto_fix

        log_path = tmp_path / "ci-watch.log"

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", return_value=([], [])),
            patch("ci_auto_fix.LOG_FILE", log_path),
        ):
            run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        assert log_path.exists()
        assert "PR" in log_path.read_text() or fake_pr_num in log_path.read_text()

    def test_no_fix_possible_returns_1(self, fake_pr_num, fake_repo_root):
        """ruff も claude も変更なし → exit 2 ではなく 1（修正不可）を返す。"""
        from ci_auto_fix import run_ci_auto_fix

        failed_check = [{"bucket": "fail", "name": "lint"}]

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", return_value=([], failed_check)),
            patch("ci_auto_fix.get_failure_logs", return_value="logic error"),
            patch("ci_auto_fix.attempt_lint_fix", return_value=False),
            patch("ci_auto_fix.attempt_claude_fix"),
            patch("ci_auto_fix._has_changes", return_value=False),
        ):
            result = run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        assert result == 1

    def test_max_retries_display_no_overflow(self, fake_pr_num, fake_repo_root, tmp_path):
        """max retries 到達時にログが '4/3' などの overflow 表示にならない。"""
        from ci_auto_fix import run_ci_auto_fix

        log_path = tmp_path / "ci-watch.log"
        failed_check = [{"bucket": "fail", "name": "lint"}]

        with (
            patch("ci_auto_fix.time.sleep"),
            patch("ci_auto_fix.get_ci_status", return_value=([], failed_check)),
            patch("ci_auto_fix.get_failure_logs", return_value="err"),
            patch("ci_auto_fix.attempt_lint_fix", return_value=True),
            patch("ci_auto_fix.commit_and_push", return_value=True),
            patch("ci_auto_fix.LOG_FILE", log_path),
        ):
            run_ci_auto_fix(fake_pr_num, fake_repo_root, max_retries=3)

        log_content = log_path.read_text()
        # "4/3" のような max を超えた表示が出ていないこと
        assert "4/3" not in log_content
