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

# Question scatter detection markers (Issue #96)
_QUESTION_MARKERS = [
    '？', '?',
    'なぜ', 'どうして', 'なんで',
    'どう違う', '違いは', '比較',
    'それぞれ', '各々',
    'あと、', 'ついでに', 'もう一つ',
]


def read_user_messages(transcript_path: str) -> list[str]:
    """Read ALL user messages (chronological) from session JSONL transcript."""
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
    return messages


def _query_topic_server(prompt: str, session_id: str, transcript_path: str) -> dict:
    """P1: Query embedding server for similarity-based topic detection.

    Returns:
        {"available": True, "is_deviation": bool, "similarity": float, "reason": str}
        {"available": False, "reason": str}  ← server not running → fall back to P0
    """
    import http.client

    all_messages = read_user_messages(transcript_path)
    baseline_messages = all_messages[:3]   # first 3 = session intent

    payload = json.dumps({
        "prompt": prompt,
        "session_id": session_id,
        "baseline_messages": baseline_messages,
    }).encode()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", 8765, timeout=2)
        conn.request("POST", "/similarity", body=payload,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = json.loads(resp.read())
        conn.close()
        return {"available": True, **data}
    except (OSError, ValueError):
        return {"available": False, "reason": "server_not_running"}


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


def detect_question_scatter(prompt: str) -> dict:
    """Detect question scatter pattern (multiple independent questions in one prompt)."""
    question_marks = prompt.count('？') + prompt.count('?')
    marker_count = sum(1 for m in _QUESTION_MARKERS if m in prompt)
    if question_marks >= 3 or marker_count >= 4:
        return {"is_scatter": True, "question_count": max(question_marks, marker_count)}
    return {"is_scatter": False, "question_count": question_marks}


def compute_question_density(transcript_path: str, window: int = 5) -> float:
    """Compute average question marks per message over recent window."""
    try:
        messages = read_user_messages(transcript_path)
    except Exception:
        return 0.0
    recent = messages[-window:]
    if not recent:
        return 0.0
    total_questions = sum(m.count('？') + m.count('?') for m in recent)
    return total_questions / len(recent)


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


def _p2_debug_log(msg: str) -> None:
    """Write a debug message to hook-debug.log (best-effort)."""
    debug_log = Path.home() / '.claude' / 'hook-debug.log'
    try:
        with open(debug_log, 'a', encoding='utf-8') as f:
            f.write(f"\n=== P2 Debug ===\n{msg}\n")
    except Exception:
        pass


def _query_llm_p2(prompt: str, baseline_messages: list[str]) -> dict:
    """P2: LLM-based judgment for gray zone cases (Haiku API).

    Called only when P1 says WARN and P0 tech veto did NOT trigger.
    WARN only — never blocks the user.

    Returns:
        {"decision": "pass"|"warn", "reason": str}
    """
    import os
    import urllib.error
    import urllib.request

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"decision": "warn", "reason": "p2_unavailable (no API key)", "judgment_failed": True}

    _SYSTEM_PROMPT = (
        "You are evaluating whether a user's new prompt is off-topic for their current work session.\n\n"
        "RULES (in priority order):\n"
        "1. Technical questions, coding, debugging, testing, refactoring → ON-TOPIC\n"
        "2. Git operations, CI/CD, documentation → ON-TOPIC\n"
        "3. Questions about a different part of the same project → ON-TOPIC\n"
        "4. Complete topic changes: weather, sports, news, casual chat, unrelated projects → OFF-TOPIC\n"
        "5. When in doubt → ON-TOPIC (false positives are more harmful than false negatives)\n\n"
        "Respond ONLY with JSON. No text outside JSON.\n"
        'ON-TOPIC:  {"ok": true}\n'
        'OFF-TOPIC: {"ok": false, "reason": "brief reason (max 20 words)"}'
    )

    baseline_text = (
        "\n".join(f"- {m[:200]}" for m in baseline_messages[:3])
        if baseline_messages
        else "(session start, no baseline)"
    )
    user_content = (
        f"Session context (initial prompts):\n{baseline_text}\n\n"
        f"New prompt to evaluate:\n{prompt[:500]}\n\n"
        "Is this new prompt on-topic for the session?"
    )

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 60,
        "system": [
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": user_content}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosemgrep: dynamic-urllib-use-detected
            resp_body = resp.read()
    except urllib.error.HTTPError as e:
        return {"decision": "warn", "reason": f"p2_api_error ({e.code})", "judgment_failed": True}
    except Exception as e:
        _p2_debug_log(f"urlopen raised {type(e).__name__}: {e}")
        return {"decision": "warn", "reason": f"p2_error: {str(e)[:50]}", "judgment_failed": True}

    if not resp_body or not resp_body.strip():
        return {"decision": "warn", "reason": "p2_empty_body", "judgment_failed": True}

    # Guard: non-JSON body (e.g. HTML from WAF/CDN returning 200 with error page)
    if not resp_body.strip().startswith((b'{', b'[')):
        return {"decision": "warn", "reason": "p2_non_json_body", "judgment_failed": True}

    try:
        data = json.loads(resp_body)
        content_list = data.get("content", [])
        if not content_list:
            return {"decision": "warn", "reason": "p2_empty_response", "judgment_failed": True}

        text = content_list[0].get("text", "")
        if not text.strip():
            return {"decision": "warn", "reason": "p2_empty_text", "judgment_failed": True}

        # Guard: Haiku returned prose instead of JSON (e.g. "I cannot determine...")
        if not text.strip().startswith(('{', '[')):
            return {"decision": "warn", "reason": "p2_non_json_text", "judgment_failed": True}

        result = json.loads(text.strip())

        if result.get("ok", True):  # missing 'ok' → default on-topic (conservative)
            return {"decision": "pass", "reason": "p2_on_topic"}
        return {"decision": "warn", "reason": f"p2_llm: {result.get('reason', 'off-topic')}"}

    except Exception as e:
        import traceback
        _p2_debug_log(
            f"inner parse error {type(e).__name__}: {e}\n"
            f"resp_body[:200]={repr(resp_body[:200])}\n"
            f"traceback:\n{traceback.format_exc()}"
        )
        return {"decision": "warn", "reason": f"p2_error: {str(e)[:50]}", "judgment_failed": True}


def _run_detection(current_prompt: str, session_id: str, transcript_path: str) -> dict:
    """Run full detection pipeline P1 → P0 veto → P2.

    Returns:
        {"is_deviation": bool, "reason": str}
    """
    # P1: embedding server（日本語対応 similarity）
    p1 = _query_topic_server(current_prompt, session_id, transcript_path)

    if p1["available"] and p1.get("reason") != "no_baseline":
        # P1: baseline あり → embedding similarity で判定
        detection = p1

        if detection.get("is_deviation"):
            # P0 veto: tech keyword があれば PASS に上書き
            # 例: "Aのバグ"→"Bのバグ" は similarity 低くても tech_context でPASS
            p0_check = detect_topic_deviation(current_prompt, [])
            if p0_check["reason"] == "tech_context":
                detection = {
                    "is_deviation": False,
                    "reason": f"p0_tech_veto (p1_sim={p1.get('similarity', '?')})",
                }
            else:
                # P1 WARN + P0 veto なし → P2 LLM 判定（グレーゾーンのみ）
                baseline = read_user_messages(transcript_path)[:3]
                p2 = _query_llm_p2(current_prompt, baseline)
                if p2["decision"] == "pass":
                    detection = {
                        "is_deviation": False,
                        "reason": f"p2_pass ({p2['reason']})",
                    }
                else:
                    detection = {
                        "is_deviation": True,
                        "reason": p2["reason"],
                        "judgment_failed": p2.get("judgment_failed", False),
                    }
    else:
        # P0 fallback: サーバー停止 or baseline未形成（セッション先頭）
        recent = read_user_messages(transcript_path)[-5:]
        detection = detect_topic_deviation(current_prompt, recent)

    return detection


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

        # --- Topic deviation detection: P1 → P0 veto → P2 ---
        additional_parts = [f"Logged user prompt. Session stats: {stats['total_tokens']} tokens"]

        try:
            detection = _run_detection(user_prompt, session_id, transcript_path)

            if detection.get("is_deviation"):
                reason = detection.get("reason", "")
                judgment_failed = detection.get("judgment_failed", False)

                # プロンプトの冒頭をモーダルに表示（どの発言が引っかかったか識別用）
                prompt_preview = user_prompt[:40].replace('\n', ' ')
                if len(user_prompt) > 40:
                    prompt_preview += "..."
                prompt_line = f"▶ 「{prompt_preview}」"

                # デフォルト値を先に設定（NameError防止 + 明示的な初期化）
                alert_title = "🔴 話題逸脱の可能性"
                alert_message = (
                    "現在のセッションのトピックと関連が薄いかもしれません。\n"
                    "別トピックの場合は新しいセッションの開始を検討してください。\n"
                    f"{prompt_line}"
                )

                if judgment_failed:
                    additional_parts.append(
                        f"🔴🔴🔴 [判定不能] LLMが話題逸脱の判定に失敗しました"
                        f" ({reason})。念のため確認してください。"
                    )
                    alert_title = "⚠️ 話題逸脱：判定不能"
                    alert_message = (
                        "LLMが判定できませんでした。\n"
                        "話題が逸脱している可能性があります。\n"
                        "念のため確認してください。\n"
                        f"{prompt_line}"
                    )
                else:
                    additional_parts.append(
                        f"🔴🔴🔴 [話題逸脱の可能性] 現在のセッションのトピックと関連が薄いかもしれません"
                        f" ({reason})。別トピックの場合は新しいセッションの開始を検討してください。"
                    )

                # AppleScriptモーダルで強制通知（バックグラウンド起動、クリックまで残る）
                try:
                    import subprocess

                    def _as_str(s: str) -> str:
                        """文字列をAppleScript文字列式に変換する。
                        ダブルクォート・バックスラッシュをエスケープし、
                        \n を AppleScript の & return & に変換する。
                        """
                        parts = [
                            '"' + p.replace('\\', '\\\\').replace('"', '\\"') + '"'
                            for p in s.split('\n')
                        ]
                        return ' & return & '.join(parts)

                    script = (
                        f'display alert {_as_str(alert_title)} '
                        f'message {_as_str(alert_message)} '
                        f'buttons {{"確認"}} '
                        f'default button "確認" '
                        f'as critical'
                    )
                    subprocess.Popen(
                        ['osascript', '-e', script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                except Exception:
                    pass  # 通知失敗はユーザーをブロックしない
        except Exception:
            pass  # Detection failure must never block user

        # --- Question scatter detection (independent of topic deviation) ---
        try:
            scatter = detect_question_scatter(user_prompt)
            density = compute_question_density(transcript_path) if transcript_path else 0.0

            if scatter["is_scatter"] or density > 3.0:
                parts = []
                if scatter["is_scatter"]:
                    parts.append(f"単発{scatter['question_count']}個検知")
                if density > 3.0:
                    parts.append(f"累積密度{density:.1f}")
                detail = "・".join(parts)
                additional_parts.append(
                    f"💡 [質問散弾パターン検知] ユーザーのプロンプトに複数の話題が"
                    f"含まれている可能性があります（{detail}）。"
                    f"対応フロー: "
                    f"(1) プロンプトを独立したタスクに分解してください"
                    f"（同一タスクの異なる側面は分けない。"
                    f"例:「バグの原因？直し方？テスト？」は1タスク） "
                    f"(2) 独立タスクが2つ以上の場合、各タスクをGitHub issueとして"
                    f"登録するかユーザーに確認してください "
                    f"(3) 承認されたら gh issue create で各タスクのissueを作成 "
                    f"(4) 最も優先度の高い質問からステップバイステップで回答"
                )
        except Exception:
            pass  # 検知失敗はユーザーをブロックしない

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
