"""Use case: health-check all installed skills.

``DoctorSkill`` scans every install-target directory, detects broken
symlinks, missing dependencies, and stale versions against the registry.
It exits non-zero (via the CLI) when any ERROR-severity issue is found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from skill_forge.domain.model import Severity, Skill, SkillScope, _version_key
from skill_forge.domain.ports import PackFetcher, SkillInstaller, SkillParser


@dataclass(frozen=True)
class DoctorIssue:
    """A single problem found by the doctor sweep."""

    skill_name: str
    kind: str  # "broken-symlink" | "missing-skill-md" | "missing-dep" | "stale-version"
    message: str
    severity: Severity

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        return f"{prefix} {self.skill_name}: {self.message}"


@dataclass
class DoctorResponse:
    """Aggregated result of the health sweep."""

    issues: list[DoctorIssue] = field(default_factory=list)
    checked_count: int = 0  # total distinct skill names examined

    @property
    def is_healthy(self) -> bool:
        """True when no ERROR or WARNING issues were found."""
        return all(i.severity == Severity.INFO for i in self.issues)

    @property
    def failure_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)


class DoctorSkill:
    """Sweep all installed skills and report health issues.

    Checks performed (in order):
    1. Broken symlinks (ERROR) — link exists but target directory is gone.
    2. Missing SKILL.md (ERROR) — directory present but no SKILL.md inside.
    3. Missing dependencies (WARNING) — ``depends_on`` entry not installed.
    4. Stale versions (WARNING) — registry has a newer version than installed.
       (only when ``registry_url`` is provided and network is reachable)
    5. Yanked versions (WARNING) — installed version has been yanked in registry.
       (only when ``registry_url`` is provided and network is reachable)
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

    def execute(
        self,
        scope: SkillScope,
        registry_url: str = "",
    ) -> DoctorResponse:
        issues: list[DoctorIssue] = []
        checked: set[str] = set()
        skill_versions: dict[str, str] = {}

        all_targets = self._installer.scan_all_targets(scope)

        for _target, paths in all_targets.items():
            for p in paths:
                name = p.name
                checked.add(name)

                # 1. Broken symlink
                if p.is_symlink() and not p.exists():
                    issues.append(
                        DoctorIssue(
                            skill_name=name,
                            kind="broken-symlink",
                            message=f"Symlink {p} → missing target",
                            severity=Severity.ERROR,
                        )
                    )
                    continue

                # 2. SKILL.md missing
                skill_md = _find_skill_md(p)
                if skill_md is None:
                    issues.append(
                        DoctorIssue(
                            skill_name=name,
                            kind="missing-skill-md",
                            message=f"SKILL.md not found in {p.resolve()}",
                            severity=Severity.ERROR,
                        )
                    )
                    continue

                # 3. Dependencies
                try:
                    content = skill_md.read_text(encoding="utf-8")
                    skill: Skill = self._parser.parse(content, base_path=skill_md.parent)
                    skill_versions[name] = skill.version

                    for dep in skill.depends_on:
                        if not self._installer.is_installed(dep.skill_name, scope):
                            issues.append(
                                DoctorIssue(
                                    skill_name=name,
                                    kind="missing-dep",
                                    message=(
                                        f"Dependency '{dep.skill_name}' is not installed"
                                    ),
                                    severity=Severity.WARNING,
                                )
                            )
                except Exception as exc:
                    issues.append(
                        DoctorIssue(
                            skill_name=name,
                            kind="parse-error",
                            message=f"Could not parse SKILL.md: {exc}",
                            severity=Severity.WARNING,
                        )
                    )

        # 4 + 5. Stale + yanked versions (network; non-fatal if unavailable)
        if registry_url and self._fetcher and skill_versions:
            index_url = registry_url.rstrip("/") + "/index.json"
            try:
                index = self._fetcher.fetch_index(index_url)
                for indexed in index.skills:
                    installed_v = skill_versions.get(indexed.name)
                    if installed_v is None:
                        continue
                    # 4. Stale version
                    if _version_key(installed_v) < _version_key(indexed.latest):
                        issues.append(
                            DoctorIssue(
                                skill_name=indexed.name,
                                kind="stale-version",
                                message=(
                                    f"Installed v{installed_v}, "
                                    f"registry has v{indexed.latest}"
                                ),
                                severity=Severity.WARNING,
                            )
                        )
                    # 5. Yanked version
                    installed_entry = indexed.find(installed_v)
                    if installed_entry is not None and installed_entry.yanked:
                        reason = (
                            f" — {installed_entry.yank_reason}"
                            if installed_entry.yank_reason
                            else ""
                        )
                        issues.append(
                            DoctorIssue(
                                skill_name=indexed.name,
                                kind="yanked-version",
                                message=(
                                    f"Installed v{installed_v} has been yanked"
                                    f"{reason} (run: skills-forge update "
                                    f"{indexed.name})"
                                ),
                                severity=Severity.WARNING,
                            )
                        )
            except Exception:  # pragma: no cover — network errors are non-fatal
                pass

        return DoctorResponse(issues=issues, checked_count=len(checked))


# ── helpers ───────────────────────────────────────────────────────────────────


def _find_skill_md(path: Path) -> Path | None:
    """Return the SKILL.md path for a directory or symlink, or None."""
    resolved = path.resolve() if path.is_symlink() else path
    candidate = resolved / "SKILL.md"
    return candidate if candidate.exists() else None


# Re-export for tests
__all__ = ["DoctorIssue", "DoctorResponse", "DoctorSkill"]
