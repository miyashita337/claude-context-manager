"""
Tests for PITFALLS.md error pattern database.

Validates:
- File existence and structure
- Entry format consistency
- Search performance
- Required entries
"""

import os
import re
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def pitfalls_file():
    """Return path to PITFALLS.md"""
    project_root = Path(__file__).parent.parent
    return project_root / ".claude" / "PITFALLS.md"


@pytest.fixture
def pitfalls_content(pitfalls_file):
    """Return content of PITFALLS.md"""
    assert pitfalls_file.exists(), "PITFALLS.md must exist"
    return pitfalls_file.read_text()


class TestPitfallsStructure:
    """Test PITFALLS.md file structure and format"""

    def test_pitfalls_file_exists(self, pitfalls_file):
        """PITFALLS.md file must exist"""
        assert pitfalls_file.exists(), f"PITFALLS.md not found at {pitfalls_file}"

    def test_has_table_of_contents(self, pitfalls_content):
        """File must have a table of contents"""
        assert "## Table of Contents" in pitfalls_content
        assert "Git Errors" in pitfalls_content
        assert "Hook Errors" in pitfalls_content
        assert "Security Errors" in pitfalls_content

    def test_has_metadata_section(self, pitfalls_content):
        """File must have metadata section"""
        assert "## Metadata" in pitfalls_content
        assert "Total Entries" in pitfalls_content
        assert "Phase**:" in pitfalls_content or "Phase:" in pitfalls_content


class TestPitfallsEntries:
    """Test individual error pattern entries"""

    def test_required_entries_exist(self, pitfalls_content):
        """Required initial entries must exist"""
        # GIT-001: Initial commit HEAD error
        assert "GIT-001" in pitfalls_content
        assert "fatal: ambiguous argument 'HEAD'" in pitfalls_content

        # GIT-002: Non-official hook path
        assert "GIT-002" in pitfalls_content
        assert ".claude/settings.json" in pitfalls_content

        # HOOK-001: Hook execution not detected
        assert "HOOK-001" in pitfalls_content

        # SEC-001: Secret pattern detection
        assert "SEC-001" in pitfalls_content
        assert "OpenAI API key" in pitfalls_content

    def test_entry_format_consistency(self, pitfalls_content):
        """All entries must have required fields"""
        # Find all error IDs
        error_ids = re.findall(r"###\s+([A-Z]+-\d{3})", pitfalls_content)
        assert len(error_ids) >= 4, "Must have at least 4 initial entries"

        for error_id in error_ids:
            # Check for required fields after each ID
            pattern = rf"###\s+{error_id}.*?(?=###|\Z)"
            entry_content = re.search(pattern, pitfalls_content, re.DOTALL)
            assert entry_content, f"Entry {error_id} not found"

            entry_text = entry_content.group(0)

            # Required fields
            assert "Error Signature" in entry_text, f"{error_id} missing Error Signature"
            assert "Solution" in entry_text, f"{error_id} missing Solution"
            assert "Prevention" in entry_text, f"{error_id} missing Prevention"
            assert "Tags" in entry_text, f"{error_id} missing Tags"
            assert "Severity" in entry_text, f"{error_id} missing Severity"

    def test_error_id_format(self, pitfalls_content):
        """Error IDs must follow CATEGORY-NNN format"""
        error_ids = re.findall(r"###\s+([A-Z]+-\d{3})", pitfalls_content)

        for error_id in error_ids:
            # Check format: LETTERS-DIGITS
            assert re.match(r"^[A-Z]+-\d{3}$", error_id), \
                f"Invalid error ID format: {error_id}"

            # Check category is valid
            category = error_id.split("-")[0]
            valid_categories = ["GIT", "HOOK", "SEC", "API", "BUILD", "CCUSAGE"]
            assert category in valid_categories, \
                f"Invalid category in {error_id}: {category}"


class TestPitfallsSearch:
    """Test grep searchability and performance"""

    def test_grep_search_works(self, pitfalls_file):
        """Grep search must find entries"""
        # Search for known error signature (with -B2 to include error ID)
        result = subprocess.run(
            ["grep", "-B2", "fatal: ambiguous argument", str(pitfalls_file)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Grep search failed"
        assert "GIT-001" in result.stdout, "Grep didn't find expected entry"

    def test_grep_search_performance(self, pitfalls_file):
        """Grep search must complete in < 0.5 seconds"""
        start = time.time()
        subprocess.run(
            ["grep", "error", str(pitfalls_file)],
            capture_output=True,
            text=True
        )
        elapsed = time.time() - start

        assert elapsed < 0.5, f"Grep search too slow: {elapsed:.3f}s > 0.5s"

    def test_search_by_tag(self, pitfalls_file, pitfalls_content):
        """Must be able to search by tag"""
        # Search for security tag - verify it's in the SEC-001 section
        # Use Python to parse since grep context can vary by entry length
        sections = re.split(r'###\s+([A-Z]+-\d{3})', pitfalls_content)

        # Find SEC-001 section
        found_sec001 = False
        for i in range(1, len(sections), 2):
            error_id = sections[i]
            content = sections[i+1] if i+1 < len(sections) else ""

            if error_id == "SEC-001":
                assert "security" in content, "SEC-001 should have 'security' tag"
                found_sec001 = True
                break

        assert found_sec001, "SEC-001 entry not found"

    def test_search_by_error_signature(self, pitfalls_file):
        """Must be able to search by error message"""
        # Search for specific error message
        result = subprocess.run(
            ["grep", "-B2", "OpenAI API key detected", str(pitfalls_file)],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "SEC-001" in result.stdout


class TestPitfallsMaintenance:
    """Test maintenance and scalability features"""

    def test_metadata_tracking(self, pitfalls_content):
        """Metadata must track entry count"""
        # Count actual entries
        error_ids = re.findall(r"###\s+([A-Z]+-\d{3})", pitfalls_content)
        actual_count = len(error_ids)

        # Check metadata reflects this
        metadata_match = re.search(r"\*\*Total Entries\*\*:\s*(\d+)", pitfalls_content)
        assert metadata_match, "Missing 'Total Entries' in metadata"

        metadata_count = int(metadata_match.group(1))
        assert metadata_count == actual_count, \
            f"Metadata count ({metadata_count}) doesn't match actual ({actual_count})"

    def test_phase_tracking(self, pitfalls_content):
        """Metadata must track scalability phase"""
        # Check phase is defined
        assert re.search(r"\*\*Phase\*\*:\s*\d", pitfalls_content), \
            "Missing Phase in metadata"

        # For initial implementation, should be Phase 1
        assert "Phase**: 1" in pitfalls_content or "Phase: 1" in pitfalls_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
