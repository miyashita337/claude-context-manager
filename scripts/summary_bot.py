#!/usr/bin/env python3
"""
Summary Bot: Issue/PR作成時にポエム調サマリーをbody先頭に自動追記する
"""
import json
import os

import anthropic
import requests

MARKER_START = "<!-- summary-bot-start -->"
MARKER_END = "<!-- summary-bot-end -->"


def get_event_data() -> dict:
    event_path = os.environ["GITHUB_EVENT_PATH"]
    with open(event_path) as f:
        return json.load(f)


def already_has_summary(body: str) -> bool:
    return (body or "").startswith(MARKER_START)


def call_claude(title: str, body: str, event_type: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    target = "Issue" if event_type == "issues" else "Pull Request"
    prompt = f"""以下の{target}の内容を読んで、ポエム調・詩的な表現で3〜5行の要約を書いてください。
技術的な内容でも、比喩や詩的な言葉を使って、読む人が一瞬でエッセンスをつかめるようにしてください。
日本語で書いてください。要約のみを出力し、前置きや説明は不要です。

タイトル: {title}
本文:
{body[:2000] if body else "（本文なし）"}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def build_new_body(poem: str, original_body: str) -> str:
    poem_lines = "\n".join(f"> {line}" for line in poem.strip().splitlines())
    summary_block = f"{MARKER_START}\n> 🎭 *AIポエムサマリー*\n>\n{poem_lines}\n\n---\n{MARKER_END}\n\n"
    return summary_block + (original_body or "")


def update_issue(repo: str, number: int, new_body: str, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/issues/{number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.patch(url, json={"body": new_body}, headers=headers)
    resp.raise_for_status()


def update_pr(repo: str, number: int, new_body: str, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/pulls/{number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.patch(url, json={"body": new_body}, headers=headers)
    resp.raise_for_status()


def main() -> None:
    event_name = os.environ["GITHUB_EVENT_NAME"]
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    event_data = get_event_data()

    if event_name == "issues":
        issue = event_data["issue"]
        number = issue["number"]
        title = issue["title"]
        body = issue.get("body") or ""

        if already_has_summary(body):
            print(f"Issue #{number}: サマリー済みのためスキップ")
            return

        print(f"Issue #{number} のサマリーを生成中...")
        poem = call_claude(title, body, event_name)
        new_body = build_new_body(poem, body)
        update_issue(repo, number, new_body, token)
        print(f"Issue #{number} のbodyを更新しました")

    elif event_name == "pull_request":
        pr = event_data["pull_request"]
        number = pr["number"]
        title = pr["title"]
        body = pr.get("body") or ""

        if already_has_summary(body):
            print(f"PR #{number}: サマリー済みのためスキップ")
            return

        print(f"PR #{number} のサマリーを生成中...")
        poem = call_claude(title, body, event_name)
        new_body = build_new_body(poem, body)
        update_pr(repo, number, new_body, token)
        print(f"PR #{number} のbodyを更新しました")

    else:
        print(f"未対応のイベント: {event_name}")


if __name__ == "__main__":
    main()
