from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.analyzer.jsonl_parser import JsonlParser, SessionStats
from src.analyzer.project_mapper import ProjectMapper
from src.cache.scan_cache import ScanCache


@dataclass
class ProjectSummary:
    """Aggregated token usage for a single project."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    session_count: int = 0
    models_used: set[str] = field(default_factory=set)

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )

    def merge(self, stats: SessionStats) -> None:
        """Merge a session's stats into this summary."""
        self.input_tokens += stats.input_tokens
        self.output_tokens += stats.output_tokens
        self.cache_creation_tokens += stats.cache_creation_tokens
        self.cache_read_tokens += stats.cache_read_tokens
        self.session_count += 1
        self.models_used.update(stats.models_used)


class Aggregator:
    """Aggregate token usage across all projects from JSONL files."""

    def __init__(
        self,
        mapper: ProjectMapper,
        scan_cache: ScanCache,
        parser: JsonlParser | None = None,
    ) -> None:
        self.mapper = mapper
        self.scan_cache = scan_cache
        self.parser = parser or JsonlParser()

    def aggregate(self) -> dict[str, ProjectSummary]:
        """Scan all project directories and aggregate by project."""
        summaries: dict[str, ProjectSummary] = {}
        for project_dir in self.mapper.list_project_dirs():
            project_name = self.mapper.extract_project_name(project_dir.name)
            jsonl_files = sorted(project_dir.glob("*.jsonl"))
            for jsonl_file in jsonl_files:
                stats = self.parser.parse_file(jsonl_file)
                if stats.total_tokens == 0:
                    continue
                if project_name not in summaries:
                    summaries[project_name] = ProjectSummary()
                summaries[project_name].merge(stats)
        return summaries

    def aggregate_sorted(self) -> list[tuple[str, ProjectSummary]]:
        """Return aggregated results sorted by total tokens descending."""
        results = self.aggregate()
        return sorted(results.items(), key=lambda x: x[1].total_tokens, reverse=True)
