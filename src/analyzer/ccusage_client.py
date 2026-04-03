from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field

from src.analyzer.project_mapper import ProjectMapper

logger = logging.getLogger(__name__)


@dataclass
class CcusageSession:
    """A single session from ccusage output."""

    session_id: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    last_activity: str
    models_used: list[str]


@dataclass
class CcusageResult:
    """Parsed ccusage session --json output."""

    sessions: list[CcusageSession] = field(default_factory=list)
    total_cost: float = 0.0

    def get_project_costs(self, username: str | None = None) -> dict[str, float]:
        """Aggregate costs by parent project, merging worktrees."""
        mapper = ProjectMapper(username=username)
        costs: dict[str, float] = {}
        for session in self.sessions:
            project = mapper.extract_project_name(session.session_id)
            costs[project] = costs.get(project, 0.0) + session.total_cost
        return costs


class CcusageClient:
    """Wrapper around ccusage CLI for cost data."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def fetch(self, since: str | None = None) -> CcusageResult | None:
        """Run ccusage session --json and parse the output."""
        cmd = ["ccusage", "session", "--json"]
        if since:
            cmd.extend(["--since", since])
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout
            )
            if result.returncode != 0:
                logger.warning(
                    "ccusage exited with code %d: %s", result.returncode, result.stderr
                )
                return None
            raw = json.loads(result.stdout)
            return self._parse_output(raw)
        except FileNotFoundError:
            logger.warning("ccusage not found. Install with: npm install -g ccusage")
            return None
        except subprocess.TimeoutExpired:
            logger.warning("ccusage timed out after %ds", self.timeout)
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse ccusage output: %s", e)
            return None

    def _parse_output(self, raw: dict) -> CcusageResult:
        """Parse raw ccusage JSON into CcusageResult."""
        sessions = []
        for s in raw.get("sessions", []):
            sessions.append(
                CcusageSession(
                    session_id=s["sessionId"],
                    input_tokens=s.get("inputTokens", 0),
                    output_tokens=s.get("outputTokens", 0),
                    cache_creation_tokens=s.get("cacheCreationTokens", 0),
                    cache_read_tokens=s.get("cacheReadTokens", 0),
                    total_tokens=s.get("totalTokens", 0),
                    total_cost=s.get("totalCost", 0.0),
                    last_activity=s.get("lastActivity", ""),
                    models_used=s.get("modelsUsed", []),
                )
            )
        totals = raw.get("totals", {})
        return CcusageResult(sessions=sessions, total_cost=totals.get("totalCost", 0.0))
