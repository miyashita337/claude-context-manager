from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.analyzer.ccusage_client import CcusageClient, CcusageResult

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestCcusageClient:
    def test_parse_output(self) -> None:
        with open(FIXTURES_DIR / "ccusage_output.json") as f:
            raw = json.load(f)
        client = CcusageClient()
        result = client._parse_output(raw)
        assert isinstance(result, CcusageResult)
        assert len(result.sessions) == 3
        assert result.total_cost == 0.44

    def test_get_project_costs(self) -> None:
        with open(FIXTURES_DIR / "ccusage_output.json") as f:
            raw = json.load(f)
        client = CcusageClient()
        result = client._parse_output(raw)
        costs = result.get_project_costs(username="testuser")
        # project-alpha: 0.15 + worktree 0.04 = 0.19
        assert abs(costs["project-alpha"] - 0.19) < 0.001
        assert abs(costs["project-beta"] - 0.25) < 0.001

    def test_fetch_success(self) -> None:
        fixture_path = FIXTURES_DIR / "ccusage_output.json"
        with open(fixture_path) as f:
            fixture_data = f.read()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = fixture_data
        with patch("subprocess.run", return_value=mock_result):
            client = CcusageClient()
            result = client.fetch()
        assert result is not None
        assert result.total_cost == 0.44

    def test_fetch_failure_returns_none(self) -> None:
        with patch(
            "subprocess.run", side_effect=FileNotFoundError("ccusage not found")
        ):
            client = CcusageClient()
            result = client.fetch()
        assert result is None

    def test_fetch_timeout_returns_none(self) -> None:
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("ccusage", 10)
        ):
            client = CcusageClient()
            result = client.fetch()
        assert result is None
