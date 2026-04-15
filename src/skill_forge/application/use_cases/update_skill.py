"""Use case: update installed skills from a registry.

``UpdateSkill`` compares the installed version of each skill against the
registry's latest, then downloads and installs any newer versions it finds.

Supports:
  --dry-run   report available updates without installing
  --yes       skip the per-skill confirmation prompt (CLI wraps this)
  --pin       force a specific version instead of latest
  --registry  explicit registry base URL (falls back to default config)
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from skill_forge.application.use_cases.publish_skill import (
    InstallFromUrl,
    InstallFromUrlRequest,
)
from skill_forge.domain.model import (
    InstallTarget,
    Skill,
    SkillScope,
    _version_key,
)
from skill_forge.domain.ports import PackFetcher, SkillInstaller, SkillParser


@dataclass(frozen=True)
class UpdateRequest:
    """Parameters for the ``update`` use case."""

    scope: SkillScope = SkillScope.GLOBAL
    target: InstallTarget = InstallTarget.CLAUDE
    skill_name: str | None = None  # None → update all installed skills
    dry_run: bool = False
    registry_url: str = ""  # base URL, e.g. https://raw.githubusercontent.com/…/main
    pin_version: str = ""   # pin to a specific version instead of latest


@dataclass(frozen=True)
class UpdateRecord:
    """Outcome for a single skill considered for update."""

    skill_name: str
    old_version: str
    new_version: str
    pack_url: str
    sha256: str
    would_update: bool  # True if an update is available (even in dry-run)
    updated: bool       # True only if the pack was actually installed


@dataclass
class UpdateResponse:
    """Aggregated result of an update run."""

    records: list[UpdateRecord] = field(default_factory=list)

    @property
    def updated_count(self) -> int:
        """Number of skills actually installed."""
        return sum(1 for r in self.records if r.updated)

    @property
    def available_count(self) -> int:
        """Number of skills with an available update (including dry-run)."""
        return sum(1 for r in self.records if r.would_update)


class UpdateSkill:
    """Compare installed skills against a registry and install newer versions.

    Args:
        installer:        Skill installer port (for scanning installed skills).
        parser:           Skill parser (for reading installed SKILL.md versions).
        fetcher:          HTTP fetcher (for downloading registry index and packs).
        install_from_url: InstallFromUrl use case that handles fetch+unpack+install.
    """

    def __init__(
        self,
        installer: SkillInstaller,
        parser: SkillParser,
        fetcher: PackFetcher,
        install_from_url: InstallFromUrl,
    ) -> None:
        self._installer = installer
        self._parser = parser
        self._fetcher = fetcher
        self._install_from_url = install_from_url

    def execute(self, request: UpdateRequest) -> UpdateResponse:
        if not request.registry_url:
            raise ValueError(
                "registry_url is required for update. "
                "Pass '--registry <url>' or set a default with "
                "'skills-forge registry set-default <name>'."
            )

        # 1. Collect installed skills and their versions
        installed = self._collect_installed(request.scope)
        if request.skill_name:
            if request.skill_name not in installed:
                raise ValueError(
                    f"Skill '{request.skill_name}' is not installed at "
                    f"{request.scope.value} scope. "
                    f"Install it first with 'skills-forge install {request.skill_name}'."
                )
            installed = {request.skill_name: installed[request.skill_name]}

        # 2. Fetch registry index
        index_url = request.registry_url.rstrip("/") + "/index.json"
        index = self._fetcher.fetch_index(index_url)

        # 3. Compare and update
        records: list[UpdateRecord] = []
        for name, current_version in installed.items():
            indexed = next(
                (s for s in index.skills if s.name == name), None
            )
            if indexed is None:
                continue  # skill not in this registry — skip silently

            # Determine target version
            target_version = (
                request.pin_version if request.pin_version else indexed.latest
            )

            iv = indexed.find(target_version)
            if iv is None:
                continue  # requested version not in registry

            pack_url = f"{request.registry_url.rstrip('/')}/{iv.path}"
            would_update = _version_key(target_version) > _version_key(current_version)

            if not would_update:
                records.append(
                    UpdateRecord(
                        skill_name=name,
                        old_version=current_version,
                        new_version=target_version,
                        pack_url=pack_url,
                        sha256=iv.sha256,
                        would_update=False,
                        updated=False,
                    )
                )
                continue

            # Perform actual install unless dry-run
            updated = False
            if not request.dry_run:
                with tempfile.TemporaryDirectory() as tmpdir:
                    install_req = InstallFromUrlRequest(
                        url=pack_url,
                        dest_dir=Path(tmpdir) / "output_skills",
                        scope=request.scope,
                        target=request.target,
                        expected_sha256=iv.sha256,
                    )
                    self._install_from_url.execute(install_req)
                    updated = True

            records.append(
                UpdateRecord(
                    skill_name=name,
                    old_version=current_version,
                    new_version=target_version,
                    pack_url=pack_url,
                    sha256=iv.sha256,
                    would_update=True,
                    updated=updated,
                )
            )

        return UpdateResponse(records=records)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _collect_installed(self, scope: SkillScope) -> dict[str, str]:
        """Return ``{skill_name: version}`` for all installed skills in scope."""
        all_targets = self._installer.scan_all_targets(scope)
        result: dict[str, str] = {}
        seen_names: set[str] = set()

        for _target, paths in all_targets.items():
            for p in paths:
                name = p.name
                if name in seen_names:
                    continue
                seen_names.add(name)

                skill_md = _find_skill_md(p)
                if skill_md is None:
                    result[name] = "0.0.0"  # treat missing SKILL.md as v0
                    continue

                try:
                    content = skill_md.read_text(encoding="utf-8")
                    skill: Skill = self._parser.parse(
                        content, base_path=skill_md.parent
                    )
                    result[name] = skill.version
                except Exception:
                    result[name] = "0.0.0"

        return result


# ── helpers ───────────────────────────────────────────────────────────────────


def _find_skill_md(path: Path) -> Path | None:
    """Return the SKILL.md path for a directory or symlink, or None."""
    resolved = path.resolve() if path.is_symlink() else path
    candidate = resolved / "SKILL.md"
    return candidate if candidate.exists() else None


__all__ = ["UpdateRecord", "UpdateRequest", "UpdateResponse", "UpdateSkill"]
