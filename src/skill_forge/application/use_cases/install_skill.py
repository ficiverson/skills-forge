"""Use case: install or uninstall a skill."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from skill_forge.domain.model import InstallTarget, SkillScope
from skill_forge.domain.ports import SkillInstaller, SkillParser


@dataclass
class InstallSkillRequest:
    skill_path: Path
    scope: SkillScope = SkillScope.GLOBAL
    target: InstallTarget = InstallTarget.CLAUDE
    skip_deps: bool = False


@dataclass
class InstallSkillResponse:
    installed_paths: list[Path] = field(default_factory=list)
    scope: SkillScope = SkillScope.GLOBAL
    target: InstallTarget = InstallTarget.CLAUDE
    missing_dependencies: list[str] = field(default_factory=list)

    @property
    def installed_path(self) -> Path:
        """Convenience accessor for the first (or only) installed path."""
        return self.installed_paths[0]


@dataclass
class UninstallSkillRequest:
    skill_name: str
    scope: SkillScope = SkillScope.GLOBAL
    target: InstallTarget = InstallTarget.ALL


@dataclass
class UninstallSkillResponse:
    removed_paths: list[Path]
    scope: SkillScope
    target: InstallTarget

    @property
    def was_installed(self) -> bool:
        """True if at least one symlink was actually removed."""
        return len(self.removed_paths) > 0


class InstallSkill:
    """Install a skill into one or more agent-CLI tool directories.

    When a ``parser`` is provided, the SKILL.md is parsed before installation
    and each ``depends_on`` entry is checked against already-installed skills.
    Missing dependencies are reported in the response — installation proceeds
    regardless, so the caller decides whether to abort or just warn.

    Pass ``skip_deps=True`` in the request (or omit the parser) to bypass
    the dependency check entirely.
    """

    def __init__(
        self,
        installer: SkillInstaller,
        parser: SkillParser | None = None,
    ) -> None:
        self._installer = installer
        self._parser = parser

    def execute(self, request: InstallSkillRequest) -> InstallSkillResponse:
        missing: list[str] = []

        if self._parser and not request.skip_deps:
            missing = self._check_dependencies(request.skill_path, request.scope)

        paths = self._installer.install(
            request.skill_path, request.scope, request.target
        )
        return InstallSkillResponse(
            installed_paths=paths,
            scope=request.scope,
            target=request.target,
            missing_dependencies=missing,
        )

    def _check_dependencies(
        self, skill_path: Path, scope: SkillScope
    ) -> list[str]:
        """Return names of depends_on skills that are not currently installed."""
        skill_md = skill_path / "SKILL.md" if skill_path.is_dir() else skill_path
        if not skill_md.exists():
            return []

        try:
            skill = self._parser.parse(  # type: ignore[union-attr]
                skill_md.read_text(encoding="utf-8"), skill_md.parent
            )
        except Exception:  # pragma: no cover  # broad catch: parser errors must not abort install
            return []

        return [
            dep.skill_name
            for dep in skill.depends_on
            if not self._installer.is_installed(dep.skill_name, scope)
        ]


class UninstallSkill:
    """Remove a previously installed skill from one or all targets.

    Idempotent: uninstalling a skill that is not installed is not an error —
    the response will have an empty ``removed_paths`` list.
    """

    def __init__(self, installer: SkillInstaller) -> None:
        self._installer = installer

    def execute(self, request: UninstallSkillRequest) -> UninstallSkillResponse:
        removed = self._installer.uninstall(
            request.skill_name, request.scope, request.target
        )
        return UninstallSkillResponse(
            removed_paths=removed,
            scope=request.scope,
            target=request.target,
        )
