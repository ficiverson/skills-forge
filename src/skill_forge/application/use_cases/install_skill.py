"""Use case: install or uninstall a skill."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from skill_forge.domain.model import InstallTarget, SkillScope
from skill_forge.domain.ports import SkillInstaller


@dataclass
class InstallSkillRequest:
    skill_path: Path
    scope: SkillScope = SkillScope.GLOBAL
    target: InstallTarget = InstallTarget.CLAUDE


@dataclass
class InstallSkillResponse:
    installed_paths: list[Path] = field(default_factory=list)
    scope: SkillScope = SkillScope.GLOBAL
    target: InstallTarget = InstallTarget.CLAUDE

    @property
    def installed_path(self) -> Path:
        """Convenience accessor for the first (or only) installed path."""
        return self.installed_paths[0]


@dataclass
class UninstallSkillRequest:
    skill_name: str
    scope: SkillScope = SkillScope.GLOBAL


@dataclass
class UninstallSkillResponse:
    was_installed: bool
    scope: SkillScope


class InstallSkill:
    """Install a skill into one or more agent-CLI tool directories."""

    def __init__(self, installer: SkillInstaller) -> None:
        self._installer = installer

    def execute(self, request: InstallSkillRequest) -> InstallSkillResponse:
        paths = self._installer.install(
            request.skill_path, request.scope, request.target
        )
        return InstallSkillResponse(
            installed_paths=paths,
            scope=request.scope,
            target=request.target,
        )


class UninstallSkill:
    """Remove a previously installed skill."""

    def __init__(self, installer: SkillInstaller) -> None:
        self._installer = installer

    def execute(self, request: UninstallSkillRequest) -> UninstallSkillResponse:
        was_installed = self._installer.uninstall(
            request.skill_name, request.scope
        )
        return UninstallSkillResponse(
            was_installed=was_installed,
            scope=request.scope,
        )
