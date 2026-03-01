#!/usr/bin/env python3
"""
Claude Code 完了通知スクリプト
セッション内容を Claude Haiku で分析し、コンテキストに合った通知を生成する

設置先: ~/.claude/notify.py
インストール: cd ~/dev_tool/Claude && make install
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# 利用可能なサウンド一覧
SOUNDS = ["Glass", "Basso", "Hero", "Ping", "Funk", "Morse", "Pop", "Purr", "Tink"]

# 通知の自動消滅までの秒数
NOTIFICATION_TIMEOUT_SECONDS = 30


def get_api_key() -> str:
    """Keychain → 環境変数の順でAPIキーを取得"""
    try:
        result = subprocess.run(
            ["security", "find-generic-password",
             "-a", os.environ.get("USER", ""),
             "-s", "anthropic-api-key", "-w"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY", "")


def get_project_title(cwd: str) -> str:
    """cwdからworktree名またはプロジェクト名を取得"""
    parts = Path(cwd).parts
    if "worktrees" in parts:
        idx = parts.index("worktrees")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return Path(cwd).name or "Claude Code"


def cwd_to_project_folder(cwd: str) -> str:
    """cwdを ~/.claude/projects/ 以下のフォルダ名に変換する
    例: /Users/foo/proj/.claude/worktrees/bar → -Users-foo-proj--claude-worktrees-bar
    ルール: 英数字とハイフン以外をすべて - に変換する（スペース・~・_・.・/ 等）
    """
    import re
    return re.sub(r"[^a-zA-Z0-9-]", "-", cwd)


def find_latest_transcript(cwd: str) -> str:
    """cwd に対応する ~/.claude/projects/<folder>/ から最新のtranscriptを探す"""
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return ""

    # cwd からプロジェクトフォルダ名を生成して完全一致を試みる
    folder_name = cwd_to_project_folder(cwd)
    project_dir = projects_dir / folder_name

    # 完全一致しない場合は前方一致で最も近いフォルダを探す
    if not project_dir.exists():
        candidates = [d for d in projects_dir.iterdir()
                      if d.is_dir() and folder_name.startswith(d.name[:20])]
        if candidates:
            project_dir = max(candidates, key=lambda d: len(d.name))

    # プロジェクトフォルダ直下の *.jsonl のみ（subagents は除外）
    if project_dir.exists():
        files = sorted(
            [f for f in project_dir.glob("*.jsonl") if f.parent == project_dir],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        return str(files[0]) if files else ""

    return ""


def read_transcript(transcript_path: str, max_chars: int = 1500) -> str:
    """transcriptから直近のやり取りを抜粋する"""
    if not transcript_path or not Path(transcript_path).exists():
        return ""
    try:
        lines = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    msg_type = entry.get("type", "")
                    if msg_type not in ("user", "assistant"):
                        continue
                    content = entry.get("message", {})
                    text = ""
                    if isinstance(content, dict):
                        for block in content.get("content", []):
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block["text"][:300]
                                break
                    elif isinstance(content, str):
                        text = content[:300]
                    if text:
                        lines.append(f"{msg_type}: {text}")
                except (json.JSONDecodeError, KeyError):
                    continue
        # 直近のやり取りのみ抽出
        summary = "\n".join(lines[-15:])
        return summary[:max_chars]
    except Exception:
        return ""


def call_haiku(api_key: str, project_title: str, transcript: str) -> dict:
    """Claude Haiku APIを呼んで通知内容を生成"""
    import urllib.request

    prompt = f"""Claude Codeのセッションが完了しました。以下の会話内容を読んで、macOS通知バナー用の内容をJSONで返してください。

プロジェクト: {project_title}
会話内容（直近）:
{transcript if transcript else "（内容なし）"}

以下のJSONのみ返してください（説明不要）:
{{
  "subtitle": "何をしたか（日本語・最大30文字）",
  "message": "詳細（日本語・最大60文字）",
  "sound": "{'/'.join(SOUNDS)} のいずれか1つ"
}}"""

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        text = data["content"][0]["text"].strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    return {}


def make_group_id() -> str:
    """通知のグループIDを生成する（remove用）"""
    return f"claude-{int(time.time() * 1000)}"


def send_notification(
    title: str,
    subtitle: str,
    message: str,
    sound: str,
    open_url: str,
    timeout: int = NOTIFICATION_TIMEOUT_SECONDS,
    group_id: str | None = None,
):
    """terminal-notifier で通知を送信し、timeout秒後に自動削除する"""
    if group_id is None:
        group_id = make_group_id()

    cmd = [
        "terminal-notifier",
        "-title", title,
        "-subtitle", subtitle,
        "-message", message,
        "-sound", sound,
        "-open", open_url,
        "-group", group_id,
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # timeout秒後にデタッチプロセスで通知を自動削除
    if timeout > 0:
        subprocess.Popen(
            ["bash", "-c", f"sleep {timeout} && terminal-notifier -remove '{group_id}'"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def log(message: str):
    """ログに書き込む"""
    log_file = Path.home() / ".claude" / "notifications.log"
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


def main():
    # stdin から JSON を読む（notify.sh 経由で渡される）
    stdin_content = sys.stdin.read().strip()
    cwd = os.getcwd()

    if stdin_content:
        try:
            start = stdin_content.find("{")
            if start >= 0:
                data = json.loads(stdin_content[start:])
                cwd = data.get("cwd", cwd)
        except Exception:
            pass

    project_title = get_project_title(cwd)
    log(f"notify.py start: project={project_title}, cwd={cwd}")

    # Haiku でコンテキスト生成を試みる
    notification = {}
    api_key = get_api_key()

    if api_key:
        try:
            transcript_path = find_latest_transcript(cwd)
            transcript = read_transcript(transcript_path)
            log(f"transcript: {transcript_path}, chars={len(transcript)}")
            notification = call_haiku(api_key, project_title, transcript)
            log(f"Haiku result: {notification}")
        except Exception as e:
            log(f"Haiku error: {e}")

    # フォールバック値
    subtitle = notification.get("subtitle") or "作業完了しました"
    message = notification.get("message") or "セッションが終了しました"
    sound = notification.get("sound") if notification.get("sound") in SOUNDS else "Glass"

    send_notification(
        title=project_title,
        subtitle=subtitle,
        message=message,
        sound=sound,
        open_url=f"file://{cwd}",
    )

    log(f"Notified: title={project_title}, subtitle={subtitle}, sound={sound}")


if __name__ == "__main__":
    main()
