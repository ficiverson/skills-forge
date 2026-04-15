"""Use case: diff the installed version of a skill against the registry latest.

``DiffSkill`` locates the named skill in the first target directory where
it is installed, reads its SKILL.md, fetches the registry to find the latest
pack URL, downloads it into a temp directory, and produces a unified diff of
the two SKILL.md files.  When the skill is up-to-date (same version and same
content) the diff is empty.
"""

from __future__ import annotations

import difflib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from skill_forge.domain.model import SkillScope
from skill_forge.domain.ports import PackFetcher, SkillInstaller, SkillParser


@dataclass(frozen=True)
class DiffRequest:
    """Parameters for the ``diff`` use case."""

    skill_name: str
    scope: SkillScope = SkillScope.GLOBAL
    registry_url: str = ""
    context_lines: int = 3  # unified diff context


@dataclass
class DiffResponse:
    """Result of the ``diff`` use case."""

    skill_name: str
    installed_version: str
    registry_version: str
    diff_lines: list[str] = field(default_factory=list)

    @property
    def has_diff(self) -> bool:
        return bool(self.diff_lines)

    @property
    def is_up_to_date(self) -> bool:
        from skill_forge.domain.model import _version_key

        if not self.registry_version:
            return True
        return _version_key(self.installed_version) >= _version_key(self.registry_version)


class DiffSkill:
    """Compare an installed skill's SKILL.md against the registry latest.

    Requires a ``registry_url`` in the request.  Raises ``ValueError`` when
    the skill is not installed or the registry URL is missing.
    """

    def __init__(
        self,
        installer: SkillInstaller,
        parser: SkillParser,
        fetcher: PackFetcher,
    ) -> None:
        self._installer = installer
        self._parser = parser
        self._fetcher = fetcher

    def execute(self, request: DiffRequest) -> DiffResponse:
        if not request.registry_url:
            raise ValueError(
                "registry_url is required for diff. "
                "Pass '--registry <url>' or configure a default registry with "
                "'skills-forge registry add <name> <url>'."
            )

        # ── 1. Find the installed skill ─────────────────────────────────────
        all_targets = self._installer.scan_all_targets(request.scope)
        installed_path: Path | None = None
        for paths in all_targets.values():
            for p in paths:
                if p.name == request.skill_name:
                    installed_path = p
                    break
            if installed_path:
                break

        if installed_path is None:
            raise ValueError(
                f"Skill '{request.skill_name}' is not installed "
                f"(scope={request.scope.value})"
            )

        # Resolve symlinks for reading
        resolved = installed_path.resolve() if installed_path.is_symlink() else installed_path
        skill_md_path = resolved / "SKILL.md"
        if not skill_md_path.exists():
            raise ValueError(
                f"Skill '{request.skill_name}': SKILL.md not found at {skill_md_path}"
            )
        local_content = skill_md_path.read_text(encoding="utf-8")
        local_skill = self._parser.parse(local_content, base_path=skill_md_path.parent)
        installed_version = local_skill.version

        # ── 2. Fetch registry index ─────────────────────────────────────────
        index_url = request.registry_url.rstrip("/") + "/index.json"
        index = self._fetcher.fetch_index(index_url)

        registry_skill = None
        for s in index.skills:
            if s.name == request.skill_name:
                registry_skill = s
                break

        if registry_skill is None:
            # Skill not in registry — report versions only, no diff lines
            return DiffResponse(
                skill_name=request.skill_name,
                installed_version=installed_version,
                registry_version="",
            )

        registry_version = registry_skill.latest
        latest_indexed = registry_skill.find(registry_version)

        if latest_indexed is None:
            return DiffResponse(
                skill_name=request.skill_name,
                installed_version=installed_version,
                registry_version=registry_version,
            )

        # ── 3. Download & unpack the registry pack into a temp dir ──────────
        pack_url = index.base_url.rstrip("/") + "/" + latest_indexed.path.lstrip("/")
        remote_content: str | None = None

        try:
            with tempfile.TemporaryDirectory(prefix="skills-forge-diff-") as tmp_dir:
                pack_path = Path(tmp_dir) / "remote.skillpack"
                self._fetcher.fetch(pack_url, pack_path)

                import zipfile

                with zipfile.ZipFile(pack_path) as zf:
                    # Find SKILL.md inside the pack (may be nested)
                    candidates = [
                        n for n in zf.namelist()
                        if n.endswith("SKILL.md")
                        and request.skill_name in n
                    ]
                    # Fallback: any SKILL.md
                    if not candidates:
                        candidates = [n for n in zf.namelist() if n.endswith("SKILL.md")]

                    if candidates:
                        remote_content = zf.read(candidates[0]).decode("utf-8")
        except Exception as exc:
            # Network/IO errors: return partial response without diff
            return DiffResponse(
                skill_name=request.skill_name,
                installed_version=installed_version,
                registry_version=registry_version,
                diff_lines=[f"# Could not fetch remote pack: {exc}"],
            )

        if remote_content is None:
            return DiffResponse(
                skill_name=request.skill_name,
                installed_version=installed_version,
                registry_version=registry_version,
                diff_lines=["# SKILL.md not found inside remote pack"],
            )

        # ── 4. Produce unified diff ─────────────────────────────────────────
        diff_lines = list(
            difflib.unified_diff(
                local_content.splitlines(keepends=True),
                remote_content.splitlines(keepends=True),
                fromfile=f"{request.skill_name}/SKILL.md (installed {installed_version})",
                tofile=f"{request.skill_name}/SKILL.md (registry  {registry_version})",
                n=request.context_lines,
            )
        )

        return DiffResponse(
            skill_name=request.skill_name,
            installed_version=installed_version,
            registry_version=registry_version,
            diff_lines=diff_lines,
        )


__all__ = ["DiffRequest", "DiffResponse", "DiffSkill"]
