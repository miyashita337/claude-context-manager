from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from src.monitor.threshold import Alert, AlertLevel

logger = logging.getLogger(__name__)

PUSHOVER_SCRIPT = Path.home() / ".claude" / "scripts" / "pushover-notify.sh"


def send_pushover(title: str, message: str) -> bool:
    """Send notification via Pushover using existing script."""
    if not PUSHOVER_SCRIPT.is_file():
        logger.warning("Pushover script not found: %s", PUSHOVER_SCRIPT)
        return False
    try:
        result = subprocess.run(
            ["bash", str(PUSHOVER_SCRIPT), title, message],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("Pushover notification failed: %s", e)
        return False


def notify_alerts(alerts: list[Alert]) -> None:
    """Send Pushover notifications for alerts."""
    for alert in alerts:
        emoji = "🚨" if alert.level == AlertLevel.ALERT else "⚠️"
        title = f"{emoji} Token Usage {alert.level.value.upper()}"
        send_pushover(title, alert.message)
