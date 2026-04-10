"""Tests for the InstallSkill and UninstallSkill use cases (v0.3.0)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from skill_forge.application.use_cases.install_skill import (
    InstallSkill,
    InstallSkillRequest,
    UninstallSkill,
    UninstallSkillRequest,
)
from skill_forge.domain.model import Dependency, InstallTarget, Skill, SkillScope
from skill_forge.domain.ports import SkillInstaller, SkillParser

# ── Stubs ─────────────────────────────────────────────────────────────────────


class _StubInstaller(SkillInstaller):
    def __init__(self, installed: list[str] | None = None) -> None:
        self._installed: set[str] = set(installed or [])
        self.installed_calls: list[Path] = []
        self.removed_calls: list[tuple[str, SkillScope]] = []

    def install(self, skill_path, scope, target=InstallTarget.CLAUDE):  # type: ignore[override]
        self.installed_calls.append(skill_path)
        return [Path(f"/fake/{skill_path.name}")]

    def uninstall(self, skill_name, scope, target=InstallTarget.ALL):  # type: ignore[override]
        self.removed_calls.append((skill_name, scope))
        if skill_name in self._installed:
            self._installed.discard(skill_name)
            return [Path(f"/fake/{skill_name}")]
        return []

    def is_installed(self, skill_name, scope):  # type: ignore[override]
        return skill_name in self._installed

    def list_installed(self, scope):  # type: ignore[override]
        return [Path(f"/fake/{n}") for n in self._installed]


class _StubParser(SkillParser):
    """Returns a skill with the given depends_on list."""

    def __init__(self, depends_on: list[str] | None = None) -> None:
        self._deps = depends_on or []

    def parse(self, content: str, base_path: Path | None = None) -> Skill:  # type: ignore[override]
        skill = MagicMock(spec=Skill)
        skill.depends_on = [Dependency(skill_name=d, reason="test") for d in self._deps]
        return skill


# ── InstallSkill ──────────────────────────────────────────────────────────────


class TestInstallSkill:
    def test_install_returns_paths(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        use_case = InstallSkill(installer=_StubInstaller())
        response = use_case.execute(InstallSkillRequest(skill_path=skill_dir))

        assert len(response.installed_paths) == 1
        assert response.missing_dependencies == []

    def test_no_missing_deps_when_all_installed(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "a-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: a-skill\ndepends_on: b-skill\n---\n")

        installer = _StubInstaller(installed=["b-skill"])
        parser = _StubParser(depends_on=["b-skill"])
        use_case = InstallSkill(installer=installer, parser=parser)

        response = use_case.execute(InstallSkillRequest(skill_path=skill_dir))

        assert response.missing_dependencies == []

    def test_reports_missing_dependency(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "a-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: a-skill\ndepends_on: b-skill\n---\n")

        installer = _StubInstaller(installed=[])  # b-skill NOT installed
        parser = _StubParser(depends_on=["b-skill"])
        use_case = InstallSkill(installer=installer, parser=parser)

        response = use_case.execute(InstallSkillRequest(skill_path=skill_dir))

        assert "b-skill" in response.missing_dependencies

    def test_skip_deps_suppresses_check(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "a-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: a-skill\ndepends_on: b-skill\n---\n")

        installer = _StubInstaller(installed=[])
        parser = _StubParser(depends_on=["b-skill"])
        use_case = InstallSkill(installer=installer, parser=parser)

        response = use_case.execute(
            InstallSkillRequest(skill_path=skill_dir, skip_deps=True)
        )

        assert response.missing_dependencies == []

    def test_no_parser_no_dep_check(self, tmp_path: Path) -> None:
        """Without a parser, dependency check is silently skipped."""
        skill_dir = tmp_path / "a-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: a-skill\ndepends_on: b-skill\n---\n")

        use_case = InstallSkill(installer=_StubInstaller(), parser=None)
        response = use_case.execute(InstallSkillRequest(skill_path=skill_dir))

        assert response.missing_dependencies == []

    def test_multiple_missing_dependencies(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "a-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: a-skill\n---\n")

        installer = _StubInstaller(installed=["c-skill"])
        parser = _StubParser(depends_on=["b-skill", "c-skill", "d-skill"])
        use_case = InstallSkill(installer=installer, parser=parser)

        response = use_case.execute(InstallSkillRequest(skill_path=skill_dir))

        assert set(response.missing_dependencies) == {"b-skill", "d-skill"}


# ── UninstallSkill ────────────────────────────────────────────────────────────


class TestUninstallSkill:
    def test_uninstall_installed_skill(self) -> None:
        installer = _StubInstaller(installed=["my-skill"])
        use_case = UninstallSkill(installer=installer)

        response = use_case.execute(
            UninstallSkillRequest(skill_name="my-skill", scope=SkillScope.GLOBAL)
        )

        assert response.was_installed is True
        assert len(response.removed_paths) == 1

    def test_uninstall_missing_skill_is_idempotent(self) -> None:
        installer = _StubInstaller(installed=[])
        use_case = UninstallSkill(installer=installer)

        response = use_case.execute(
            UninstallSkillRequest(skill_name="ghost-skill", scope=SkillScope.GLOBAL)
        )

        assert response.was_installed is False
        assert response.removed_paths == []

    def test_uninstall_with_explicit_target(self) -> None:
        installer = _StubInstaller(installed=["my-skill"])
        use_case = UninstallSkill(installer=installer)

        response = use_case.execute(
            UninstallSkillRequest(
                skill_name="my-skill",
                scope=SkillScope.PROJECT,
                target=InstallTarget.CLAUDE,
            )
        )

        assert response.target == InstallTarget.CLAUDE
        assert response.was_installed is True
