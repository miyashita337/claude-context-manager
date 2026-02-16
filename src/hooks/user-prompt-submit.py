#!/usr/bin/env python3
"""Hook for capturing user prompts before submission to Claude."""

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
                    "hookEventName": "UserPromptSubmit",
                    "status": "skipped"
                }
            }))
            sys.exit(0)

        # Sanitize stdin (remove non-JSON prefix from shell profile pollution)
        stdin_content = sanitize_stdin(stdin_content, "UserPromptSubmit")

        # Parse JSON
        input_data = json.loads(stdin_content)

        # Extract session ID and user prompt
        session_id = input_data.get('session_id', 'unknown')
        user_prompt = input_data.get('prompt', '')

        # Log the user prompt
        logger = SessionLogger(session_id)
        logger.add_entry('user', user_prompt)

        # Get session stats (for potential future use)
        stats = logger.get_session_stats()

        # Return success with hookEventName
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "status": "logged",
                "additionalContext": f"Logged user prompt. Session stats: {stats['total_tokens']} tokens"
            }
        }))
        sys.exit(0)

    except Exception as e:
        # Log error but don't fail the hook
        # Write to debug log
        debug_log = Path.home() / '.claude' / 'hook-debug.log'
        try:
            with open(debug_log, 'a', encoding='utf-8') as f:
                f.write(f"\n=== UserPromptSubmit Error ===\n")
                f.write(f"ERROR: {str(e)}\n")
                import traceback
                f.write(f"Traceback: {traceback.format_exc()}\n")
        except:
            pass

        # Return error status with hookEventName
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "status": "error"
            }
        }))
        sys.exit(0)  # Don't block user interaction


if __name__ == '__main__':
    main()
