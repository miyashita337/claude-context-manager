#!/usr/bin/env python3
"""Token Analyzer CLI — project-level token usage analysis for Claude Code."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.analyzer.aggregator import Aggregator
from src.analyzer.project_mapper import ProjectMapper
from src.cache.scan_cache import ScanCache
from src.output.cli_report import CliReporter


CACHE_DIR = Path.home() / ".claude" / "tools" / "token-analyzer" / ".cache"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Token usage analysis by project")
    parser.add_argument("--top", type=int, default=15, help="Show top N projects")
    parser.add_argument("--no-cache", action="store_true", help="Ignore scan cache")
    args = parser.parse_args(argv)

    mapper = ProjectMapper()
    cache_file = CACHE_DIR / "scan_cache.json"
    cache = ScanCache(cache_file) if not args.no_cache else ScanCache(Path("/dev/null"))

    aggregator = Aggregator(mapper=mapper, scan_cache=cache)
    ranked = aggregator.aggregate_sorted()

    if args.top:
        ranked = ranked[: args.top]

    reporter = CliReporter()
    reporter.render(ranked)

    if not args.no_cache:
        cache.save()

    return 0


if __name__ == "__main__":
    sys.exit(main())
