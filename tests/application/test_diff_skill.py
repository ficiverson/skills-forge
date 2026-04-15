"""Tests for the DiffSkill use case."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from skill_forge.application.use_cases.diff_skill import (
    DiffRequest,
    DiffResponse,
    DiffSkill,
)
from skill_forge.domain.model import InstallTarget, RegistryIndex, SkillScope
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

# ── helpers ───────────────────────────────────────────────────────────────────

_SKILL_MD_V1 = """\
---
name: python-tdd
version: 1.0.0
description: |
  TDD workflow for Python.
---
## Instructions

Write tests first.
"""

_SKILL_MD_V2 = """\
---
name: python-tdd
version: 1.1.0
description: |
  TDD workflow for Python.
---
## Instructions

Write tests first, then implementation.
"""


def _make_skillpack(tmp_path: Path, skill_md_content: str, skill_name: str = "python-tdd") -> Path:
    """Build a minimal .skillpack zip containing a SKILL.md."""
    pack_path = tmp_path / f"{skill_name}.skillpack"
    with zipfile.ZipFile(pack_path, "w") as zf:
        zf.writestr(f"{skill_name}/SKILL.md", skill_md_content)
    return pack_path


class _StubInstaller:
    """Fake installer: exposes a single installed skill directory."""

    def __init__(self, installed_path: Path | None, skill_name: str = "python-tdd") -> None:
        self._path = installed_path
        self._name = skill_name

    def scan_all_targets(self, scope: SkillScope) -> dict[InstallTarget, list[Path]]:
        if self._path is not None:
            return {InstallTarget.CLAUDE: [self._path]}
        return {InstallTarget.CLAUDE: []}

    # Satisfy the rest of SkillInstaller protocol (unused in these tests)
    def is_installed(self, skill_name: str, scope: SkillScope) -> bool:  # pragma: no cover
        return False

    def install(self, *args, **kwargs) -> None:  # pragma: no cover
        pass

    def uninstall(self, *args, **kwargs) -> None:  # pragma: no cover
        pass

    def list_installed(self, *args, **kwargs) -> list:  # pragma: no cover
        return []


class _StubFetcher:
    """Fake fetcher: returns a pre-built RegistryIndex and copies a pack file."""

    def __init__(
        self,
        index: RegistryIndex,
        pack_path: Path | None = None,
    ) -> None:
        self._index = index
        self._pack_path = pack_path

    def fetch_index(self, url: str) -> RegistryIndex:
        return self._index

    def fetch(self, url: str, dest: Path) -> None:
        if self._pack_path is None:
            raise RuntimeError("No pack configured in stub")
        import shutil
        shutil.copy2(self._pack_path, dest)


def _make_registry(
    skill_name: str = "python-tdd",
    latest: str = "1.1.0",
    pack_path_str: str = "packs/python-tdd-1.1.0.skillpack",
) -> RegistryIndex:
    from skill_forge.domain.model import IndexedSkill, IndexedVersion

    return RegistryIndex(
        registry_name="test-registry",
        base_url="https://reg.example.com",
        updated_at="2026-04-11T00:00:00Z",
        skills=(
            IndexedSkill(
                category="dev",
                name=skill_name,
                latest=latest,
                versions=(
                    IndexedVersion(
                        version=latest,
                        path=pack_path_str,
                        sha256="a" * 64,
                    ),
                ),
            ),
        ),
    )


# ── tests ─────────────────────────────────────────────────────────────────────


class TestDiffSkillMissingRegistryUrl:
    def test_raises_when_no_registry_url(self, tmp_path: Path) -> None:
        installer = _StubInstaller(tmp_path)
        (tmp_path / "SKILL.md").write_text(_SKILL_MD_V1, encoding="utf-8")
        use_case = DiffSkill(
            installer=installer,
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(_make_registry()),
        )
        with pytest.raises(ValueError, match="registry_url"):
            use_case.execute(DiffRequest(skill_name="python-tdd", registry_url=""))


class TestDiffSkillNotInstalled:
    def test_raises_when_skill_not_found(self, tmp_path: Path) -> None:
        installer = _StubInstaller(installed_path=None)
        use_case = DiffSkill(
            installer=installer,
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(_make_registry()),
        )
        with pytest.raises(ValueError, match="not installed"):
            use_case.execute(
                DiffRequest(skill_name="python-tdd", registry_url="https://reg.example.com")
            )


class TestDiffSkillUpToDate:
    def test_no_diff_when_identical(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "python-tdd"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(_SKILL_MD_V1, encoding="utf-8")

        pack_path = _make_skillpack(tmp_path, _SKILL_MD_V1)
        registry = _make_registry(latest="1.0.0")

        use_case = DiffSkill(
            installer=_StubInstaller(skill_dir),
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(registry, pack_path=pack_path),
        )
        response = use_case.execute(
            DiffRequest(skill_name="python-tdd", registry_url="https://reg.example.com")
        )

        assert not response.has_diff
        assert response.installed_version == "1.0.0"
        assert response.registry_version == "1.0.0"
        assert response.is_up_to_date


class TestDiffSkillHasDiff:
    def test_diff_lines_populated_when_versions_differ(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "python-tdd"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(_SKILL_MD_V1, encoding="utf-8")

        pack_path = _make_skillpack(tmp_path, _SKILL_MD_V2)
        registry = _make_registry(latest="1.1.0")

        use_case = DiffSkill(
            installer=_StubInstaller(skill_dir),
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(registry, pack_path=pack_path),
        )
        response = use_case.execute(
            DiffRequest(skill_name="python-tdd", registry_url="https://reg.example.com")
        )

        assert response.has_diff
        assert response.installed_version == "1.0.0"
        assert response.registry_version == "1.1.0"
        assert not response.is_up_to_date
        # diff lines should be a unified diff
        combined = "".join(response.diff_lines)
        assert "1.0.0" in combined
        assert "1.1.0" in combined
        assert "---" in combined or "+++" in combined


class TestDiffSkillNotInRegistry:
    def test_empty_registry_version_when_skill_absent(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "python-tdd"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(_SKILL_MD_V1, encoding="utf-8")

        # Registry has a *different* skill
        other_registry = _make_registry(skill_name="other-skill", latest="1.0.0")

        use_case = DiffSkill(
            installer=_StubInstaller(skill_dir),
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(other_registry),
        )
        response = use_case.execute(
            DiffRequest(skill_name="python-tdd", registry_url="https://reg.example.com")
        )

        assert response.registry_version == ""
        assert not response.has_diff


class TestDiffSkillMissingSkillMd:
    def test_raises_when_skill_md_absent(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "python-tdd"
        skill_dir.mkdir()
        # No SKILL.md created

        use_case = DiffSkill(
            installer=_StubInstaller(skill_dir),
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(_make_registry()),
        )
        with pytest.raises(ValueError, match=r"SKILL\.md not found"):
            use_case.execute(
                DiffRequest(skill_name="python-tdd", registry_url="https://reg.example.com")
            )


class TestDiffResponseProperties:
    def test_is_up_to_date_true_when_same_version(self) -> None:
        r = DiffResponse(
            skill_name="x", installed_version="1.2.0", registry_version="1.2.0"
        )
        assert r.is_up_to_date

    def test_is_up_to_date_true_when_ahead(self) -> None:
        r = DiffResponse(
            skill_name="x", installed_version="1.3.0", registry_version="1.2.0"
        )
        assert r.is_up_to_date

    def test_is_up_to_date_false_when_behind(self) -> None:
        r = DiffResponse(
            skill_name="x", installed_version="1.0.0", registry_version="1.1.0"
        )
        assert not r.is_up_to_date

    def test_is_up_to_date_true_when_no_registry_version(self) -> None:
        r = DiffResponse(skill_name="x", installed_version="1.0.0", registry_version="")
        assert r.is_up_to_date

    def test_has_diff_false_when_empty(self) -> None:
        r = DiffResponse(skill_name="x", installed_version="1.0.0", registry_version="1.1.0")
        assert not r.has_diff

    def test_has_diff_true_when_lines_present(self) -> None:
        r = DiffResponse(
            skill_name="x",
            installed_version="1.0.0",
            registry_version="1.1.0",
            diff_lines=["--- a\n", "+++ b\n"],
        )
        assert r.has_diff
