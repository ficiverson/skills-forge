"""Tests for the UpdateSkill use case (v0.5.0 — BKL-019)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from skill_forge.application.use_cases.publish_skill import InstallFromUrl
from skill_forge.application.use_cases.update_skill import (
    UpdateRecord,
    UpdateRequest,
    UpdateResponse,
    UpdateSkill,
)
from skill_forge.domain.model import (
    IndexedSkill,
    IndexedVersion,
    InstallTarget,
    RegistryIndex,
    Skill,
    SkillIdentity,
)
from skill_forge.domain.ports import PackFetcher, SkillInstaller, SkillParser

# ── Stubs ─────────────────────────────────────────────────────────────────────


class _StubInstaller(SkillInstaller):
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
        return False

    def list_installed(self, scope):
        return []

    def scan_all_targets(self, scope):
        return self._targets


class _StubParser(SkillParser):
    def __init__(self, version: str = "1.0.0") -> None:
        self._version = version

    def parse(self, content, base_path=None):
        skill = MagicMock(spec=Skill)
        skill.identity = SkillIdentity(name="my-skill", category="cat")
        skill.version = self._version
        return skill


def _make_registry(
    skill_name: str,
    latest: str,
    base_url: str = "https://reg.example.com",
) -> RegistryIndex:
    iv = IndexedVersion(
        version=latest,
        path=f"packs/cat/{skill_name}-{latest}.skillpack",
        sha256="d" * 64,
    )
    is_ = IndexedSkill(
        category="cat",
        name=skill_name,
        latest=latest,
        versions=(iv,),
    )
    return RegistryIndex(
        registry_name="test",
        base_url=base_url,
        updated_at="2026-01-01T00:00:00Z",
        skills=(is_,),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestUpdateSkillNoRegistryUrl:
    def test_raises_without_registry_url(self, tmp_path: Path) -> None:
        use_case = UpdateSkill(
            installer=_StubInstaller(),
            parser=_StubParser(),
            fetcher=MagicMock(spec=PackFetcher),
            install_from_url=MagicMock(spec=InstallFromUrl),
        )
        with pytest.raises(ValueError, match="registry_url is required"):
            use_case.execute(UpdateRequest(registry_url=""))


class TestUpdateSkillDryRun:
    def test_dry_run_finds_available_update(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\nversion: 1.0.0\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = _make_registry("my-skill", "2.0.0")

        install_from_url = MagicMock(spec=InstallFromUrl)
        use_case = UpdateSkill(
            installer=installer,
            parser=_StubParser(version="1.0.0"),
            fetcher=fetcher,
            install_from_url=install_from_url,
        )
        response = use_case.execute(
            UpdateRequest(
                registry_url="https://reg.example.com",
                dry_run=True,
            )
        )

        assert response.available_count == 1
        assert response.updated_count == 0  # dry-run: nothing installed
        install_from_url.execute.assert_not_called()

    def test_dry_run_no_updates_when_current(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = _make_registry("my-skill", "1.0.0")

        use_case = UpdateSkill(
            installer=installer,
            parser=_StubParser(version="1.0.0"),
            fetcher=fetcher,
            install_from_url=MagicMock(spec=InstallFromUrl),
        )
        response = use_case.execute(
            UpdateRequest(
                registry_url="https://reg.example.com",
                dry_run=True,
            )
        )
        assert response.available_count == 0
        assert response.updated_count == 0


class TestUpdateSkillInstall:
    def test_update_installs_newer_version(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = _make_registry("my-skill", "2.0.0")

        install_from_url = MagicMock(spec=InstallFromUrl)
        use_case = UpdateSkill(
            installer=installer,
            parser=_StubParser(version="1.0.0"),
            fetcher=fetcher,
            install_from_url=install_from_url,
        )
        response = use_case.execute(
            UpdateRequest(
                registry_url="https://reg.example.com",
                dry_run=False,
            )
        )

        assert response.updated_count == 1
        install_from_url.execute.assert_called_once()

    def test_skill_not_found_in_registry_is_skipped(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "unknown-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: unknown-skill\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})
        fetcher = MagicMock(spec=PackFetcher)
        # Registry has a different skill
        fetcher.fetch_index.return_value = _make_registry("other-skill", "1.0.0")

        use_case = UpdateSkill(
            installer=installer,
            parser=_StubParser(version="1.0.0"),
            fetcher=fetcher,
            install_from_url=MagicMock(spec=InstallFromUrl),
        )
        response = use_case.execute(UpdateRequest(registry_url="https://reg.example.com"))
        assert response.records == []

    def test_specific_skill_name_filter(self, tmp_path: Path) -> None:
        skill_a = tmp_path / "skill-a"
        skill_b = tmp_path / "skill-b"
        skill_a.mkdir()
        skill_b.mkdir()
        (skill_a / "SKILL.md").write_text("---\nname: skill-a\n---\n")
        (skill_b / "SKILL.md").write_text("---\nname: skill-b\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_a, skill_b]})

        iv_a = IndexedVersion(
            version="2.0.0",
            path="packs/cat/skill-a-2.0.0.skillpack",
            sha256="e" * 64,
        )
        iv_b = IndexedVersion(
            version="2.0.0",
            path="packs/cat/skill-b-2.0.0.skillpack",
            sha256="f" * 64,
        )
        registry = RegistryIndex(
            registry_name="test",
            base_url="https://reg.example.com",
            updated_at="2026-01-01T00:00:00Z",
            skills=(
                IndexedSkill(
                    category="cat",
                    name="skill-a",
                    latest="2.0.0",
                    versions=(iv_a,),
                ),
                IndexedSkill(
                    category="cat",
                    name="skill-b",
                    latest="2.0.0",
                    versions=(iv_b,),
                ),
            ),
        )
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = registry

        install_from_url = MagicMock(spec=InstallFromUrl)

        def _parse(content: str, base_path: object = None) -> Skill:
            skill = MagicMock(spec=Skill)
            skill.version = "1.0.0"
            return skill

        parser = MagicMock(spec=SkillParser)
        parser.parse.side_effect = _parse

        use_case = UpdateSkill(
            installer=installer,
            parser=parser,
            fetcher=fetcher,
            install_from_url=install_from_url,
        )
        response = use_case.execute(
            UpdateRequest(
                registry_url="https://reg.example.com",
                skill_name="skill-a",  # only update skill-a
            )
        )

        # Only skill-a should be updated
        assert len(response.records) == 1
        assert response.records[0].skill_name == "skill-a"
        assert response.updated_count == 1

    def test_unknown_specific_skill_raises(self, tmp_path: Path) -> None:
        installer = _StubInstaller(targets={})
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = _make_registry("my-skill", "1.0.0")

        use_case = UpdateSkill(
            installer=installer,
            parser=_StubParser(),
            fetcher=fetcher,
            install_from_url=MagicMock(spec=InstallFromUrl),
        )
        with pytest.raises(ValueError, match="not installed"):
            use_case.execute(
                UpdateRequest(
                    registry_url="https://reg.example.com",
                    skill_name="ghost-skill",
                )
            )


class TestUpdateSkillPinVersion:
    def test_pin_version_targets_specific_version(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        installer = _StubInstaller(targets={InstallTarget.CLAUDE: [skill_dir]})

        iv_v1 = IndexedVersion(
            version="1.5.0",
            path="packs/cat/my-skill-1.5.0.skillpack",
            sha256="g" * 64,
        )
        iv_v2 = IndexedVersion(
            version="2.0.0",
            path="packs/cat/my-skill-2.0.0.skillpack",
            sha256="h" * 64,
        )
        registry = RegistryIndex(
            registry_name="test",
            base_url="https://reg.example.com",
            updated_at="2026-01-01T00:00:00Z",
            skills=(
                IndexedSkill(
                    category="cat",
                    name="my-skill",
                    latest="2.0.0",
                    versions=(iv_v1, iv_v2),
                ),
            ),
        )
        fetcher = MagicMock(spec=PackFetcher)
        fetcher.fetch_index.return_value = registry

        install_from_url = MagicMock(spec=InstallFromUrl)
        use_case = UpdateSkill(
            installer=installer,
            parser=_StubParser(version="1.0.0"),
            fetcher=fetcher,
            install_from_url=install_from_url,
        )
        response = use_case.execute(
            UpdateRequest(
                registry_url="https://reg.example.com",
                pin_version="1.5.0",
            )
        )

        assert response.records[0].new_version == "1.5.0"
        assert response.updated_count == 1


class TestUpdateResponseProperties:
    def test_available_count_and_updated_count(self) -> None:
        records = [
            UpdateRecord("a", "1.0.0", "2.0.0", "", "x" * 64, True, True),
            UpdateRecord("b", "1.0.0", "1.0.0", "", "y" * 64, False, False),
            UpdateRecord("c", "1.0.0", "2.0.0", "", "z" * 64, True, False),
        ]
        resp = UpdateResponse(records=records)
        assert resp.available_count == 2  # a and c would update
        assert resp.updated_count == 1  # only a was actually installed
