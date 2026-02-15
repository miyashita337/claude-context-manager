#!/usr/bin/env python3
"""Hook for capturing Claude's tool usage and responses."""

import json
import sys
from pathlib import Path

# Add shared directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'shared'))

from logger import SessionLogger


def main():
    """Main hook entry point."""
    try:
        # Read hook input from stdin
        stdin_content = sys.stdin.read()

        # Handle empty stdin gracefully
        if not stdin_content or not stdin_content.strip():
            output = {
                "hookSpecificOutput": {
                    "status": "skipped",
                    "reason": "empty stdin"
                }
            }
            print(json.dumps(output))
            sys.exit(0)

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

        # Get session stats
        stats = logger.get_session_stats()

        # Return hook output
        output = {
            "hookSpecificOutput": {
                "status": "logged",
                "session_id": session_id,
                "total_tokens": stats['total_tokens']
            }
        }

        print(json.dumps(output))

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

        # Return error status but to stdout (not stderr) to avoid Claude error display
        error_output = {
            "hookSpecificOutput": {
                "status": "error",
                "error": str(e)
            }
        }
        print(json.dumps(error_output))
        sys.exit(0)  # Don't block Claude


if __name__ == '__main__':
    main()
