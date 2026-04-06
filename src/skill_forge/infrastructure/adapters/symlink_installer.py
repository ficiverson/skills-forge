"""Adapter: installs skills via symlinks (global or project scope)."""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import SkillScope
from skill_forge.domain.ports import SkillInstaller


class SymlinkSkillInstaller(SkillInstaller):
    """Installs skills by creating symlinks.

    Global: ~/.claude/skills/<skill-name> -> <skill-path>
    Project: .claude/skills/<skill-name> -> <skill-path>
    """

    def __init__(
        self,
        global_skills_dir: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        self._global_dir = global_skills_dir or Path.home() / ".claude" / "skills"
        self._project_root = project_root or Path.cwd()

    def install(self, skill_path: Path, scope: SkillScope) -> Path:
        target_dir = self._resolve_dir(scope)
        target_dir.mkdir(parents=True, exist_ok=True)

        skill_name = skill_path.name
        link_path = target_dir / skill_name

        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()

        link_path.symlink_to(skill_path.resolve())
        return link_path

    def uninstall(self, skill_name: str, scope: SkillScope) -> bool:
        target_dir = self._resolve_dir(scope)
        link_path = target_dir / skill_name

        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
            return True
        return False

    def is_installed(self, skill_name: str, scope: SkillScope) -> bool:
        target_dir = self._resolve_dir(scope)
        link_path = target_dir / skill_name
        return link_path.exists() or link_path.is_symlink()

    def list_installed(self, scope: SkillScope) -> list[Path]:
        target_dir = self._resolve_dir(scope)
        if not target_dir.exists():
            return []
        return [
            p for p in target_dir.iterdir()
            if p.is_dir() or p.is_symlink()
        ]

    def _resolve_dir(self, scope: SkillScope) -> Path:
        if scope == SkillScope.GLOBAL:
            return self._global_dir
        return self._project_root / ".claude" / "skills"
