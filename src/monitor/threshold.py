from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.config.usage_config import ThresholdConfig


class AlertLevel(Enum):
    WARN = "warn"
    ALERT = "alert"


@dataclass
class Alert:
    level: AlertLevel
    message: str
    cost: float


class ThresholdChecker:
    """Check token costs against configured thresholds."""

    def __init__(self, config: ThresholdConfig) -> None:
        self.config = config

    def check(self, session_cost: float, daily_cost: float) -> list[Alert]:
        """Check costs and return any triggered alerts."""
        alerts: list[Alert] = []
        if session_cost >= self.config.session_warn:
            alerts.append(
                Alert(
                    level=AlertLevel.WARN,
                    message=f"Session cost ${session_cost:.2f} exceeds warning threshold ${self.config.session_warn:.2f}",
                    cost=session_cost,
                )
            )
        if daily_cost >= self.config.daily_alert:
            alerts.append(
                Alert(
                    level=AlertLevel.ALERT,
                    message=f"Daily cost ${daily_cost:.2f} exceeds alert threshold ${self.config.daily_alert:.2f}",
                    cost=daily_cost,
                )
            )
        elif daily_cost >= self.config.daily_warn:
            alerts.append(
                Alert(
                    level=AlertLevel.WARN,
                    message=f"Daily cost ${daily_cost:.2f} exceeds warning threshold ${self.config.daily_warn:.2f}",
                    cost=daily_cost,
                )
            )
        return alerts
