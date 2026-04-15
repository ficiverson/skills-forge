"""Tests for the DoctorSkill use case (v0.5.0 — BKL-021)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from skill_forge.application.use_cases.doctor_skill import (
    DoctorIssue,
    DoctorResponse,
    DoctorSkill,
)
from skill_forge.domain.model import (
    Dependency,
    IndexedSkill,
    IndexedVersion,
    InstallTarget,
    RegistryIndex,
    Severity,
    Skill,
    SkillIdentity,
    SkillScope,
)
from skill_forge.domain.ports import PackFetcher, SkillInstaller, SkillParser

# ── Stubs ─────────────────────────────────────────────────────────────────────


class _StubInstaller(SkillInstaller):
    def __init__(
        self,
        targets: dict[InstallTarget, list[Path]] | None = None,
        installed_names: list[str] | None = None,
    ) -> None:
        self._targets: dict[InstallTarget, list[Path]] = targets or {}
        self._installed: set[str] = set(installed_names or [])

    def install(self, skill_path, scope, target=InstallTarget.CLAUDE):
        return []

    def uninstall(self, skill_name, scope, target=InstallTarget.ALL):
        return []

    def is_installed(self, skill_name, scope):
        return skill_name in self._installed

    def list_installed(self, scope):
        return []

    def scan_all_targets(self, scope):
        return self._targets


def _stub_skill(name: str = "s", version: str = "1.0.0", deps: list[str] | None = None) -> Skill:
    skill = MagicMock(spec=Skill)
    skill.identity = SkillIdentity(name=name, category="cat")
    skill.version = version
    skill.depends_on = [
        Dependency(skill_name=d, reason="needs it") for d in (deps or [])
    ]
    skill.has_dependencies = bool(deps)
    return skill


class _StubParser(SkillParser):
    def __init__(self, skill: Skill) -> None:
        self._skill = skill

    def parse(self, content, base_path=None):
        return self._skill


class _FailingParser(SkillParser):
    def parse(self, content, base_path=None):
        raise RuntimeError("parse failure")


# ── Tests: basic checks ────────────────────────────────────────────────────────


class TestDoctorHealthy:
    def test_empty_install_returns_zero_checked(self) -> None:
        use_case = DoctorSkill(
            installer=_StubInstaller(),
            parser=_StubParser(_stub_skill()),
        )
        response = use_case.execute(scope=SkillScope.GLOBAL)
        assert response.checked_count == 0
        assert response.is_healthy
        assert response.issues == []

    def test_valid_skill_returns_healthy(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        use_case = DoctorSkill(
            installer=installer,
            parser=_StubParser(_stub_skill("my-skill")),
        )
        response = use_case.execute(scope=SkillScope.GLOBAL)
        assert response.checked_count == 1
        assert response.is_healthy


class TestDoctorBrokenSymlinks:
    def test_broken_symlink_raises_error_issue(self, tmp_path: Path) -> None:
        link = tmp_path / "broken-skill"
        link.symlink_to(tmp_path / "does-not-exist")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [link]})
        use_case = DoctorSkill(
            installer=installer,
            parser=_StubParser(_stub_skill()),
        )
        response = use_case.execute(scope=SkillScope.GLOBAL)

        assert response.failure_count == 1
        broken = [i for i in response.issues if i.kind == "broken-symlink"]
        assert len(broken) == 1
        assert broken[0].severity == Severity.ERROR
        assert broken[0].skill_name == "broken-skill"

    def test_missing_skill_md_raises_error(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "no-md-skill"
        skill_dir.mkdir()  # no SKILL.md inside

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        use_case = DoctorSkill(
            installer=installer,
            parser=_StubParser(_stub_skill()),
        )
        response = use_case.execute(scope=SkillScope.GLOBAL)

        errors = [i for i in response.issues if i.kind == "missing-skill-md"]
        assert len(errors) == 1
        assert errors[0].severity == Severity.ERROR


class TestDoctorMissingDeps:
    def test_missing_dep_produces_warning(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "parent-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: parent-skill\n---\n")

        installer = _StubInstaller(
            targets={InstallTarget.CLAUDE: [skill_dir]},
            installed_names=[],  # dep is NOT installed
        )
        use_case = DoctorSkill(
            installer=installer,
            parser=_StubParser(_stub_skill("parent-skill", deps=["child-skill"])),
        )
        response = use_case.execute(scope=SkillScope.GLOBAL)

        warnings = [i for i in response.issues if i.kind == "missing-dep"]
        assert len(warnings) == 1
        assert warnings[0].severity == Severity.WARNING
        assert "child-skill" in warnings[0].message

    def test_satisfied_dep_produces_no_warning(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "parent-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: parent-skill\n---\n")

        installer = _StubInstaller(
            targets={InstallTarget.CLAUDE: [skill_dir]},
            installed_names=["child-skill"],
        )
        use_case = DoctorSkill(
            installer=installer,
            parser=_StubParser(_stub_skill("parent-skill", deps=["child-skill"])),
        )
        response = use_case.execute(scope=SkillScope.GLOBAL)

        dep_warnings = [i for i in response.issues if i.kind == "missing-dep"]
        assert len(dep_warnings) == 0


class TestDoctorParseError:
    def test_parse_error_produces_warning(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("bad content")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        use_case = DoctorSkill(
            installer=installer,
            parser=_FailingParser(),
        )
        response = use_case.execute(scope=SkillScope.GLOBAL)

        errors = [i for i in response.issues if i.kind == "parse-error"]
        assert len(errors) == 1
        assert errors[0].severity == Severity.WARNING


class TestDoctorStaleVersions:
    def _make_registry_index(
        self, skill_name: str, latest: str
    ) -> RegistryIndex:
        iv = IndexedVersion(
            version=latest,
            path=f"packs/cat/{skill_name}-{latest}.skillpack",
            sha256="c" * 64,
        )
        is_ = IndexedSkill(
            category="cat",
            name=skill_name,
            latest=latest,
            versions=(iv,),
        )
        return RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="2026-01-01T00:00:00Z",
            skills=(is_,),
        )

    def test_stale_version_produces_warning(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = self._make_registry_index("my-skill", "2.0.0")

        use_case = DoctorSkill(
            installer=installer,
            parser=_StubParser(_stub_skill("my-skill", version="1.0.0")),
            fetcher=fetcher,
        )
        response = use_case.execute(
            scope=SkillScope.GLOBAL,
            registry_url="https://example.com",
        )

        stale = [i for i in response.issues if i.kind == "stale-version"]
        assert len(stale) == 1
        assert stale[0].severity == Severity.WARNING
        assert "2.0.0" in stale[0].message

    def test_current_version_no_stale_warning(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = self._make_registry_index("my-skill", "1.0.0")

        use_case = DoctorSkill(
            installer=installer,
            parser=_StubParser(_stub_skill("my-skill", version="1.0.0")),
            fetcher=fetcher,
        )
        response = use_case.execute(
            scope=SkillScope.GLOBAL,
            registry_url="https://example.com",
        )

        stale = [i for i in response.issues if i.kind == "stale-version"]
        assert len(stale) == 0


class TestDoctorResponseProperties:
    def test_is_healthy_only_with_info_issues(self) -> None:
        from skill_forge.domain.model import Severity

        resp = DoctorResponse(
            issues=[
                DoctorIssue(
                    skill_name="x",
                    kind="stale-version",
                    message="ok",
                    severity=Severity.INFO,
                )
            ],
            checked_count=1,
        )
        assert resp.is_healthy

    def test_failure_count_counts_errors_only(self) -> None:
        resp = DoctorResponse(
            issues=[
                DoctorIssue("a", "broken-symlink", "msg", Severity.ERROR),
                DoctorIssue("b", "missing-dep", "msg", Severity.WARNING),
            ],
            checked_count=2,
        )
        assert resp.failure_count == 1
        assert resp.warning_count == 1
