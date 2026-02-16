#!/usr/bin/env python3
"""CI Auto-Fixer - Monitors CI and automatically fixes errors."""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict

# Add shared directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'shared'))

from logger import SessionLogger


def log_debug(message: str):
    """Log debug message to ci-watch.log."""
    log_file = Path.home() / '.claude' / 'ci-watch.log'
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")
    except:
        pass


def get_pr_number(branch: str, repo_root: str) -> Optional[str]:
    """Get PR number for the current branch."""
    try:
        result = subprocess.run(
            ['gh', 'pr', 'list', '--head', branch, '--json', 'number', '--jq', '.[0].number'],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root
        )
        if result.returncode == 0 and result.stdout.strip():
            pr_num = result.stdout.strip()
            return pr_num if pr_num != 'null' else None
    except:
        pass
    return None


def check_ci_status(pr_number: str, repo_root: str) -> Dict[str, any]:
    """Check CI status for a PR.

    Returns:
        dict with keys: 'completed', 'success', 'failed_checks'
    """
    try:
        # Get CI checks status
        result = subprocess.run(
            ['gh', 'pr', 'checks', pr_number, '--json', 'name,status,conclusion'],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root
        )

        if result.returncode != 0:
            return {'completed': False, 'success': False, 'failed_checks': []}

        checks = json.loads(result.stdout)
        if not checks:
            return {'completed': False, 'success': False, 'failed_checks': []}

        # Check if all checks are completed
        all_completed = all(check.get('status') == 'completed' for check in checks)
        if not all_completed:
            return {'completed': False, 'success': False, 'failed_checks': []}

        # Check if all checks passed
        failed_checks = [
            check for check in checks
            if check.get('conclusion') not in ['success', 'skipped']
        ]

        success = len(failed_checks) == 0

        return {
            'completed': True,
            'success': success,
            'failed_checks': failed_checks
        }
    except Exception as e:
        log_debug(f"Error checking CI status: {e}")
        return {'completed': False, 'success': False, 'failed_checks': []}


def search_pitfalls(error_signature: str, repo_root: str) -> Optional[str]:
    """Search PITFALLS.md for solutions."""
    pitfalls_file = Path(repo_root) / '.claude' / 'PITFALLS.md'
    if not pitfalls_file.exists():
        return None

    try:
        content = pitfalls_file.read_text(encoding='utf-8')
        # Simple search for error signature
        if error_signature.lower() in content.lower():
            # Extract relevant section
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if error_signature.lower() in line.lower():
                    # Get context (10 lines before and after)
                    start = max(0, i - 10)
                    end = min(len(lines), i + 30)
                    return '\n'.join(lines[start:end])
    except:
        pass

    return None


def apply_auto_fix(failed_checks: List[Dict], repo_root: str, attempt: int) -> bool:
    """Apply automatic fixes for failed CI checks.

    Returns:
        True if fixes were applied, False otherwise
    """
    log_debug(f"\n🔧 Attempt {attempt}: Analyzing failures...")

    # For now, just log what we would do
    # In a full implementation, this would:
    # 1. Analyze error messages
    # 2. Search PITFALLS.md
    # 3. Apply safe fixes
    # 4. Commit and push

    for check in failed_checks:
        name = check.get('name', 'Unknown')
        conclusion = check.get('conclusion', 'Unknown')
        log_debug(f"  ❌ {name}: {conclusion}")

        # Search for solutions
        solution = search_pitfalls(name, repo_root)
        if solution:
            log_debug(f"  💡 Found solution in PITFALLS.md")
            log_debug(f"     {solution[:100]}...")
        else:
            log_debug(f"  ⚠️  No solution found in PITFALLS.md")

    # For safety, don't actually apply fixes in this initial implementation
    # User needs to manually review and fix
    log_debug(f"\n⚠️  Auto-fix not yet implemented - manual intervention required")
    return False


def monitor_ci(pr_number: str, repo_root: str, max_retries: int = 4):
    """Monitor CI and auto-fix errors."""
    log_debug(f"\n🔍 CI Auto-Monitor started for PR #{pr_number}")
    log_debug(f"   Max retries: {max_retries}")
    log_debug(f"   Repo: {repo_root}")

    attempt = 0
    poll_interval = 30  # Check every 30 seconds
    max_polls = 60  # Max 30 minutes (60 * 30s)

    for poll in range(max_polls):
        log_debug(f"\n📊 Polling CI status... ({poll + 1}/{max_polls})")

        status = check_ci_status(pr_number, repo_root)

        if not status['completed']:
            log_debug(f"   ⏳ CI still running...")
            time.sleep(poll_interval)
            continue

        # CI completed
        if status['success']:
            log_debug(f"\n✅ CI PASSED - All checks successful!")
            return True

        # CI failed
        log_debug(f"\n❌ CI FAILED - {len(status['failed_checks'])} check(s) failed")

        if attempt >= max_retries:
            log_debug(f"\n🛑 Max retries ({max_retries}) reached - stopping auto-fix")
            log_debug(f"\n📋 Failed checks:")
            for check in status['failed_checks']:
                log_debug(f"   - {check.get('name')}: {check.get('conclusion')}")
            return False

        # Try to auto-fix
        attempt += 1
        fixes_applied = apply_auto_fix(status['failed_checks'], repo_root, attempt)

        if not fixes_applied:
            log_debug(f"\n🛑 No auto-fixes available - manual intervention required")
            return False

        # Wait for new CI run
        log_debug(f"\n⏳ Waiting for CI to re-run after auto-fix...")
        time.sleep(60)  # Wait 1 minute for CI to start

    log_debug(f"\n⏱️  Timeout: CI did not complete within 30 minutes")
    return False


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: ci-auto-fixer.py <pr_number> <repo_root>", file=sys.stderr)
        sys.exit(1)

    pr_number = sys.argv[1]
    repo_root = sys.argv[2]
    max_retries = int(sys.argv[3]) if len(sys.argv) > 3 else 4

    try:
        success = monitor_ci(pr_number, repo_root, max_retries)
        sys.exit(0 if success else 1)
    except Exception as e:
        log_debug(f"\n💥 Error in CI auto-fixer: {e}")
        import traceback
        log_debug(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
