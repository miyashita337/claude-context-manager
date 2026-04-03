from __future__ import annotations
from src.analyzer.project_mapper import ProjectMapper


class TestProjectMapper:
    def test_extract_project_name_simple(self) -> None:
        mapper = ProjectMapper(username="testuser")
        assert mapper.extract_project_name("-Users-testuser-my-project") == "my-project"

    def test_extract_project_name_home(self) -> None:
        mapper = ProjectMapper(username="testuser")
        assert mapper.extract_project_name("-Users-testuser") == "home"

    def test_extract_project_name_nested(self) -> None:
        mapper = ProjectMapper(username="testuser")
        assert mapper.extract_project_name("-Users-testuser-org-repo") == "org-repo"

    def test_worktree_to_parent(self) -> None:
        mapper = ProjectMapper(username="testuser")
        assert (
            mapper.extract_project_name(
                "-Users-testuser-my-project--claude-worktrees-feature-1"
            )
            == "my-project"
        )

    def test_worktree_to_parent_nested(self) -> None:
        mapper = ProjectMapper(username="testuser")
        assert (
            mapper.extract_project_name(
                "-Users-testuser-my-project--claude-worktrees-fix-bug-123"
            )
            == "my-project"
        )

    def test_list_project_dirs(self, tmp_path) -> None:
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        (projects_dir / "-Users-testuser-alpha").mkdir()
        (projects_dir / "-Users-testuser-alpha--claude-worktrees-feat").mkdir()
        (projects_dir / "-Users-testuser-beta").mkdir()
        (projects_dir / "-private-tmp").mkdir()
        mapper = ProjectMapper(username="testuser", projects_dir=projects_dir)
        dirs = mapper.list_project_dirs()
        names = [d.name for d in dirs]
        assert "-Users-testuser-alpha" in names
        assert "-Users-testuser-beta" in names
        assert "-private-tmp" not in names

    def test_group_by_parent_project(self) -> None:
        mapper = ProjectMapper(username="testuser")
        session_ids = [
            "-Users-testuser-alpha",
            "-Users-testuser-alpha--claude-worktrees-feat-1",
            "-Users-testuser-alpha--claude-worktrees-feat-2",
            "-Users-testuser-beta",
        ]
        groups = mapper.group_by_parent(session_ids)
        assert set(groups.keys()) == {"alpha", "beta"}
        assert len(groups["alpha"]) == 3
        assert len(groups["beta"]) == 1
