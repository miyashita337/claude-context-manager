#!/usr/bin/env python3
"""Hook for capturing user prompts before submission to Claude.

P0: Rule-based topic deviation detection (Issue #28)
- Reads transcript_path for recent conversation context
- Warns (never blocks) when clearly off-topic content is detected
"""

import json
import sys
from pathlib import Path

# Add shared directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'shared'))

from logger import SessionLogger

# --- Topic Detection Constants ---

# Off-topic keyword patterns (日本語・English)
# Must NOT appear together with tech keywords to trigger warning
_OFF_TOPIC = [
    # 天気・気象
    '天気', '気温', '台風', '気候', '天候', '晴れ', '曇り', '降水',
    # ニュース・時事・政治
    'ニュース', '時事', '政治', '選挙', '事件', '事故', '芸能',
    # 金融・株式
    '株価', '為替', '仮想通貨', 'bitcoin', 'btc', '投資信託',
    # 料理・食事
    'レシピ', '食べ物', 'ランチ', 'ディナー', '献立', '食材',
    # エンタメ・雑談
    'アニメ', 'マンガ', 'スポーツ', '野球', 'サッカー', '競馬',
]

# Tech/work-related keywords that override off-topic detection
_TECH = [
    # コーディング全般
    'コード', '実装', 'バグ', 'エラー', 'デバッグ', 'テスト', 'リファクタ',
    'ファイル', '関数', 'クラス', 'メソッド', 'モジュール', 'ライブラリ',
    # Git / CI
    'git', 'commit', 'push', 'pull', 'branch', 'merge', 'pr', 'issue',
    # 言語・フレームワーク
    'python', 'typescript', 'javascript', 'bash', 'shell', 'sql',
    'api', 'json', 'yaml', 'toml', 'hook', 'cli', 'sdk',
    # 作業動詞
    'インストール', '設定', 'ビルド', 'デプロイ', '修正', '追加', '削除',
    'import', 'def ', 'class ', 'return', 'fix', 'feat', 'refactor',
    # このプロジェクト固有
    'セッション', 'analytics', 'hook', 'claude', 'llm', 'token',
]


def read_recent_user_messages(transcript_path: str, max_messages: int = 5) -> list[str]:
    """Read last N user messages from session JSONL transcript."""
    path = Path(transcript_path)
    if not path.exists():
        return []
    messages = []
    try:
        with open(path, errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get('type') == 'user':
                    content = event.get('message', {}).get('content', '')
                    if isinstance(content, str) and content.strip():
                        messages.append(content[:300])
    except Exception:
        pass
    return messages[-max_messages:]


def detect_topic_deviation(current_prompt: str, recent_messages: list[str]) -> dict:
    """Rule-based off-topic detection (P0).

    Returns:
        {"is_deviation": bool, "reason": str}
    """
    text = (current_prompt + ' ' + ' '.join(recent_messages)).lower()
    prompt_lower = current_prompt.lower()

    # Tech keyword present → always PASS (prevents false positives like "天気予報APIの実装")
    for kw in _TECH:
        if kw in text:
            return {"is_deviation": False, "reason": "tech_context"}

    # Off-topic keyword in current prompt → WARN
    found = [kw for kw in _OFF_TOPIC if kw in prompt_lower]
    if found:
        return {
            "is_deviation": True,
            "reason": f"off-topic keywords: {', '.join(found[:3])}",
        }

    return {"is_deviation": False, "reason": "ok"}


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

        # Extract session ID, user prompt, and transcript path
        session_id = input_data.get('session_id', 'unknown')
        user_prompt = input_data.get('prompt', '')
        transcript_path = input_data.get('transcript_path', '')

        # Log the user prompt
        logger = SessionLogger(session_id)
        logger.add_entry('user', user_prompt)

        # Get session stats
        stats = logger.get_session_stats()

        # --- P0: Topic deviation detection (Issue #28) ---
        additional_parts = [f"Logged user prompt. Session stats: {stats['total_tokens']} tokens"]

        try:
            recent_messages = read_recent_user_messages(transcript_path)
            detection = detect_topic_deviation(user_prompt, recent_messages)
            if detection["is_deviation"]:
                additional_parts.append(
                    f"⚠️ [話題逸脱の可能性] 現在のトピックと関連が薄いかもしれません "
                    f"({detection['reason']})。"
                    f"別トピックの場合は新しいセッションの開始を検討してください。"
                )
        except Exception:
            pass  # Detection failure must never block user

        # Return success with hookEventName
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "status": "logged",
                "additionalContext": " | ".join(additional_parts)
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
