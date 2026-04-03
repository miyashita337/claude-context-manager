#!/usr/bin/env python3
"""Token Analyzer CLI — project-level token usage analysis for Claude Code."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.analyzer.aggregator import Aggregator, ProjectSummary
from src.analyzer.ccusage_client import CcusageClient
from src.analyzer.merger import Merger
from src.analyzer.project_mapper import ProjectMapper
from src.cache.scan_cache import ScanCache
from src.output.cli_report import CliReporter


CACHE_DIR = Path.home() / ".claude" / "tools" / "token-analyzer" / ".cache"

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Token usage analysis by project")
    parser.add_argument("--top", type=int, default=15, help="Show top N projects")
    parser.add_argument("--since", type=str, help="Filter from date (YYYYMMDD)")
    parser.add_argument("--no-cache", action="store_true", help="Ignore scan cache")
    parser.add_argument(
        "--no-cost", action="store_true", help="Skip ccusage cost lookup"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    mapper = ProjectMapper()
    cache_file = CACHE_DIR / "scan_cache.json"
    cache = ScanCache(cache_file) if not args.no_cache else ScanCache(Path("/dev/null"))

    # Phase 1: JSONL aggregation
    aggregator = Aggregator(mapper=mapper, scan_cache=cache)
    summaries = aggregator.aggregate()

    # Phase 2: ccusage cost lookup
    costs: dict[str, float] | None = None
    if not args.no_cost:
        client = CcusageClient()
        ccusage_result = client.fetch(since=args.since)
        if ccusage_result:
            costs = ccusage_result.get_project_costs(username=mapper.username)
            logger.info("ccusage costs loaded for %d projects", len(costs))
        else:
            logger.warning("ccusage unavailable, showing tokens only")

    # Merge
    merger = Merger()
    merged = merger.merge(summaries, costs)

    # Sort and limit
    ranked = sorted(merged.items(), key=lambda x: x[1].total_tokens, reverse=True)
    if args.top:
        ranked = ranked[: args.top]

    # Convert for reporter
    report_data = []
    cost_map = {}
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

    reporter = CliReporter()
    reporter.render(report_data, costs=cost_map if cost_map else None)

    if not args.no_cache:
        cache.save()

    return 0


if __name__ == "__main__":
    sys.exit(main())
