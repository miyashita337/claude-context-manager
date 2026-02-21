#!/usr/bin/env python3
"""CI Auto-Fix Loop (Issue #40).

Monitors CI status after git push and attempts automatic fixes.
Max 3 retries by default.

Return codes:
  0 = success (CI passed)
  1 = max retries exhausted
  2 = commit/push failed
"""

import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOG_FILE = Path.home() / ".claude" / "ci-watch.log"

INITIAL_WAIT = 30   # seconds before first CI check (wait for CI to kick off)
PENDING_WAIT = 15   # seconds between pending-check polls
POST_PUSH_WAIT = 30 # seconds after push before next check cycle
LOG_LIMIT = 3000    # max chars of CI failure log passed to claude

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    """Run a shell command and return CompletedProcess.

    Args:
        cmd: Command as a string (will be split via shlex) or list of args.
    """
    args = shlex.split(cmd) if isinstance(cmd, str) else cmd
    return subprocess.run(args, shell=False, capture_output=True, text=True, **kwargs)


def _log(msg: str) -> None:
    """Append a message to LOG_FILE (module-level, patchable in tests)."""
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[ci-auto-fix] {msg}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_ci_status(pr_num: str):
    """Return (pending, failed) check lists, or (None, None) on error.

    Args:
        pr_num: PR number as a string.

    Returns:
        Tuple of (pending_list, failed_list) or (None, None) on gh error / bad JSON.
    """
    result = run(f"gh pr checks {pr_num} --json bucket,name,link")
    if result.returncode != 0:
        return None, None
    try:
        checks = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, None

    pending = [c for c in checks if c.get("bucket") == "pending"]
    failed  = [c for c in checks if c.get("bucket") == "fail"]
    return pending, failed


def get_failure_logs(pr_num: str) -> str:
    """Fetch stdout from the latest failed CI run, truncated to LOG_LIMIT chars.

    Args:
        pr_num: PR number as a string.

    Returns:
        Log text (may be empty if no failed run found).
    """
    list_result = run(
        "gh run list --json databaseId,conclusion "
        "--jq '[.[] | select(.conclusion == \"failure\")] | .[0].databaseId'"
    )
    run_id = list_result.stdout.strip()
    if not run_id:
        return ""

    log_result = run(f"gh run view {run_id} --log-failed")
    return log_result.stdout[:LOG_LIMIT]


def attempt_lint_fix(repo_root: str) -> bool:
    """Run ruff (or make lint-fix fallback) and report whether changes were made.

    Strategy:
      1. `ruff check --fix .` — if exit 127 (not found), fall back to `make lint-fix`
      2. `ruff format .`      — only when ruff is available
      3. `git status --porcelain` — return True iff there are staged/unstaged changes

    Args:
        repo_root: Absolute path to the repository root.

    Returns:
        True if the working tree has changes after the fix attempt.
    """
    ruff_fix = run("ruff check --fix .", cwd=repo_root)

    if ruff_fix.returncode == 127:
        # ruff not installed — fall back to project make target
        run("make lint-fix", cwd=repo_root)
    else:
        run("ruff format .", cwd=repo_root)

    git_status = run("git status --porcelain", cwd=repo_root)
    return bool(git_status.stdout.strip())


def attempt_claude_fix(logs: str, repo_root: str) -> None:
    """Use the claude CLI to analyze and fix CI errors (best-effort).

    This is called when lint/format fixers make no changes, so the failure
    is likely a logic bug.  claude --dangerously-skip-permissions allows the
    subprocess to edit files without interactive prompts.

    Args:
        logs:      CI failure log text.
        repo_root: Absolute path to the repository root.
    """
    prompt = (
        "CI failed. Analyze and fix the following errors in the codebase. "
        "Focus on code logic fixes. Do not modify test files unless they are clearly wrong.\n\n"
        f"{logs}"
    )
    run(
        ["claude", "--dangerously-skip-permissions", "--print", prompt],
        cwd=repo_root,
    )


def commit_and_push(repo_root: str, attempt_num: int) -> bool:
    """Stage all changes, commit with an auto-fix message, and push.

    Args:
        repo_root:   Absolute path to the repository root.
        attempt_num: Current attempt number (included in the commit message).

    Returns:
        True if commit and push both succeeded.
    """
    run("git add -A", cwd=repo_root)

    commit_result = run(
        f'git commit -m "fix: CI auto-fix attempt {attempt_num}"',
        cwd=repo_root,
    )
    if commit_result.returncode != 0:
        _log("Nothing to commit")
        return False

    push_result = run("git push", cwd=repo_root)
    if push_result.returncode != 0:
        _log(f"Push failed: {push_result.stderr.strip()}")
        return False

    return True


def run_ci_auto_fix(pr_num: str, repo_root: str, max_retries: int = 3) -> int:
    """Main CI auto-fix loop.

    Flow per iteration:
      1. Wait for CI to start (INITIAL_WAIT on first pass, POST_PUSH_WAIT after push).
      2. Poll until all pending checks resolve.
      3. If all passed  → return 0.
      4. If max retries → return 1.
      5. Attempt lint fix → if no changes, try claude fix.
      6. Commit + push   → if fails, return 2.
      7. Increment attempt counter and repeat.

    Args:
        pr_num:      PR number as a string.
        repo_root:   Absolute path to the repository root.
        max_retries: Maximum number of fix+push attempts before giving up.

    Returns:
        0 = CI passed, 1 = max retries exhausted, 2 = commit/push failed.
    """
    _log(f"Starting CI auto-fix for PR #{pr_num}")
    time.sleep(INITIAL_WAIT)

    attempt = 0
    while True:
        # ── 1. Fetch current check statuses ──────────────────────────────
        pending, failed = get_ci_status(pr_num)

        if pending is None:
            # gh call failed; retry after a short pause
            time.sleep(10)
            continue

        # ── 2. Wait for pending checks to resolve ────────────────────────
        while pending:
            _log(f"  {len(pending)} checks still pending...")
            time.sleep(PENDING_WAIT)
            pending, failed = get_ci_status(pr_num)
            if pending is None:
                time.sleep(10)
                break

        # ── 3. Success path ──────────────────────────────────────────────
        if not failed:
            _log("✅ All CI checks passed!")
            return 0

        # ── 4. Max retries guard ─────────────────────────────────────────
        _log(
            f"❌ {len(failed)} CI check(s) failed "
            f"(attempt {attempt + 1}/{max_retries})"
        )
        if attempt >= max_retries:
            _log(f"⛔ Max retries ({max_retries}) reached. Manual fix required.")
            return 1

        # ── 5. Attempt auto-fix ──────────────────────────────────────────
        logs = get_failure_logs(pr_num)
        lint_fixed = attempt_lint_fix(repo_root)

        if not lint_fixed:
            _log("Lint fix made no changes, trying claude fix...")
            attempt_claude_fix(logs, repo_root)

        # ── 6. Commit + push ─────────────────────────────────────────────
        success = commit_and_push(repo_root, attempt + 1)
        if not success:
            _log("⛔ Commit/push failed. Stopping.")
            return 2

        _log(f"Pushed fix attempt {attempt + 1}")
        attempt += 1
        time.sleep(POST_PUSH_WAIT)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: ci_auto_fix.py <pr_num> <repo_root> [max_retries]",
            file=sys.stderr,
        )
        sys.exit(1)

    _pr_num    = sys.argv[1]
    _repo_root = sys.argv[2]
    _max_retries = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    sys.exit(run_ci_auto_fix(_pr_num, _repo_root, _max_retries))
