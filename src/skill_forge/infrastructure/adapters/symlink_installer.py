"""Adapter: installs skills via symlinks into agent-CLI tool directories.

All supported targets share the same SKILL.md format (agentskills.io open
standard).  The only difference between them is the destination path.

Global paths (--scope global / user):
    claude  → ~/.claude/skills/<name>
    gemini  → ~/.gemini/skills/<name>
    codex   → ~/.codex/skills/<name>
    agents  → ~/.agents/skills/<name>   ← universal cross-vendor alias
    vscode  → (not supported at global scope; VS Code has no global skills dir)

Project paths (--scope project):
    claude  → .claude/skills/<name>
    gemini  → .gemini/skills/<name>
    codex   → .codex/skills/<name>
    vscode  → .github/skills/<name>
    agents  → .agents/skills/<name>     ← universal cross-vendor alias

all     → every applicable path for the chosen scope (vscode excluded at global)
"""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import InstallTarget, SkillScope
from skill_forge.domain.ports import SkillInstaller

# Targets that have a meaningful global (home-dir) path.
_GLOBAL_TARGETS: dict[InstallTarget, str] = {
    InstallTarget.CLAUDE:  ".claude/skills",
    InstallTarget.GEMINI:  ".gemini/skills",
    InstallTarget.CODEX:   ".codex/skills",
    InstallTarget.AGENTS:  ".agents/skills",
    # VSCODE intentionally omitted — no global skills dir
}

# Targets that have a project-relative path.
_PROJECT_TARGETS: dict[InstallTarget, str] = {
    InstallTarget.CLAUDE:  ".claude/skills",
    InstallTarget.GEMINI:  ".gemini/skills",
    InstallTarget.CODEX:   ".codex/skills",
    InstallTarget.VSCODE:  ".github/skills",
    InstallTarget.AGENTS:  ".agents/skills",
}


class SymlinkSkillInstaller(SkillInstaller):
    """Installs skills by creating symlinks into agent-CLI tool directories."""

    def __init__(
        self,
        global_skills_dir: Path | None = None,
        project_root: Path | None = None,
    ) -> None:
        # global_skills_dir kept for backward-compat (used when target=CLAUDE)
        self._legacy_global_dir = global_skills_dir or Path.home() / ".claude" / "skills"
        self._project_root = project_root or Path.cwd()

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    def install(
        self,
        skill_path: Path,
        scope: SkillScope,
        target: InstallTarget = InstallTarget.CLAUDE,
    ) -> list[Path]:
        """Symlink skill_path into every resolved target directory."""
        dirs = self._resolve_dirs(scope, target)
        installed: list[Path] = []
        for target_dir in dirs:
            target_dir.mkdir(parents=True, exist_ok=True)
            link_path = target_dir / skill_path.name
            if link_path.exists() or link_path.is_symlink():
                link_path.unlink()
            link_path.symlink_to(skill_path.resolve())
            installed.append(link_path)
        return installed

    def uninstall(self, skill_name: str, scope: SkillScope) -> bool:
        """Remove from the default (CLAUDE) target for the given scope."""
        target_dir = self._resolve_dirs(scope, InstallTarget.CLAUDE)[0]
        link_path = target_dir / skill_name
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
            return True
        return False

    def is_installed(self, skill_name: str, scope: SkillScope) -> bool:
        target_dir = self._resolve_dirs(scope, InstallTarget.CLAUDE)[0]
        link_path = target_dir / skill_name
        return link_path.exists() or link_path.is_symlink()

    def list_installed(self, scope: SkillScope) -> list[Path]:
        target_dir = self._resolve_dirs(scope, InstallTarget.CLAUDE)[0]
        if not target_dir.exists():
            return []
        return [p for p in target_dir.iterdir() if p.is_dir() or p.is_symlink()]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_dirs(self, scope: SkillScope, target: InstallTarget) -> list[Path]:
        """Return the concrete filesystem directories for (scope, target)."""
        if target == InstallTarget.ALL:
            mapping = (
                _GLOBAL_TARGETS if scope == SkillScope.GLOBAL else _PROJECT_TARGETS
            )
            return [self._make_path(scope, rel) for rel in mapping.values()]

        if target == InstallTarget.VSCODE and scope == SkillScope.GLOBAL:
            raise ValueError(
                "VS Code has no global skills directory. "
                "Use --scope project, or choose a different --target."
            )

        if scope == SkillScope.GLOBAL:
            rel = _GLOBAL_TARGETS.get(target)
            if rel is None:
                raise ValueError(f"Target '{target.value}' is not valid at global scope.")
            # Honour the legacy override for claude so tests that pass a custom
            # global_skills_dir continue to work unchanged.
            if target == InstallTarget.CLAUDE and self._legacy_global_dir != (
                Path.home() / ".claude" / "skills"
            ):
                return [self._legacy_global_dir]
            return [Path.home() / rel]

        # PROJECT scope
        rel = _PROJECT_TARGETS.get(target)
        if rel is None:
            raise ValueError(f"Target '{target.value}' is not valid at project scope.")
        return [self._project_root / rel]

    def _make_path(self, scope: SkillScope, rel: str) -> Path:
        if scope == SkillScope.GLOBAL:
            return Path.home() / rel
        return self._project_root / rel
