#!/usr/bin/env python3
"""Generate and manage launchd plists for scheduled reports."""
from __future__ import annotations

from pathlib import Path

from src.config.usage_config import UsageConfig

PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PREFIX = "com.claude.token-analyzer"
TOOL_DIR = Path.home() / ".claude" / "tools" / "token-analyzer"


def generate_daily_plist(config: UsageConfig) -> str:
    """Generate launchd plist for daily report."""
    hour, minute = config.schedule.daily_time.split(":")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_PREFIX}.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{TOOL_DIR}/monitor/entry.py</string>
        <string>report-daily</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{int(hour)}</integer>
        <key>Minute</key>
        <integer>{int(minute)}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.claude/logs/token-analyzer-daily.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.claude/logs/token-analyzer-daily.err</string>
</dict>
</plist>"""


def generate_weekly_plist(config: UsageConfig) -> str:
    """Generate launchd plist for weekly report (Sunday)."""
    hour, minute = config.schedule.weekly_time.split(":")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_PREFIX}.weekly</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{TOOL_DIR}/monitor/entry.py</string>
        <string>report-weekly</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>{int(hour)}</integer>
        <key>Minute</key>
        <integer>{int(minute)}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.claude/logs/token-analyzer-weekly.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.claude/logs/token-analyzer-weekly.err</string>
</dict>
</plist>"""


def install_schedules(config: UsageConfig | None = None) -> None:
    """Write plist files and load them with launchctl."""
    import subprocess

    config = config or UsageConfig.load()
    PLIST_DIR.mkdir(parents=True, exist_ok=True)
    log_dir = Path.home() / ".claude" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    if config.schedule.daily_enabled:
        daily_path = PLIST_DIR / f"{PLIST_PREFIX}.daily.plist"
        daily_path.write_text(generate_daily_plist(config))
        subprocess.run(["launchctl", "unload", str(daily_path)], capture_output=True)
        subprocess.run(["launchctl", "load", str(daily_path)], capture_output=True)
        print(f"Daily report scheduled: {config.schedule.daily_time} JST")
    if config.schedule.weekly_enabled:
        weekly_path = PLIST_DIR / f"{PLIST_PREFIX}.weekly.plist"
        weekly_path.write_text(generate_weekly_plist(config))
        subprocess.run(["launchctl", "unload", str(weekly_path)], capture_output=True)
        subprocess.run(["launchctl", "load", str(weekly_path)], capture_output=True)
        print(
            f"Weekly report scheduled: {config.schedule.weekly_day} {config.schedule.weekly_time} JST"
        )
