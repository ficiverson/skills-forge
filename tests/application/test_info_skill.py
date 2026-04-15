"""Tests for the GetSkillInfo use case (v0.5.0 — NEW-001)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from skill_forge.application.use_cases.info_skill import (
    GetSkillInfo,
    InfoRequest,
)
from skill_forge.domain.model import (
    InstallTarget,
    Skill,
    SkillIdentity,
)
from skill_forge.domain.ports import PackFetcher, SkillInstaller, SkillParser

# ── Stubs ─────────────────────────────────────────────────────────────────────


class _StubInstaller(SkillInstaller):
    """Installer that returns a configurable set of installed skill paths."""

    def __init__(
        self,
        targets: dict[InstallTarget, list[Path]] | None = None,
    ) -> None:
        self._targets: dict[InstallTarget, list[Path]] = targets or {}

    def install(self, skill_path, scope, target=InstallTarget.CLAUDE):
        return []

    def uninstall(self, skill_name, scope, target=InstallTarget.ALL):
        return []

    def is_installed(self, skill_name, scope):
        return any(any(p.name == skill_name for p in paths) for paths in self._targets.values())

    def list_installed(self, scope):
        return []

    def scan_all_targets(self, scope):
        return self._targets


class _StubParser(SkillParser):
    def __init__(self, skill: Skill | None = None) -> None:
        self._skill = skill

    def parse(self, content, base_path=None):
        if self._skill is not None:
            return self._skill
        raise ValueError("No skill configured in stub")


def _make_skill(name: str = "my-skill", version: str = "1.0.0") -> Skill:
    skill = MagicMock(spec=Skill)
    skill.identity = SkillIdentity(name=name, category="testing")
    skill.version = version
    skill.total_estimated_tokens = 200
    skill.has_evals = False
    skill.evals = []
    skill.has_dependencies = False
    skill.depends_on = []
    skill.requires_forge = None
    return skill


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestGetSkillInfoNotInstalled:
    def test_not_installed_returns_empty_locations(self) -> None:
        installer = _StubInstaller()
        use_case = GetSkillInfo(
            installer=installer,
            parser=_StubParser(),
        )
        response = use_case.execute(InfoRequest(skill_name="missing-skill"))
        assert not response.is_installed
        assert response.skill is None
        assert response.install_locations == []

    def test_is_installed_false_when_no_targets(self) -> None:
        use_case = GetSkillInfo(
            installer=_StubInstaller(),
            parser=_StubParser(),
        )
        resp = use_case.execute(InfoRequest(skill_name="x"))
        assert resp.is_installed is False


class TestGetSkillInfoInstalled:
    def test_finds_skill_in_claude_target(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\ncategory: testing\n---\n")
        expected_skill = _make_skill("my-skill", "1.2.3")
        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        parser = _StubParser(skill=expected_skill)
        use_case = GetSkillInfo(installer=installer, parser=parser)

        response = use_case.execute(InfoRequest(skill_name="my-skill"))

        assert response.is_installed
        assert response.skill is expected_skill
        assert response.installed_version == "1.2.3"
        assert len(response.install_locations) == 1
        assert response.install_locations[0].target == InstallTarget.CLAUDE
        assert not response.install_locations[0].is_broken

    def test_multiple_targets(self, tmp_path: Path) -> None:
        claude_dir = tmp_path / "claude" / "my-skill"
        gemini_dir = tmp_path / "gemini" / "my-skill"
        for d in (claude_dir, gemini_dir):
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        skill = _make_skill()
        installer = _StubInstaller(
            targets={
                InstallTarget.CLAUDE: [claude_dir],
                InstallTarget.GEMINI: [gemini_dir],
            }
        )
        use_case = GetSkillInfo(installer=installer, parser=_StubParser(skill=skill))
        response = use_case.execute(InfoRequest(skill_name="my-skill"))

        assert len(response.install_locations) == 2
        targets = {loc.target for loc in response.install_locations}
        assert InstallTarget.CLAUDE in targets
        assert InstallTarget.GEMINI in targets

    def test_broken_symlink_detected(self, tmp_path: Path) -> None:
        link = tmp_path / "my-skill"
        link.symlink_to(tmp_path / "nonexistent")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [link]})
        use_case = GetSkillInfo(installer=installer, parser=_StubParser())
        response = use_case.execute(InfoRequest(skill_name="my-skill"))

        assert response.is_installed
        assert response.install_locations[0].is_broken
        assert response.skill is None  # broken → cannot parse


class TestGetSkillInfoRegistryComparison:
    def test_registry_url_checked_when_provided(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        skill = _make_skill("my-skill", "1.0.0")
        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})

        fetcher = MagicMock(spec=PackFetcher)
        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            RegistryIndex,
        )

        fake_version = IndexedVersion(
            version="2.0.0",
            path="packs/testing/my-skill-2.0.0.skillpack",
            sha256="a" * 64,
        )
        fake_skill = IndexedSkill(
            category="testing",
            name="my-skill",
            latest="2.0.0",
            versions=(fake_version,),
        )
        fake_index = RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="2026-01-01T00:00:00Z",
            skills=(fake_skill,),
        )
        fetcher.fetch_index.return_value = fake_index

        use_case = GetSkillInfo(
            installer=installer,
            parser=_StubParser(skill=skill),
            fetcher=fetcher,
        )
        response = use_case.execute(
            InfoRequest(
                skill_name="my-skill",
                registry_url="https://example.com",
            )
        )

        assert response.registry_latest == "2.0.0"
        assert response.is_up_to_date is False

    def test_up_to_date_when_on_latest(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        skill = _make_skill("my-skill", "2.0.0")
        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            RegistryIndex,
        )

        fake_version = IndexedVersion(
            version="2.0.0",
            path="packs/testing/my-skill-2.0.0.skillpack",
            sha256="b" * 64,
        )
        fake_skill = IndexedSkill(
            category="testing",
            name="my-skill",
            latest="2.0.0",
            versions=(fake_version,),
        )
        fake_index = RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="2026-01-01T00:00:00Z",
            skills=(fake_skill,),
        )
        fetcher.fetch_index.return_value = fake_index

        use_case = GetSkillInfo(
            installer=installer,
            parser=_StubParser(skill=skill),
            fetcher=fetcher,
        )
        response = use_case.execute(
            InfoRequest(
                skill_name="my-skill",
                registry_url="https://example.com",
            )
        )
        assert response.is_up_to_date is True

    def test_is_up_to_date_none_when_no_registry(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")
        skill = _make_skill("my-skill", "1.0.0")
        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        use_case = GetSkillInfo(installer=installer, parser=_StubParser(skill=skill))
        response = use_case.execute(InfoRequest(skill_name="my-skill"))
        assert response.registry_latest is None
        assert response.is_up_to_date is None

    def test_network_error_does_not_raise(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")
        skill = _make_skill("my-skill", "1.0.0")
        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.side_effect = RuntimeError("network error")

        use_case = GetSkillInfo(
            installer=installer,
            parser=_StubParser(skill=skill),
            fetcher=fetcher,
        )
        response = use_case.execute(
            InfoRequest(skill_name="my-skill", registry_url="https://example.com")
        )
        assert response.registry_latest is None
