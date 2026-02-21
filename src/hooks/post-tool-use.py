#!/usr/bin/env python3
"""Hook for capturing Claude's tool usage and responses."""

import json
import sys
from pathlib import Path

# Add shared directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'shared'))

from logger import SessionLogger


def sanitize_stdin(stdin_content: str, hook_name: str) -> str:
    """Remove non-JSON text from stdin before the first '{' or '['.

    Args:
        stdin_content: Raw stdin content
        hook_name: Name of the hook (for logging)

    Returns:
        Sanitized stdin content with non-JSON prefix removed
    """
    if not stdin_content:
        return stdin_content

    # Find first JSON character
    start_idx = -1
    for i, char in enumerate(stdin_content):
        if char in ('{', '['):
            start_idx = i
            break

    # No JSON found, return as-is (will fail JSON parse, but that's expected)
    if start_idx == -1:
        return stdin_content

    # Non-JSON text found before JSON - sanitize and log
    if start_idx > 0:
        debug_log = Path.home() / '.claude' / 'hook-debug.log'
        try:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"\n=== Stdin Sanitization ({hook_name}) ===\n")
                f.write(f"Removed {start_idx} bytes of non-JSON prefix\n")
                f.write(f"Prefix content: {repr(stdin_content[:start_idx])}\n")
        except:
            pass

        return stdin_content[start_idx:]

    return stdin_content


def main():
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        stdin_content = sys.stdin.read()

        # Handle empty stdin gracefully
        if not stdin_content or not stdin_content.strip():
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "status": "skipped"
                }
            }))
            sys.exit(0)

        # Sanitize stdin (remove non-JSON prefix from shell profile pollution)
        stdin_content = sanitize_stdin(stdin_content, "PostToolUse")

        # Parse JSON
        input_data = json.loads(stdin_content)

        # Extract session ID and tool information
        session_id = input_data.get('session_id', 'unknown')
        tool_name = input_data.get('tool_name', 'unknown')
        tool_input = input_data.get('tool_input', {})
        # Claude Code provides 'tool_response' not 'tool_result'
        tool_response = input_data.get('tool_response', input_data.get('tool_result', ''))

        # Format content for logging
        content = f"Tool: {tool_name}\n"
        if tool_input:
            content += f"Input: {json.dumps(tool_input, indent=2, ensure_ascii=False)}\n"
        # Convert tool_response to string if it's a dict
        if isinstance(tool_response, dict):
            content += f"Result: {json.dumps(tool_response, indent=2, ensure_ascii=False)}"
        else:
            content += f"Result: {tool_response}"

        # Log the tool usage
        logger = SessionLogger(session_id)
        logger.add_entry(
            'assistant',
            content,
            tool_name=tool_name,
            tool_input=tool_input
        )

        # Get session stats (for potential future use)
        stats = logger.get_session_stats()

        # Auto-monitor CI after git push or gh pr create
        additional_context = f"Logged {tool_name} tool usage. Session stats: {stats['total_tokens']} tokens"
        if tool_name == "Bash" and tool_input.get('command'):
            command = tool_input.get('command', '')
            is_push = 'git push' in command and '--dry-run' not in command
            is_pr_create = 'gh pr create' in command

            if is_push or is_pr_create:
                try:
                    import re
                    import subprocess
                    import time

                    pr_num = None
                    repo_root = None
                    branch = None

                    # Case A: gh pr create → extract PR number from response URL
                    # Response contains: https://github.com/owner/repo/pull/NUMBER
                    if is_pr_create:
                        response_text = str(tool_response)
                        m = re.search(r'/pull/(\d+)', response_text)
                        if m:
                            pr_num = m.group(1)
                            git_root_result = subprocess.run(
                                ['git', 'rev-parse', '--show-toplevel'],
                                capture_output=True, text=True, check=False,
                                cwd=Path.cwd()
                            )
                            if git_root_result.returncode == 0:
                                repo_root = git_root_result.stdout.strip()
                            branch_result = subprocess.run(
                                ['git', 'branch', '--show-current'],
                                capture_output=True, text=True, check=False,
                                cwd=repo_root or str(Path.cwd())
                            )
                            if branch_result.returncode == 0:
                                branch = branch_result.stdout.strip()

                    # Case B: git push → look up existing PR by branch
                    if is_push and not pr_num:
                        git_root_result = subprocess.run(
                            ['git', 'rev-parse', '--show-toplevel'],
                            capture_output=True, text=True, check=False,
                            cwd=Path.cwd()
                        )
                        if git_root_result.returncode == 0:
                            repo_root = git_root_result.stdout.strip()
                            branch_result = subprocess.run(
                                ['git', 'branch', '--show-current'],
                                capture_output=True, text=True, check=False,
                                cwd=repo_root
                            )
                            if branch_result.returncode == 0:
                                branch = branch_result.stdout.strip()
                                pr_result = subprocess.run(
                                    ['gh', 'pr', 'list', '--head', branch,
                                     '--json', 'number', '--jq', '.[0].number'],
                                    capture_output=True, text=True, check=False,
                                    cwd=repo_root
                                )
                                if pr_result.returncode == 0:
                                    raw = pr_result.stdout.strip()
                                    if raw and raw != 'null':
                                        pr_num = raw

                    if pr_num and repo_root:
                        signal_file = Path.home() / '.claude' / 'ci-monitoring-request.json'
                        signal_data = {
                            'pr_number': pr_num,
                            'branch': branch or '',
                            'repo_root': repo_root,
                            'timestamp': time.time()
                        }
                        with open(signal_file, 'w', encoding='utf-8') as f:
                            json.dump(signal_data, f, indent=2)

                        hooks_dir = Path(__file__).parent
                        subprocess.Popen(
                            [sys.executable, str(hooks_dir / "ci_auto_fix.py"),
                             pr_num, repo_root],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        additional_context += f" | 🔄 CI自動修正ループ起動 - PR #{pr_num} (最大3回リトライ)"
                except Exception:
                    pass

        # Return success with hookEventName
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "status": "logged",
                "additionalContext": additional_context
            }
        }))
        sys.exit(0)

    except Exception as e:
        # Log error but don't fail the hook
        # Write to debug log
        debug_log = Path.home() / '.claude' / 'hook-debug.log'
        try:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"\n=== PostToolUse Error ===\n")
                f.write(f"ERROR: {str(e)}\n")
                import traceback
                f.write(f"Traceback: {traceback.format_exc()}\n")
        except:
            pass

        # Return error status with hookEventName
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "status": "error"
            }
        }))
        sys.exit(0)  # Don't block Claude


if __name__ == '__main__':
    main()
