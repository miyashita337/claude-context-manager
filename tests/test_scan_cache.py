from __future__ import annotations

import time
from pathlib import Path

from src.cache.scan_cache import ScanCache


class TestScanCache:
    def test_first_scan_returns_all_files(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "a.jsonl").write_text('{"type":"test"}\n')
        (data_dir / "b.jsonl").write_text('{"type":"test"}\n')
        cache = ScanCache(cache_file)
        changed = cache.get_changed_files(data_dir, "*.jsonl")
        assert len(changed) == 2

    def test_second_scan_returns_empty_if_unchanged(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "a.jsonl").write_text('{"type":"test"}\n')
        cache = ScanCache(cache_file)
        cache.get_changed_files(data_dir, "*.jsonl")
        cache.save()
        cache2 = ScanCache(cache_file)
        changed = cache2.get_changed_files(data_dir, "*.jsonl")
        assert len(changed) == 0

    def test_modified_file_detected(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        f = data_dir / "a.jsonl"
        f.write_text('{"type":"test"}\n')
        cache = ScanCache(cache_file)
        cache.get_changed_files(data_dir, "*.jsonl")
        cache.save()
        time.sleep(0.1)
        f.write_text('{"type":"test"}\n{"type":"new"}\n')
        cache2 = ScanCache(cache_file)
        changed = cache2.get_changed_files(data_dir, "*.jsonl")
        assert len(changed) == 1
        assert changed[0].name == "a.jsonl"

    def test_new_file_detected(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.json"
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "a.jsonl").write_text('{"type":"test"}\n')
        cache = ScanCache(cache_file)
        cache.get_changed_files(data_dir, "*.jsonl")
        cache.save()
        (data_dir / "b.jsonl").write_text('{"type":"new"}\n')
        cache2 = ScanCache(cache_file)
        changed = cache2.get_changed_files(data_dir, "*.jsonl")
        assert len(changed) == 1
        assert changed[0].name == "b.jsonl"
