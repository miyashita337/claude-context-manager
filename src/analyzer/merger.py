from __future__ import annotations

from dataclasses import dataclass, field

from src.analyzer.aggregator import ProjectSummary


@dataclass
class MergedProjectSummary:
    """Project summary with optional cost data from ccusage."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    session_count: int = 0
    models_used: set[str] = field(default_factory=set)
    cost_usd: float | None = None

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )


class Merger:
    """Merge JSONL-parsed summaries with ccusage cost data."""

    def merge(
        self,
        summaries: dict[str, ProjectSummary],
        costs: dict[str, float] | None = None,
    ) -> dict[str, MergedProjectSummary]:
        """Merge token summaries with cost data by project name."""
        costs = costs or {}
        result: dict[str, MergedProjectSummary] = {}
        for name, summary in summaries.items():
            result[name] = MergedProjectSummary(
                input_tokens=summary.input_tokens,
                output_tokens=summary.output_tokens,
                cache_creation_tokens=summary.cache_creation_tokens,
                cache_read_tokens=summary.cache_read_tokens,
                session_count=summary.session_count,
                models_used=summary.models_used.copy(),
                cost_usd=costs.get(name),
            )
        return result
