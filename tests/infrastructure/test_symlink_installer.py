"""Tests for SymlinkSkillInstaller with InstallTarget support."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_forge.domain.model import InstallTarget, SkillScope
from skill_forge.infrastructure.adapters.symlink_installer import (
    SymlinkSkillInstaller,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill(tmp_path: Path, name: str = "my-skill") -> Path:
    skill_dir = tmp_path / "source" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\nbody\n")
    return skill_dir


def _installer(tmp_path: Path) -> SymlinkSkillInstaller:
    """Installer whose *global* claude path is redirected into tmp_path."""
    return SymlinkSkillInstaller(
        global_skills_dir=tmp_path / "global" / ".claude" / "skills",
        project_root=tmp_path / "project",
    )


# ---------------------------------------------------------------------------
# Single-target installs
# ---------------------------------------------------------------------------

class TestSingleTargetInstall:
    def test_claude_global_default(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = _installer(tmp_path)
        paths = installer.install(skill, SkillScope.GLOBAL, InstallTarget.CLAUDE)
        assert len(paths) == 1
        assert paths[0].name == "my-skill"
        assert paths[0].is_symlink()

    def test_gemini_global(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths = installer.install(skill, SkillScope.GLOBAL, InstallTarget.GEMINI)
        assert len(paths) == 1
        assert ".gemini/skills" in str(paths[0])
        assert paths[0].is_symlink()

    def test_codex_global(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths = installer.install(skill, SkillScope.GLOBAL, InstallTarget.CODEX)
        assert ".codex/skills" in str(paths[0])

    def test_agents_global(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths = installer.install(skill, SkillScope.GLOBAL, InstallTarget.AGENTS)
        assert ".agents/skills" in str(paths[0])

    def test_agents_project(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths = installer.install(skill, SkillScope.PROJECT, InstallTarget.AGENTS)
        assert str(paths[0]).endswith(".agents/skills/my-skill")

    def test_vscode_project(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths = installer.install(skill, SkillScope.PROJECT, InstallTarget.VSCODE)
        assert ".github/skills" in str(paths[0])
        assert paths[0].is_symlink()

    def test_claude_project(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths = installer.install(skill, SkillScope.PROJECT, InstallTarget.CLAUDE)
        assert ".claude/skills" in str(paths[0])


# ---------------------------------------------------------------------------
# ALL target
# ---------------------------------------------------------------------------

class TestAllTarget:
    def test_all_global_writes_four_directories(self, tmp_path: Path) -> None:
        # GLOBAL + ALL → claude, gemini, codex, agents (vscode excluded)
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(
            global_skills_dir=tmp_path / "global" / ".claude" / "skills",
            project_root=tmp_path / "project",
        )
        # Patch home to tmp_path so we don't write into the real home dir
        original_home = Path.home
        Path.home = classmethod(lambda cls: tmp_path)  # type: ignore[method-assign]
        try:
            paths = installer.install(skill, SkillScope.GLOBAL, InstallTarget.ALL)
        finally:
            Path.home = original_home  # type: ignore[method-assign]
        assert len(paths) == 4
        path_strs = [str(p) for p in paths]
        assert any(".claude/skills" in p for p in path_strs)
        assert any(".gemini/skills" in p for p in path_strs)
        assert any(".codex/skills" in p for p in path_strs)
        assert any(".agents/skills" in p for p in path_strs)
        assert not any(".github/skills" in p for p in path_strs)  # vscode excluded globally

    def test_all_project_writes_five_directories(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths = installer.install(skill, SkillScope.PROJECT, InstallTarget.ALL)
        assert len(paths) == 5
        path_strs = [str(p) for p in paths]
        assert any(".claude/skills" in p for p in path_strs)
        assert any(".gemini/skills" in p for p in path_strs)
        assert any(".codex/skills" in p for p in path_strs)
        assert any(".github/skills" in p for p in path_strs)
        assert any(".agents/skills" in p for p in path_strs)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestInstallErrors:
    def test_vscode_global_raises(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        with pytest.raises(ValueError, match="VS Code has no global skills directory"):
            installer.install(skill, SkillScope.GLOBAL, InstallTarget.VSCODE)

    def test_reinstall_replaces_existing_symlink(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = SymlinkSkillInstaller(project_root=tmp_path / "project")
        paths1 = installer.install(skill, SkillScope.PROJECT, InstallTarget.AGENTS)
        paths2 = installer.install(skill, SkillScope.PROJECT, InstallTarget.AGENTS)
        assert paths1[0] == paths2[0]
        assert paths2[0].is_symlink()


# ---------------------------------------------------------------------------
# Backward-compat: install() always returns list[Path]
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_install_always_returns_list(self, tmp_path: Path) -> None:
        skill = _make_skill(tmp_path)
        installer = _installer(tmp_path)
        result = installer.install(skill, SkillScope.GLOBAL)
        assert isinstance(result, list)
        assert len(result) >= 1
