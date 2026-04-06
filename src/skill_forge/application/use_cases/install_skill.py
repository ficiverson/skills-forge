"""Use case: install or uninstall a skill."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_forge.domain.model import SkillScope
from skill_forge.domain.ports import SkillInstaller


@dataclass
class InstallSkillRequest:
    skill_path: Path
    scope: SkillScope = SkillScope.GLOBAL


@dataclass
class InstallSkillResponse:
    installed_path: Path
    scope: SkillScope


@dataclass
class UninstallSkillRequest:
    skill_name: str
    scope: SkillScope = SkillScope.GLOBAL


@dataclass
class UninstallSkillResponse:
    was_installed: bool
    scope: SkillScope


class InstallSkill:
    """Install a skill for Claude Code to discover."""

    def __init__(self, installer: SkillInstaller) -> None:
        self._installer = installer

    def execute(self, request: InstallSkillRequest) -> InstallSkillResponse:
        path = self._installer.install(request.skill_path, request.scope)
        return InstallSkillResponse(
            installed_path=path,
            scope=request.scope,
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
