#!/usr/bin/env python3
"""PreToolUse hook: block low-quality dependency additions.

Reads PreToolUse JSON from stdin. If the Bash command is a dependency-add
command (npm/pnpm/yarn/pip/uv/cargo/go), check each package against quality
thresholds (weekly downloads, last commit, license). BLOCK (exit 2) with a
reason on stderr if any package fails. Fail-open on timeout, allowlist hit,
or APPROVE_DEPS=1.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIMEOUT = 5.0
MIN_WEEKLY_DL = 10_000
MAX_COMMIT_AGE_DAYS = 180
ALLOWED_LICENSES = {
    "mit",
    "apache-2.0",
    "apache 2.0",
    "apache2.0",
    "bsd",
    "bsd-2-clause",
    "bsd-3-clause",
    "isc",
}

ALLOWLIST_PATH = Path(".claude/hooks/dep-guard-allowlist.json")

# Regex for dependency-add commands. Captures (ecosystem, rest)
CMD_PATTERNS = [
    (re.compile(r"\bnpm\s+(?:install|add|i)\b([^;|&\n]*)"), "npm"),
    (re.compile(r"\bpnpm\s+(?:install|add)\b([^;|&\n]*)"), "npm"),
    (re.compile(r"\byarn\s+add\b([^;|&\n]*)"), "npm"),
    (re.compile(r"\bpip3?\s+install\b([^;|&\n]*)"), "pypi"),
    (re.compile(r"\buv\s+(?:add|pip\s+install)\b([^;|&\n]*)"), "pypi"),
    (re.compile(r"\bcargo\s+add\b([^;|&\n]*)"), "cargo"),
    (re.compile(r"\bgo\s+get\b([^;|&\n]*)"), "go"),
]


def extract_packages(command: str) -> tuple[str, list[str]] | None:
    """Return (ecosystem, [pkgs]) or None if not a dep-add command."""
    for pat, eco in CMD_PATTERNS:
        m = pat.search(command)
        if not m:
            continue
        tail = m.group(1).strip()
        if not tail:
            return None  # bare `npm install` = lockfile install
        tokens = [t.strip("'\"") for t in tail.split() if not t.startswith("-")]
        pkgs = []
        for t in tokens:
            # strip version spec: lodash@4, requests==2.0, foo~1.0
            name = re.split(r"[@=<>~!]", t, maxsplit=1)[0]
            if eco == "npm" and t.startswith("@"):
                # scoped: @scope/pkg@ver -> @scope/pkg
                parts = t.split("@")
                name = "@" + parts[1] if len(parts) > 1 else t
            if name:
                pkgs.append(name)
        return (eco, pkgs) if pkgs else None
    return None


def _fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "dep-guard/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read())


def _commit_age_days(repo_url: str) -> float | None:
    m = re.search(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", repo_url or "")
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    data = _fetch_json(f"https://api.github.com/repos/{owner}/{repo}")
    pushed = data.get("pushed_at")
    if not pushed:
        return None
    dt = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


def _license_ok(lic: str | None) -> bool:
    if not lic:
        return False
    return lic.strip().lower() in ALLOWED_LICENSES


def check_npm(pkg: str) -> tuple[bool, str]:
    dl = _fetch_json(f"https://api.npmjs.org/downloads/point/last-week/{pkg}")
    weekly = dl.get("downloads", 0)
    if weekly < MIN_WEEKLY_DL:
        return False, f"weekly DL: {weekly:,} (< {MIN_WEEKLY_DL:,})"
    meta = _fetch_json(f"https://registry.npmjs.org/{pkg}")
    latest = meta.get("dist-tags", {}).get("latest", "")
    ver = meta.get("versions", {}).get(latest, {})
    lic = ver.get("license") or meta.get("license")
    if isinstance(lic, dict):
        lic = lic.get("type")
    if not _license_ok(lic):
        return False, f"license: {lic} (not in allowlist)"
    repo = ver.get("repository") or meta.get("repository") or {}
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    age = _commit_age_days(repo)
    if age is not None and age > MAX_COMMIT_AGE_DAYS:
        return False, f"last commit: {int(age)} days ago (> {MAX_COMMIT_AGE_DAYS})"
    return True, "ok"


def check_pypi(pkg: str) -> tuple[bool, str]:
    meta = _fetch_json(f"https://pypi.org/pypi/{pkg}/json")
    info = meta.get("info", {})
    lic = info.get("license") or ""
    # PyPI license strings are messy; accept if any allowed token appears.
    low = lic.lower()
    if not any(tok in low for tok in ALLOWED_LICENSES):
        # fall back to classifiers
        classifiers = " ".join(info.get("classifiers", [])).lower()
        if not any(tok in classifiers for tok in ALLOWED_LICENSES):
            return False, f"license: {lic[:40] or 'unknown'} (not in allowlist)"
    try:
        stats = _fetch_json(f"https://pypistats.org/api/packages/{pkg}/recent")
        weekly = stats.get("data", {}).get("last_week", 0)
    except Exception:
        weekly = MIN_WEEKLY_DL  # fail-open on stats
    if weekly < MIN_WEEKLY_DL:
        return False, f"weekly DL: {weekly:,} (< {MIN_WEEKLY_DL:,})"
    repo = ""
    urls = info.get("project_urls") or {}
    for k, v in urls.items():
        if "github.com" in (v or ""):
            repo = v
            break
    age = _commit_age_days(repo)
    if age is not None and age > MAX_COMMIT_AGE_DAYS:
        return False, f"last commit: {int(age)} days ago (> {MAX_COMMIT_AGE_DAYS})"
    return True, "ok"


def check_cargo(pkg: str) -> tuple[bool, str]:
    meta = _fetch_json(f"https://crates.io/api/v1/crates/{pkg}")
    crate = meta.get("crate", {})
    downloads = crate.get("recent_downloads", 0) or 0
    weekly = downloads // 12  # recent_downloads ~= 90 days
    if weekly < MIN_WEEKLY_DL:
        return False, f"weekly DL: {weekly:,} (< {MIN_WEEKLY_DL:,})"
    versions = meta.get("versions", [])
    lic = versions[0].get("license") if versions else None
    if not _license_ok((lic or "").split(" OR ")[0]):
        return False, f"license: {lic} (not in allowlist)"
    repo = crate.get("repository") or ""
    age = _commit_age_days(repo)
    if age is not None and age > MAX_COMMIT_AGE_DAYS:
        return False, f"last commit: {int(age)} days ago (> {MAX_COMMIT_AGE_DAYS})"
    return True, "ok"


def check_go(pkg: str) -> tuple[bool, str]:
    # Minimal: resolve via pkg.go.dev, check GitHub commit age.
    if not pkg.startswith("github.com/"):
        return True, "ok (non-github, skipped)"
    repo = "https://" + "/".join(pkg.split("/")[:3])
    age = _commit_age_days(repo)
    if age is not None and age > MAX_COMMIT_AGE_DAYS:
        return False, f"last commit: {int(age)} days ago (> {MAX_COMMIT_AGE_DAYS})"
    return True, "ok"


_CHECKER_NAMES = {
    "npm": "check_npm",
    "pypi": "check_pypi",
    "cargo": "check_cargo",
    "go": "check_go",
}


def _get_checker(eco: str):
    name = _CHECKER_NAMES.get(eco)
    return globals().get(name) if name else None


def load_allowlist() -> dict:
    try:
        return json.loads(ALLOWLIST_PATH.read_text())
    except Exception:
        return {}


def evaluate(eco: str, pkgs: list[str], allowlist: dict) -> list[tuple[str, str]]:
    """Return list of (pkg, reason) for blocked packages."""
    blocked = []
    allowed = set(allowlist.get(eco, []))
    checker = _get_checker(eco)
    if not checker:
        return []
    for pkg in pkgs:
        if pkg in allowed:
            continue
        try:
            ok, reason = checker(pkg)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, Exception):
            # fail-open on any registry issue
            continue
        if not ok:
            blocked.append((pkg, reason))
    return blocked


def main() -> int:
    if os.environ.get("APPROVE_DEPS") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    tool = payload.get("tool_name") or payload.get("tool")
    if tool != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command", "")
    if not cmd:
        return 0
    parsed = extract_packages(cmd)
    if not parsed:
        return 0
    eco, pkgs = parsed
    blocked = evaluate(eco, pkgs, load_allowlist())
    if not blocked:
        return 0
    lines = ["🚫 依存追加ブロック:"]
    for pkg, reason in blocked:
        lines.append(f"  {pkg}: {reason}")
    lines.append("")
    lines.append("承認して続行する場合:")
    lines.append(f"  APPROVE_DEPS=1 {cmd}")
    lines.append("")
    lines.append("恒久的に許可する場合:")
    lines.append(f"  {ALLOWLIST_PATH} に追加")
    sys.stderr.write("\n".join(lines) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
