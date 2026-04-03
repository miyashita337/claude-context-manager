from __future__ import annotations

from src.config.usage_config import ThresholdConfig
from src.monitor.threshold import ThresholdChecker, Alert, AlertLevel


class TestThresholdChecker:
    def test_no_alert_below_threshold(self) -> None:
        config = ThresholdConfig(session_warn=30.0, daily_warn=50.0, daily_alert=150.0)
        checker = ThresholdChecker(config)
        alerts = checker.check(session_cost=10.0, daily_cost=30.0)
        assert len(alerts) == 0

    def test_session_warn(self) -> None:
        config = ThresholdConfig(session_warn=30.0, daily_warn=50.0, daily_alert=150.0)
        checker = ThresholdChecker(config)
        alerts = checker.check(session_cost=35.0, daily_cost=35.0)
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.WARN
        assert "session" in alerts[0].message.lower()

    def test_daily_warn(self) -> None:
        config = ThresholdConfig(session_warn=30.0, daily_warn=50.0, daily_alert=150.0)
        checker = ThresholdChecker(config)
        alerts = checker.check(session_cost=10.0, daily_cost=60.0)
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.WARN

    def test_daily_alert(self) -> None:
        config = ThresholdConfig(session_warn=30.0, daily_warn=50.0, daily_alert=150.0)
        checker = ThresholdChecker(config)
        alerts = checker.check(session_cost=10.0, daily_cost=200.0)
        assert any(a.level == AlertLevel.ALERT for a in alerts)

    def test_multiple_alerts(self) -> None:
        config = ThresholdConfig(session_warn=30.0, daily_warn=50.0, daily_alert=150.0)
        checker = ThresholdChecker(config)
        alerts = checker.check(session_cost=50.0, daily_cost=200.0)
        assert len(alerts) >= 2
