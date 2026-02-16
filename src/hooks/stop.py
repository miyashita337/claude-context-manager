#!/usr/bin/env python3
"""Hook for finalizing session when Claude Code stops."""

import json
import sys
import subprocess
from pathlib import Path

# Add shared directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'shared'))


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

        # Handle empty stdin gracefully (CRITICAL: stop.py previously lacked this guard)
        if not stdin_content or not stdin_content.strip():
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "Stop",
                    "status": "skipped"
                }
            }))
            sys.exit(0)

        # Sanitize stdin (remove non-JSON prefix from shell profile pollution)
        stdin_content = sanitize_stdin(stdin_content, "Stop")

        # Parse JSON
        input_data = json.loads(stdin_content)

        # Extract session ID
        session_id = input_data.get('session_id', 'unknown')

        # Path to TypeScript finalization script
        project_root = Path(__file__).parent.parent.parent
        ts_script = project_root / 'src' / 'cli' / 'finalize-session.ts'

        # Call TypeScript script to finalize session
        result = subprocess.run(
            ['npx', 'tsx', str(ts_script), session_id],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )

        # Log finalization result to debug log
        debug_log = Path.home() / '.claude' / 'hook-debug.log'
        try:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"\n=== Stop Hook Finalization ===\n")
                f.write(f"Session ID: {session_id}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write(f"Stdout: {result.stdout}\n")
                if result.stderr:
                    f.write(f"Stderr: {result.stderr}\n")
        except:
            pass

        # Return success with hookEventName
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "status": "session_finalized"
            }
        }))
        sys.exit(0)

    except Exception as e:
        # Log error but don't fail the hook
        debug_log = Path.home() / '.claude' / 'hook-debug.log'
        try:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"\n=== Stop Hook Error ===\n")
                f.write(f"ERROR: {str(e)}\n")
                import traceback
                f.write(f"Traceback: {traceback.format_exc()}\n")
        except:
            pass

        # Return error status with hookEventName
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "status": "error"
            }
        }))
        sys.exit(0)  # Don't block shutdown


if __name__ == '__main__':
    main()
