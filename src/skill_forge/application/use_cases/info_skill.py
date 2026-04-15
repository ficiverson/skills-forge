"""Use case: display detailed information about an installed skill.

``GetSkillInfo`` locates a skill across all target directories for the given
scope, parses its SKILL.md, and optionally fetches the registry to report
whether a newer version is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from skill_forge.domain.model import InstallTarget, Skill, SkillScope
from skill_forge.domain.ports import PackFetcher, SkillInstaller, SkillParser


@dataclass(frozen=True)
class InfoRequest:
    """Parameters for the ``info`` use case."""

    skill_name: str
    scope: SkillScope = SkillScope.GLOBAL
    registry_url: str = ""  # base URL of a registry to compare versions against


@dataclass(frozen=True)
class InstallLocation:
    """Records one place where a skill is installed."""

    target: InstallTarget
    path: Path
    is_broken: bool  # symlink exists but points to a missing target


@dataclass
class InfoResponse:
    """Result of the ``info`` use case."""

    skill_name: str
    skill: Skill | None  # None if no valid installation found
    install_locations: list[InstallLocation] = field(default_factory=list)
    registry_latest: str | None = None  # None when registry was not checked / skill absent
    registry_deprecated: bool = False
    registry_replaced_by: str = ""
    registry_deprecation_message: str = ""

    @property
    def is_installed(self) -> bool:
        return len(self.install_locations) > 0

    @property
    def installed_version(self) -> str:
        return self.skill.version if self.skill else ""

    @property
    def is_up_to_date(self) -> bool | None:
        """None when the registry was not checked; True/False otherwise."""
        if not self.registry_latest or not self.installed_version:
            return None
        from skill_forge.domain.model import _version_key  # internal helper

        return _version_key(self.installed_version) >= _version_key(self.registry_latest)


class GetSkillInfo:
    """Locate an installed skill and surface its metadata.

    Scans all install targets for ``scope``, reads the skill's SKILL.md,
    and optionally hits the registry to compare installed vs available version.
    """

    def __init__(
        self,
        installer: SkillInstaller,
        parser: SkillParser,
        fetcher: PackFetcher | None = None,
    ) -> None:
        self._installer = installer
        self._parser = parser
        self._fetcher = fetcher

    def execute(self, request: InfoRequest) -> InfoResponse:
        all_targets = self._installer.scan_all_targets(request.scope)

        locations: list[InstallLocation] = []
        skill: Skill | None = None

        for target, paths in all_targets.items():
            for p in paths:
                if p.name != request.skill_name:
                    continue

                skill_md = _find_skill_md(p)
                is_broken = skill_md is None or not skill_md.exists()
                locations.append(InstallLocation(target=target, path=p, is_broken=is_broken))

                if not is_broken and skill is None and skill_md is not None:
                    try:
                        content = skill_md.read_text(encoding="utf-8")
                        skill = self._parser.parse(content, base_path=skill_md.parent)
                    except Exception:  # pragma: no cover
                        pass

        # Optional registry comparison
        registry_latest: str | None = None
        registry_deprecated = False
        registry_replaced_by = ""
        registry_deprecation_message = ""
        if request.registry_url and self._fetcher:
            index_url = request.registry_url.rstrip("/") + "/index.json"
            try:
                index = self._fetcher.fetch_index(index_url)
                for indexed in index.skills:
                    if indexed.name == request.skill_name:
                        registry_latest = indexed.latest
                        registry_deprecated = indexed.deprecated
                        registry_replaced_by = indexed.replaced_by
                        registry_deprecation_message = indexed.deprecation_message
                        break
            except Exception:  # network errors are non-fatal for info
                pass

        return InfoResponse(
            skill_name=request.skill_name,
            skill=skill,
            install_locations=locations,
            registry_latest=registry_latest,
            registry_deprecated=registry_deprecated,
            registry_replaced_by=registry_replaced_by,
            registry_deprecation_message=registry_deprecation_message,
        )


# ── helpers ───────────────────────────────────────────────────────────────────


def _find_skill_md(path: Path) -> Path | None:
    """Return the SKILL.md path for a directory or symlink, or None."""
    resolved = path.resolve() if path.is_symlink() else path
    candidate = resolved / "SKILL.md"
    return candidate if candidate.exists() else None
