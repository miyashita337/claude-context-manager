"""Tests for CLAUDE.md guidance rules and workflow guide (#93, #95)."""
import pathlib
import pytest

# Paths
_GLOBAL_CLAUDE_MD = pathlib.Path.home() / ".claude" / "CLAUDE.md"
_WORKTREE = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOW_GUIDE = _WORKTREE / ".claude" / "docs" / "workflow-guide.md"
_PROJECT_CLAUDE_MD = _WORKTREE / ".claude" / "CLAUDE.md"

_skip_no_global = pytest.mark.skipif(
    not _GLOBAL_CLAUDE_MD.exists(),
    reason="~/.claude/CLAUDE.md not available (CI environment)",
)


@_skip_no_global
class TestCLAUDEMdGuidance:
    """#93: Global CLAUDE.md guidance rules."""

    def test_qa_section_exists(self):
        text = _GLOBAL_CLAUDE_MD.read_text(encoding="utf-8")
        assert "# 質問の受け答え" in text

    def test_existing_step_by_step_rule_preserved(self):
        text = _GLOBAL_CLAUDE_MD.read_text(encoding="utf-8")
        assert "ステップバイステップ" in text

    def test_recommend_one_option_rule_exists(self):
        text = _GLOBAL_CLAUDE_MD.read_text(encoding="utf-8")
        assert "推奨案を1つ明示" in text

    def test_default_action_rule_exists(self):
        text = _GLOBAL_CLAUDE_MD.read_text(encoding="utf-8")
        assert "デフォルトアクションを提示" in text

    def test_rules_in_correct_section(self):
        text = _GLOBAL_CLAUDE_MD.read_text(encoding="utf-8")
        qa_start = text.index("# 質問の受け答え")
        # Find next top-level section
        rest = text[qa_start + 1:]
        next_section = rest.find("\n# ")
        if next_section == -1:
            qa_section = rest
        else:
            qa_section = rest[:next_section]
        assert "推奨案を1つ明示" in qa_section
        assert "デフォルトアクションを提示" in qa_section

    def test_qa_section_not_bloated(self):
        """AP-3 prevention: QA section should be <=10 lines."""
        text = _GLOBAL_CLAUDE_MD.read_text(encoding="utf-8")
        qa_start = text.index("# 質問の受け答え")
        rest = text[qa_start:]
        next_section = rest.find("\n# ", 1)
        if next_section == -1:
            qa_section = rest
        else:
            qa_section = rest[:next_section]
        lines = [l for l in qa_section.strip().split("\n") if l.strip()]
        assert len(lines) <= 10, f"QA section has {len(lines)} lines, max 10"


class TestWorkflowGuide:
    """#95: Workflow improvement guide."""

    def test_file_exists(self):
        assert _WORKFLOW_GUIDE.exists(), f"{_WORKFLOW_GUIDE} does not exist"

    def test_plan_mode_section(self):
        text = _WORKFLOW_GUIDE.read_text(encoding="utf-8")
        assert "Plan Mode" in text or "plan mode" in text

    def test_clear_and_two_round_rule(self):
        text = _WORKFLOW_GUIDE.read_text(encoding="utf-8")
        assert "/clear" in text
        assert "2回" in text or "2回" in text

    def test_structured_prompt_section(self):
        text = _WORKFLOW_GUIDE.read_text(encoding="utf-8")
        assert "構造化" in text or "テーブル" in text or "箇条書き" in text

    def test_multi_session_section(self):
        text = _WORKFLOW_GUIDE.read_text(encoding="utf-8")
        assert "マルチセッション" in text or "セッション分割" in text

    def test_under_100_lines(self):
        text = _WORKFLOW_GUIDE.read_text(encoding="utf-8")
        lines = text.strip().split("\n")
        assert len(lines) <= 100, f"Guide has {len(lines)} lines, max 100"

    def test_has_data_source_reference(self):
        text = _WORKFLOW_GUIDE.read_text(encoding="utf-8")
        assert "SFEIR" in text or "claude.com" in text or "code.claude.com" in text or "anthropic" in text.lower()

    def test_project_claude_md_references_guide(self):
        text = _PROJECT_CLAUDE_MD.read_text(encoding="utf-8")
        assert "workflow-guide" in text
