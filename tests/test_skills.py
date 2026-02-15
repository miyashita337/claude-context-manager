"""
Tests for Claude Code Skills.

Validates:
- Skill file existence and structure
- YAML frontmatter format
- File size limits
- Tool restrictions
- Reference directory structure
"""

import os
import re
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def skills_dir():
    """Return path to skills directory"""
    project_root = Path(__file__).parent.parent
    return project_root / ".claude" / "skills"


@pytest.fixture
def skill_names():
    """Return list of expected skill names"""
    return ["fact-check", "pre-commit", "git-workflow"]


@pytest.fixture
def pitfalls_file():
    """Return path to PITFALLS.md"""
    project_root = Path(__file__).parent.parent
    return project_root / ".claude" / "PITFALLS.md"


class TestSkillStructure:
    """Test basic skill directory and file structure"""

    def test_skills_directory_exists(self, skills_dir):
        """Skills directory must exist"""
        assert skills_dir.exists(), f"Skills directory not found at {skills_dir}"
        assert skills_dir.is_dir(), f"{skills_dir} is not a directory"

    def test_all_skill_files_exist(self, skills_dir, skill_names):
        """All expected skill SKILL.md files must exist"""
        for skill_name in skill_names:
            skill_file = skills_dir / skill_name / "SKILL.md"
            assert skill_file.exists(), f"Skill file not found: {skill_file}"

    def test_all_references_directories_exist(self, skills_dir, skill_names):
        """All skills should have a references directory"""
        for skill_name in skill_names:
            ref_dir = skills_dir / skill_name / "references"
            assert ref_dir.exists(), f"References directory not found: {ref_dir}"
            assert ref_dir.is_dir(), f"{ref_dir} is not a directory"


class TestSkillYAMLFrontmatter:
    """Test YAML frontmatter in skill files"""

    def test_yaml_frontmatter_exists(self, skills_dir, skill_names):
        """All skills must have YAML frontmatter"""
        for skill_name in skill_names:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()

            # Check for YAML frontmatter delimiters
            assert content.startswith("---\n"), \
                f"{skill_name}: SKILL.md must start with '---'"

            # Find end of frontmatter
            end_marker = content.find("\n---\n", 4)
            assert end_marker > 0, \
                f"{skill_name}: YAML frontmatter must end with '---'"

    def test_yaml_frontmatter_required_fields(self, skills_dir, skill_names):
        """All skills must have required YAML fields"""
        for skill_name in skill_names:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()

            # Extract YAML frontmatter
            start = content.find("---\n") + 4
            end = content.find("\n---\n", start)
            frontmatter_text = content[start:end]

            # Parse YAML
            frontmatter = yaml.safe_load(frontmatter_text)

            # Check required fields
            assert "name" in frontmatter, f"{skill_name}: Missing 'name' field"
            assert "description" in frontmatter, f"{skill_name}: Missing 'description' field"

            # Validate name matches directory
            assert frontmatter["name"] == skill_name, \
                f"{skill_name}: YAML 'name' ({frontmatter['name']}) must match directory name"

    def test_yaml_frontmatter_optional_fields(self, skills_dir, skill_names):
        """Validate optional YAML fields if present"""
        expected_tools = {
            "fact-check": ["WebSearch", "WebFetch", "Read", "Grep"],
            "pre-commit": ["Bash", "Read", "Grep"],
            "git-workflow": ["Bash", "Read", "Grep"]
        }

        for skill_name in skill_names:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()

            # Extract and parse YAML
            start = content.find("---\n") + 4
            end = content.find("\n---\n", start)
            frontmatter_text = content[start:end]
            frontmatter = yaml.safe_load(frontmatter_text)

            # Check tools if specified
            if "tools" in frontmatter:
                tools = frontmatter["tools"]
                if isinstance(tools, str):
                    tools = [t.strip() for t in tools.split(",")]

                expected = expected_tools.get(skill_name, [])
                assert set(tools) == set(expected), \
                    f"{skill_name}: Tools mismatch. Expected {expected}, got {tools}"

            # Check model if specified
            if "model" in frontmatter:
                valid_models = ["sonnet", "opus", "haiku"]
                assert frontmatter["model"] in valid_models, \
                    f"{skill_name}: Invalid model '{frontmatter['model']}'. Must be one of {valid_models}"


class TestSkillContent:
    """Test skill file content and size"""

    def test_skill_file_size(self, skills_dir, skill_names):
        """Skills must be under 800 lines (hard limit)"""
        import warnings

        for skill_name in skill_names:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()
            line_count = len(content.splitlines())

            # Hard limit: 800 lines
            assert line_count < 800, \
                f"{skill_name}: Skill file too large ({line_count} lines > 800 hard limit)"

            # Warning for files over 500 lines (readability concern)
            if line_count > 500:
                warnings.warn(
                    f"{skill_name}: Skill file larger than recommended "
                    f"({line_count} lines > 500 recommended limit). "
                    "Consider splitting into multiple skills.",
                    UserWarning
                )

    def test_skill_has_purpose_section(self, skills_dir, skill_names):
        """All skills should have a Purpose section"""
        for skill_name in skill_names:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()

            assert "**Purpose**:" in content or "## Purpose" in content, \
                f"{skill_name}: Missing Purpose section"

    def test_skill_has_workflow_or_examples(self, skills_dir, skill_names):
        """All skills should have Workflow or Examples section"""
        for skill_name in skill_names:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()

            has_workflow = "## Workflow" in content or "### Workflow" in content
            has_examples = "## Examples" in content or "### Examples" in content

            assert has_workflow or has_examples, \
                f"{skill_name}: Missing Workflow or Examples section"


class TestSkillReferences:
    """Test skill reference files and symlinks"""

    def test_pre_commit_has_error_patterns_symlink(self, skills_dir, pitfalls_file):
        """pre-commit skill should have symlink to PITFALLS.md"""
        symlink = skills_dir / "pre-commit" / "references" / "error-patterns.md"

        assert symlink.exists(), \
            "pre-commit skill missing error-patterns.md symlink"

        # Check it's a symlink
        assert symlink.is_symlink(), \
            "error-patterns.md should be a symlink"

        # Check it points to PITFALLS.md
        target = symlink.resolve()
        assert target == pitfalls_file.resolve(), \
            f"error-patterns.md symlink points to {target}, expected {pitfalls_file}"

    def test_git_workflow_has_git_errors_reference(self, skills_dir):
        """git-workflow skill should have git-errors.md reference"""
        git_errors = skills_dir / "git-workflow" / "references" / "git-errors.md"

        assert git_errors.exists(), \
            "git-workflow skill missing git-errors.md reference"

        # Check it contains git error entries
        content = git_errors.read_text()
        assert "GIT-001" in content, \
            "git-errors.md should contain GIT-001 entry"
        assert "GIT-002" in content, \
            "git-errors.md should contain GIT-002 entry"


class TestSkillIntegration:
    """Test integration between skills and other components"""

    def test_skills_reference_pitfalls_md(self, skills_dir, skill_names):
        """Skills should reference PITFALLS.md where appropriate"""
        skills_should_reference = ["pre-commit", "git-workflow"]

        for skill_name in skills_should_reference:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()

            assert "PITFALLS.md" in content, \
                f"{skill_name}: Should reference PITFALLS.md"

    def test_skills_reference_fact_check_skill(self, skills_dir):
        """Some skills should suggest using /fact-check"""
        should_reference = ["pre-commit", "git-workflow"]

        for skill_name in should_reference:
            skill_file = skills_dir / skill_name / "SKILL.md"
            content = skill_file.read_text()

            assert "/fact-check" in content or "fact-check" in content, \
                f"{skill_name}: Should reference /fact-check skill"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
