"""
End-to-end tests for error resolution workflow.

Validates:
- Error detection → PITFALLS.md search → Solution application
- Skills integration with PITFALLS.md
- Real error scenarios from past incidents
"""

import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


@pytest.fixture
def project_root():
    """Return project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture
def pitfalls_file(project_root):
    """Return path to PITFALLS.md"""
    return project_root / ".claude" / "PITFALLS.md"


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )

        # Configure git
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )

        yield repo_path


class TestErrorDetectionAndResolution:
    """Test complete error detection and resolution workflows"""

    def test_initial_commit_head_error_detection(self, temp_git_repo):
        """Reproduce GIT-001: Initial commit HEAD error"""
        # Create a file and add it
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("test content")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True
        )

        # Try to unstage with git reset HEAD (should fail)
        result = subprocess.run(
            ["git", "reset", "HEAD", "test.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True
        )

        # Should fail with HEAD error
        assert result.returncode != 0, "Expected git reset HEAD to fail before first commit"
        assert "HEAD" in result.stderr or "fatal" in result.stderr, \
            "Expected HEAD-related error message"

    def test_initial_commit_head_error_solution(self, temp_git_repo, pitfalls_file):
        """Verify GIT-001 solution from PITFALLS.md works"""
        # Create and stage a file
        test_file = temp_git_repo / "test.txt"
        test_file.write_text("test content")

        subprocess.run(
            ["git", "add", "test.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            check=True
        )

        # Search PITFALLS.md for solution
        result = subprocess.run(
            ["grep", "-A20", "fatal: ambiguous argument.*HEAD", str(pitfalls_file)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Should find GIT-001 in PITFALLS.md"
        assert "git rm --cached" in result.stdout, \
            "PITFALLS.md should suggest 'git rm --cached' as solution"

        # Apply solution from PITFALLS.md
        result = subprocess.run(
            ["git", "rm", "--cached", "test.txt"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True
        )

        # Solution should work
        assert result.returncode == 0, f"git rm --cached failed: {result.stderr}"

        # Verify file is unstaged
        status = subprocess.run(
            ["git", "status", "--short"],
            cwd=temp_git_repo,
            capture_output=True,
            text=True,
            check=True
        )

        assert "?? test.txt" in status.stdout, "File should be untracked after unstaging"

    def test_secret_detection_pattern(self, pitfalls_file):
        """Test SEC-001: Secret pattern detection"""
        # Search for secret patterns in PITFALLS.md
        result = subprocess.run(
            ["grep", "-B5", "-A15", "OpenAI API key detected", str(pitfalls_file)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Should find SEC-001 in PITFALLS.md"

        # Verify solution steps are present
        solution_text = result.stdout
        assert "git rm --cached" in solution_text, \
            "SEC-001 solution should include 'git rm --cached'"
        assert ".gitignore" in solution_text, \
            "SEC-001 solution should mention .gitignore"
        assert ".env" in solution_text, \
            "SEC-001 solution should mention .env"


class TestPitfallsSearchPerformance:
    """Test PITFALLS.md search performance"""

    def test_grep_search_performance(self, pitfalls_file):
        """Grep search should complete in < 0.5 seconds"""
        search_patterns = [
            "fatal: ambiguous argument",
            "OpenAI API key",
            "Hook not executing",
            "GIT-001"
        ]

        for pattern in search_patterns:
            start = time.time()
            result = subprocess.run(
                ["grep", pattern, str(pitfalls_file)],
                capture_output=True,
                text=True
            )
            elapsed = time.time() - start

            # Search should be fast
            assert elapsed < 0.5, \
                f"Grep search for '{pattern}' too slow: {elapsed:.3f}s > 0.5s"

            # Should find results (for these known patterns)
            if pattern in ["fatal: ambiguous argument", "OpenAI API key", "GIT-001"]:
                assert result.returncode == 0, \
                    f"Should find '{pattern}' in PITFALLS.md"


class TestSkillsPitfallsIntegration:
    """Test integration between Skills and PITFALLS.md"""

    def test_pre_commit_skill_references_pitfalls(self, project_root):
        """pre-commit skill should reference PITFALLS.md"""
        skill_file = project_root / ".claude" / "skills" / "pre-commit" / "SKILL.md"
        content = skill_file.read_text()

        # Should reference PITFALLS.md
        assert "PITFALLS.md" in content, \
            "pre-commit skill should reference PITFALLS.md"

        # Should mention error resolution
        assert "error" in content.lower(), \
            "pre-commit skill should discuss error resolution"

        # Should reference specific error IDs
        assert "SEC-001" in content or "GIT-001" in content, \
            "pre-commit skill should reference specific error IDs"

    def test_git_workflow_skill_references_git_errors(self, project_root):
        """git-workflow skill should reference git-errors.md"""
        skill_file = project_root / ".claude" / "skills" / "git-workflow" / "SKILL.md"
        content = skill_file.read_text()

        # Should reference PITFALLS.md or git-errors.md
        assert "PITFALLS.md" in content or "git-errors.md" in content, \
            "git-workflow skill should reference error documentation"

        # Should mention initial commit handling
        assert "initial commit" in content.lower(), \
            "git-workflow skill should discuss initial commit handling"

    def test_error_patterns_symlink_works(self, project_root, pitfalls_file):
        """pre-commit skill's error-patterns.md symlink should work"""
        symlink = project_root / ".claude" / "skills" / "pre-commit" / "references" / "error-patterns.md"

        # Symlink should exist and point to PITFALLS.md
        assert symlink.exists(), "error-patterns.md symlink should exist"
        assert symlink.is_symlink(), "error-patterns.md should be a symlink"

        # Should be readable and contain same content
        symlink_content = symlink.read_text()
        pitfalls_content = pitfalls_file.read_text()

        assert symlink_content == pitfalls_content, \
            "Symlink should point to PITFALLS.md with identical content"


class TestMakePreGitCheckIntegration:
    """Test make pre-git-check integration"""

    def test_make_pre_git_check_exists(self, project_root):
        """make pre-git-check target should exist"""
        # Check if Makefile exists
        makefile = project_root / "Makefile"
        assert makefile.exists(), "Makefile should exist"

        # Check if pre-git-check target exists
        content = makefile.read_text()
        assert "pre-git-check" in content, \
            "Makefile should have pre-git-check target"

    def test_make_pre_git_check_runs(self, project_root):
        """make pre-git-check should execute without errors"""
        result = subprocess.run(
            ["make", "pre-git-check"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Should complete (may succeed or fail depending on repo state)
        # Just verify it runs without crashing
        assert result.returncode in [0, 1], \
            f"make pre-git-check should exit with 0 or 1, got {result.returncode}"

        # Should produce output
        assert result.stdout or result.stderr, \
            "make pre-git-check should produce output"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
