#!/usr/bin/env python3
"""Lightweight entry point for hook-based monitoring and scheduled reports."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from io import StringIO

from src.analyzer.aggregator import Aggregator, ProjectSummary
from src.analyzer.ccusage_client import CcusageClient
from src.analyzer.merger import Merger
from src.analyzer.project_mapper import ProjectMapper
from src.cache.scan_cache import ScanCache
from src.config.usage_config import UsageConfig
from src.monitor.notifier import notify_alerts, send_pushover
from src.monitor.threshold import ThresholdChecker
from src.output.cli_report import CliReporter

from pathlib import Path

CACHE_DIR = Path.home() / ".claude" / "tools" / "token-analyzer" / ".cache"


def check_session() -> int:
    """Quick check: fetch current costs and notify if thresholds exceeded."""
    config = UsageConfig.load()
    if not config.pushover_enabled:
        return 0
    client = CcusageClient(timeout=5)
    result = client.fetch()
    if result is None:
        return 0
    daily_cost = result.total_cost
    session_costs = [s.total_cost for s in result.sessions]
    max_session_cost = max(session_costs) if session_costs else 0.0
    checker = ThresholdChecker(config.thresholds)
    alerts = checker.check(session_cost=max_session_cost, daily_cost=daily_cost)
    if alerts:
        notify_alerts(alerts)
    return 0


def _generate_report(
    since: str | None = None, top: int = 10
) -> tuple[str, dict[str, float] | None]:
    """Generate token usage report text and cost map."""
    mapper = ProjectMapper()
    cache = ScanCache(CACHE_DIR / "scan_cache.json")
    aggregator = Aggregator(mapper=mapper, scan_cache=cache)
    summaries = aggregator.aggregate()

    costs: dict[str, float] | None = None
    client = CcusageClient(timeout=15)
    ccusage_result = client.fetch(since=since)
    if ccusage_result:
        costs = ccusage_result.get_project_costs(username=mapper.username)

    merger = Merger()
    merged = merger.merge(summaries, costs)
    ranked = sorted(merged.items(), key=lambda x: x[1].total_tokens, reverse=True)[:top]

    report_data: list[tuple[str, ProjectSummary]] = []
    cost_map: dict[str, float] = {}
    for name, ms in ranked:
        ps = ProjectSummary(
            input_tokens=ms.input_tokens,
            output_tokens=ms.output_tokens,
            cache_creation_tokens=ms.cache_creation_tokens,
            cache_read_tokens=ms.cache_read_tokens,
            session_count=ms.session_count,
            models_used=ms.models_used,
        )
        report_data.append((name, ps))
        if ms.cost_usd is not None:
            cost_map[name] = ms.cost_usd

    output = StringIO()
    reporter = CliReporter(output=output)
    reporter.render(report_data, costs=cost_map if cost_map else None)

    cache.save()
    return output.getvalue(), cost_map


def report_daily() -> int:
    """Generate and send daily token usage report via Pushover."""
    today = datetime.now().strftime("%Y-%m-%d")
    since = datetime.now().strftime("%Y%m%d")

    report_text, cost_map = _generate_report(since=since, top=10)

    total_cost = sum(cost_map.values()) if cost_map else 0
    cost_str = f"~${total_cost:.2f}" if cost_map else "N/A"

    title = f"📊 Daily Token Report ({today})"
    message = f"Total: {cost_str}\n\n{report_text[:900]}"

    success = send_pushover(title, message)
    if success:
        print(f"Daily report sent: {today}")
    else:
        print(f"Failed to send daily report: {today}")
        print(report_text)
    return 0 if success else 1


def report_weekly() -> int:
    """Generate and send weekly token usage report via Pushover."""
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    since = week_ago.strftime("%Y%m%d")
    period = f"{week_ago.strftime('%m/%d')}–{today.strftime('%m/%d')}"

    report_text, cost_map = _generate_report(since=since, top=10)

    total_cost = sum(cost_map.values()) if cost_map else 0
    cost_str = f"~${total_cost:.2f}" if cost_map else "N/A"

    title = f"📊 Weekly Token Report ({period})"
    message = f"Total: {cost_str}\n\n{report_text[:900]}"

    success = send_pushover(title, message)
    if success:
        print(f"Weekly report sent: {period}")
    else:
        print(f"Failed to send weekly report: {period}")
        print(report_text)
    return 0 if success else 1


def report_test() -> int:
    """Send a test notification to verify Pushover is working."""
    title = "🔔 Token Analyzer Test"
    message = "テスト通知です。Token Analyzerの定期レポート機能が正常に動作しています。"
    success = send_pushover(title, message)
    if success:
        print("Test notification sent successfully!")
    else:
        print("Test notification FAILED. Check Pushover configuration.")
    return 0 if success else 1


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: entry.py <check-session|report-daily|report-weekly|report-test>")
        return 1
    command = sys.argv[1]
    commands = {
        "check-session": check_session,
        "report-daily": report_daily,
        "report-weekly": report_weekly,
        "report-test": report_test,
    }
    handler = commands.get(command)
    if handler:
        return handler()
    print(f"Unknown command: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
