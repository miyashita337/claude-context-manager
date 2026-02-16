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


def get_check_details(pr_number: str, check_name: str, repo_root: str) -> Optional[str]:
    """Get detailed error message from a failed check."""
    try:
        result = subprocess.run(
            ['gh', 'pr', 'checks', pr_number, '--json', 'name,detailsUrl'],
            capture_output=True,
            text=True,
            check=False,
            cwd=repo_root
        )
        if result.returncode == 0:
            checks = json.loads(result.stdout)
            for check in checks:
                if check.get('name') == check_name:
                    # Get more details using gh run view
                    return None  # Will implement if needed
    except:
        pass
    return None


def apply_pre_commit_fixes(repo_root: str) -> bool:
    """Apply fixes for pre-commit hook failures.

    Returns:
        True if fixes were applied, False otherwise
    """
    log_debug(f"\n  🔍 Checking for unstaged secrets...")

    # Run pre-commit hook to identify issues
    result = subprocess.run(
        ['bash', '-c', 'git diff --cached --name-only 2>/dev/null || echo ""'],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root
    )

    if result.returncode != 0:
        return False

    staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
    if not staged_files:
        log_debug(f"  ℹ️  No staged files to check")
        return False

    # Check for .env files
    env_files = [f for f in staged_files if f.endswith('.env') or '.env.' in f]
    if env_files:
        log_debug(f"\n  🔧 Unstaging .env files: {env_files}")
        for file in env_files:
            subprocess.run(
                ['git', 'rm', '--cached', file],
                capture_output=True,
                cwd=repo_root
            )

        # Add to .gitignore if not already there
        gitignore = Path(repo_root) / '.gitignore'
        if gitignore.exists():
            content = gitignore.read_text()
            for file in env_files:
                if file not in content:
                    with open(gitignore, 'a') as f:
                        f.write(f"\n{file}\n")
                    log_debug(f"  ✅ Added {file} to .gitignore")

        return True

    return False


def apply_lint_fixes(repo_root: str) -> bool:
    """Apply automatic lint fixes using ruff.

    Returns:
        True if fixes were applied, False otherwise
    """
    log_debug(f"\n  🔍 Running ruff --fix...")

    result = subprocess.run(
        ['ruff', 'check', '--fix', '.'],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root
    )

    if result.returncode == 0 or 'fixed' in result.stdout.lower():
        log_debug(f"  ✅ Ruff auto-fix applied")
        return True

    return False


def apply_auto_fix(failed_checks: List[Dict], repo_root: str, attempt: int) -> bool:
    """Apply automatic fixes for failed CI checks.

    Following CLAUDE.md investigation checklist:
    1. Collect evidence (check error messages)
    2. Form hypotheses (search PITFALLS.md)
    3. Verify with experiments (apply safe fixes only)

    Returns:
        True if fixes were applied and committed, False otherwise
    """
    log_debug(f"\n🔧 Attempt {attempt}: Analyzing failures...")
    log_debug(f"   Following CLAUDE.md investigation checklist:")
    log_debug(f"   1. Evidence: Failed checks detected")
    log_debug(f"   2. Hypotheses: Searching PITFALLS.md for solutions")
    log_debug(f"   3. Verification: Applying safe fixes only\n")

    fixes_applied = False
    fix_descriptions = []

    for check in failed_checks:
        name = check.get('name', 'Unknown')
        conclusion = check.get('conclusion', 'Unknown')
        log_debug(f"  ❌ {name}: {conclusion}")

        # Phase 1: Search for solutions in PITFALLS.md
        solution = search_pitfalls(name, repo_root)
        if solution:
            log_debug(f"  💡 Found solution in PITFALLS.md")
            log_debug(f"     {solution[:200]}...")

        # Phase 2: Apply safe fixes based on check type
        if 'pre-commit' in name.lower() or 'security' in name.lower():
            log_debug(f"\n  🔧 Applying pre-commit fixes...")
            if apply_pre_commit_fixes(repo_root):
                fixes_applied = True
                fix_descriptions.append("Unstaged secrets and updated .gitignore")

        elif 'lint' in name.lower() or 'ruff' in name.lower():
            log_debug(f"\n  🔧 Applying lint fixes...")
            if apply_lint_fixes(repo_root):
                fixes_applied = True
                fix_descriptions.append("Applied ruff auto-fix")

        else:
            log_debug(f"  ⚠️  No auto-fix available for this check type")

    if not fixes_applied:
        log_debug(f"\n⚠️  No fixes could be applied automatically")
        return False

    # Phase 3: Commit and push fixes
    log_debug(f"\n📝 Committing fixes...")

    # Stage all changes
    subprocess.run(
        ['git', 'add', '-A'],
        capture_output=True,
        cwd=repo_root
    )

    # Create commit message
    commit_msg = f"""fix: auto-fix CI failures (attempt {attempt})

Applied fixes:
{chr(10).join('- ' + desc for desc in fix_descriptions)}

Auto-fixed by CI auto-monitor following CLAUDE.md investigation checklist.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
"""

    # Commit
    result = subprocess.run(
        ['git', 'commit', '-m', commit_msg],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root
    )

    if result.returncode != 0:
        log_debug(f"  ❌ Commit failed: {result.stderr}")
        return False

    log_debug(f"  ✅ Committed fixes")

    # Push
    result = subprocess.run(
        ['git', 'push'],
        capture_output=True,
        text=True,
        check=False,
        cwd=repo_root
    )

    if result.returncode != 0:
        log_debug(f"  ❌ Push failed: {result.stderr}")
        return False

    log_debug(f"  ✅ Pushed fixes to remote")
    log_debug(f"\n✨ Auto-fix cycle complete - waiting for CI to re-run...")

    return True


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
