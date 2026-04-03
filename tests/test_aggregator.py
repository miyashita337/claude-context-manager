from __future__ import annotations

import shutil
from pathlib import Path

from src.analyzer.aggregator import Aggregator, ProjectSummary
from src.analyzer.project_mapper import ProjectMapper
from src.cache.scan_cache import ScanCache

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestAggregator:
    def test_aggregate_single_project(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / "projects"
        proj_dir = projects_dir / "-Users-testuser-alpha"
        proj_dir.mkdir(parents=True)
        shutil.copy(FIXTURES_DIR / "sample_session.jsonl", proj_dir / "session1.jsonl")

        mapper = ProjectMapper(username="testuser", projects_dir=projects_dir)
        cache = ScanCache(tmp_path / "cache.json")
        agg = Aggregator(mapper=mapper, scan_cache=cache)
        results = agg.aggregate()

        assert "alpha" in results
        summary = results["alpha"]
        assert isinstance(summary, ProjectSummary)
        assert summary.input_tokens == 300
        assert summary.output_tokens == 580
        assert summary.session_count == 1

    def test_aggregate_worktree_merged(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / "projects"
        main_dir = projects_dir / "-Users-testuser-alpha"
        wt_dir = projects_dir / "-Users-testuser-alpha--claude-worktrees-feat"
        main_dir.mkdir(parents=True)
        wt_dir.mkdir(parents=True)
        shutil.copy(FIXTURES_DIR / "sample_session.jsonl", main_dir / "s1.jsonl")
        shutil.copy(FIXTURES_DIR / "sample_session.jsonl", wt_dir / "s2.jsonl")

        mapper = ProjectMapper(username="testuser", projects_dir=projects_dir)
        cache = ScanCache(tmp_path / "cache.json")
        agg = Aggregator(mapper=mapper, scan_cache=cache)
        results = agg.aggregate()

        assert "alpha" in results
        assert results["alpha"].input_tokens == 600
        assert results["alpha"].session_count == 2

    def test_aggregate_empty_dir(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        mapper = ProjectMapper(username="testuser", projects_dir=projects_dir)
        cache = ScanCache(tmp_path / "cache.json")
        agg = Aggregator(mapper=mapper, scan_cache=cache)
        results = agg.aggregate()
        assert results == {}

    def test_sorted_by_total_tokens(self, tmp_path: Path) -> None:
        projects_dir = tmp_path / "projects"
        alpha_dir = projects_dir / "-Users-testuser-alpha"
        beta_dir = projects_dir / "-Users-testuser-beta"
        alpha_dir.mkdir(parents=True)
        beta_dir.mkdir(parents=True)
        shutil.copy(FIXTURES_DIR / "sample_session.jsonl", alpha_dir / "s1.jsonl")
        shutil.copy(FIXTURES_DIR / "sample_session.jsonl", beta_dir / "s1.jsonl")
        shutil.copy(FIXTURES_DIR / "sample_session.jsonl", beta_dir / "s2.jsonl")

        mapper = ProjectMapper(username="testuser", projects_dir=projects_dir)
        cache = ScanCache(tmp_path / "cache.json")
        agg = Aggregator(mapper=mapper, scan_cache=cache)
        ranked = agg.aggregate_sorted()
        assert ranked[0][0] == "beta"
        assert ranked[1][0] == "alpha"
