from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ThresholdConfig:
    session_warn: float = 30.0
    daily_warn: float = 50.0
    daily_alert: float = 150.0


@dataclass
class ScheduleConfig:
    daily_enabled: bool = True
    daily_time: str = "19:00"
    weekly_enabled: bool = True
    weekly_time: str = "19:00"
    weekly_day: str = "sunday"


@dataclass
class UsageConfig:
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    pushover_enabled: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> UsageConfig:
        """Load config from YAML file, falling back to defaults."""
        if path is None:
            path = Path.home() / ".claude" / "tools" / "token-analyzer" / "config.yaml"
        if not path.is_file():
            return cls()
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        thresholds = raw.get("thresholds", {})
        schedule = raw.get("schedule", {})
        return cls(
            thresholds=ThresholdConfig(
                session_warn=thresholds.get("session", {}).get("warn", 30.0),
                daily_warn=thresholds.get("daily", {}).get("warn", 50.0),
                daily_alert=thresholds.get("daily", {}).get("alert", 150.0),
            ),
            schedule=ScheduleConfig(
                daily_enabled=schedule.get("daily", {}).get("enabled", True),
                daily_time=schedule.get("daily", {}).get("time", "19:00"),
                weekly_enabled=schedule.get("weekly", {}).get("enabled", True),
                weekly_time=schedule.get("weekly", {}).get("time", "19:00"),
                weekly_day=schedule.get("weekly", {}).get("day", "sunday"),
            ),
            pushover_enabled=raw.get("notification", {}).get("pushover", True),
        )
