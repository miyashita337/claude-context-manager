#!/usr/bin/env python3
"""Lightweight entry point for hook-based monitoring."""
from __future__ import annotations

import sys

from src.analyzer.ccusage_client import CcusageClient
from src.config.usage_config import UsageConfig
from src.monitor.notifier import notify_alerts
from src.monitor.threshold import ThresholdChecker


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


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: entry.py <check-session|report-daily|report-weekly>")
        return 1
    command = sys.argv[1]
    if command == "check-session":
        return check_session()
    print(f"Unknown command: {command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
