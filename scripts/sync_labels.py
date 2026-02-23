#!/usr/bin/env python3
"""
GitHub Labels Sync - priority_config.py に基づいてラベルを同期する

使い方:
  python3 scripts/sync_labels.py [--repo OWNER/REPO] [--dry-run]

動作:
  priority_config.py の PRIORITIES を元に GitHub ラベルを create/update する。
  既存ラベルは上書き更新、存在しないラベルは新規作成。
"""

import argparse
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from priority_config import PRIORITIES


def get_existing_labels(repo: str) -> set[str]:
    """リポジトリの既存ラベル名一覧を取得する"""
    result = subprocess.run(
        ["gh", "label", "list", "--repo", repo, "--json", "name", "--limit", "100"],
        capture_output=True,
        text=True,
        check=True,
    )
    import json
    return {item["name"] for item in json.loads(result.stdout)}


def create_or_update_label(repo: str, name: str, description: str, color: str, exists: bool, dry_run: bool) -> None:
    """ラベルを作成または更新する"""
    action = "edit" if exists else "create"
    cmd = [
        "gh", "label", action, name,
        "--description", description,
        "--color", color,
        "--repo", repo,
    ]
    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠️  失敗: {name} - {result.stderr.strip()}", file=sys.stderr)
    else:
        verb = "更新" if exists else "作成"
        print(f"  ✅ {verb}: {name} (#{color})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync GitHub labels from priority_config.py")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""),
                        help="対象リポジトリ (owner/repo)")
    parser.add_argument("--dry-run", action="store_true",
                        help="実際には変更せず、実行予定コマンドを表示する")
    args = parser.parse_args()

    if not args.repo:
        print("エラー: --repo または GITHUB_REPOSITORY 環境変数でリポジトリを指定してください", file=sys.stderr)
        sys.exit(1)

    print(f"リポジトリ: {args.repo}")
    if args.dry_run:
        print("(dry-run モード: 変更は行いません)")

    existing = get_existing_labels(args.repo)

    for p in PRIORITIES:
        exists = p.name in existing
        create_or_update_label(args.repo, p.name, p.description, p.color, exists, args.dry_run)


if __name__ == "__main__":
    main()
