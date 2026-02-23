#!/usr/bin/env python3
"""
Issue Priority Auto-Label

GitHub Actions の issues.opened / issues.edited で起動し、
Claude が優先度を判定して GitHub ラベルを自動付与する。
summary_bot.py と同じ構造で実装。

優先度の定義は priority_config.py で一元管理。
"""
import json
import os
import re
import subprocess
import sys

import anthropic

from priority_config import DEFAULT_PRIORITY, LABEL_NAMES, PRIORITIES

VALID_PRIORITIES = LABEL_NAMES
BOT_SENDER = "github-actions[bot]"
BODY_TRUNCATE = 2000


def get_event_data() -> dict:
    """GITHUB_EVENT_PATH から GitHub イベントの JSON を読み込む"""
    with open(os.environ["GITHUB_EVENT_PATH"]) as f:
        return json.load(f)


def is_bot_edit(sender: str) -> bool:
    """github-actions[bot] による編集かチェック（無限ループ防止）"""
    return sender == BOT_SENDER


def parse_priority(text: str) -> str:
    """Claude のレスポンスから優先度ラベル名を抽出。不正値は DEFAULT_PRIORITY にフォールバック。"""
    if not text:
        return DEFAULT_PRIORITY
    stripped = text.strip()
    # 完全一致（大文字小文字を無視）
    for name in VALID_PRIORITIES:
        if stripped.lower() == name.lower():
            return name
    # 文章中から優先度名を探す（例: "High because it is a bug"）
    pattern = r"\b(" + "|".join(re.escape(n) for n in VALID_PRIORITIES) + r")\b"
    match = re.search(pattern, stripped, re.IGNORECASE)
    if match:
        # 正規の大文字小文字に正規化して返す
        matched = match.group(1).lower()
        for name in VALID_PRIORITIES:
            if name.lower() == matched:
                return name
    return DEFAULT_PRIORITY


def build_prompt(title: str, body: str) -> str:
    """Claude に送るプロンプトを生成。優先度定義は priority_config から自動生成。"""
    safe_body = (body or "")[:BODY_TRUNCATE]
    definitions = "\n".join(f"- {p.name}: {p.definition}" for p in PRIORITIES)
    valid_names = ", ".join(f'"{n}"' for n in LABEL_NAMES)
    return f"""以下の GitHub Issue の優先度を答えてください。

定義:
{definitions}

タイトル: {title}
本文:
{safe_body if safe_body else "（本文なし）"}

回答は必ず {valid_names} のいずれか 1 単語のみ出力してください。"""


def get_priority_from_claude(title: str, body: str) -> str:
    """Claude API を呼び出して優先度を判定する"""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = build_prompt(title, body)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text
    return parse_priority(raw)


def remove_priority_labels(issue_number: str, repo: str) -> None:
    """全優先度ラベルを除去（ラベル未存在時のエラーは無視）"""
    for priority in VALID_PRIORITIES:
        subprocess.run(
            [
                "gh", "issue", "edit", issue_number,
                "--remove-label", priority,
                "--repo", repo,
            ],
            capture_output=True,  # エラー出力を握りつぶす（ラベル未存在時対応）
        )


def add_priority_label(issue_number: str, repo: str, priority: str) -> None:
    """優先度ラベルを付与（失敗時は CalledProcessError を上げる）"""
    subprocess.run(
        [
            "gh", "issue", "edit", issue_number,
            "--add-label", priority,
            "--repo", repo,
        ],
        check=True,
    )


def main() -> None:
    event_data = get_event_data()
    sender = event_data.get("sender", {}).get("login", "")

    if is_bot_edit(sender):
        print("github-actions[bot] による編集のためスキップ（無限ループ防止）")
        return

    # 必須環境変数の早期バリデーション
    for key in ("ANTHROPIC_API_KEY", "GITHUB_REPOSITORY"):
        if key not in os.environ:
            print(f"必須環境変数 {key} が未設定です", file=sys.stderr)
            sys.exit(1)

    issue = event_data["issue"]
    issue_number = str(issue["number"])
    title = issue["title"]
    body = issue.get("body") or ""
    repo = os.environ["GITHUB_REPOSITORY"]

    print(f"Issue #{issue_number} の優先度を判定中...")
    priority = get_priority_from_claude(title, body)
    print(f"判定結果: {priority}")

    remove_priority_labels(issue_number, repo)
    add_priority_label(issue_number, repo, priority)
    print(f"Issue #{issue_number} に {priority} ラベルを設定しました")


if __name__ == "__main__":
    main()
