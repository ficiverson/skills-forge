"""Tests for the pack/unpack use cases."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_forge.application.use_cases.pack_skill import (
    PackSkill,
    PackSkillRequest,
    UnpackSkill,
    UnpackSkillRequest,
)
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker


def _make_skill(base: Path, category: str, name: str) -> Path:
    skill_dir = base / "output_skills" / category / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: |\n  A test skill\n---\n",
        encoding="utf-8",
    )
    return skill_dir


def _build_pack_use_case() -> PackSkill:
    return PackSkill(packer=ZipSkillPacker(), parser=MarkdownSkillParser())


def _build_unpack_use_case() -> UnpackSkill:
    return UnpackSkill(packer=ZipSkillPacker())


class TestPackSkillUseCase:
    def test_packs_single_skill(self, tmp_path: Path):
        skill_dir = _make_skill(tmp_path, "dev", "python-tdd")
        use_case = _build_pack_use_case()

        response = use_case.execute(
            PackSkillRequest(
                skill_dirs=[skill_dir],
                output_path=tmp_path / "out",
                version="0.1.0",
                author="fer",
            )
        )

        assert response.pack_path.exists()
        assert response.pack_path.suffix == ".skillpack"
        assert response.manifest.skill_count == 1
        assert response.manifest.name == "python-tdd"
        assert response.manifest.version == "0.1.0"
        assert response.manifest.author == "fer"
        assert response.manifest.skills[0].category == "dev"
        assert response.manifest.skills[0].name == "python-tdd"

    def test_auto_derives_filename_when_output_is_dir(self, tmp_path: Path):
        skill_dir = _make_skill(tmp_path, "dev", "python-tdd")
        out_dir = tmp_path / "packs"
        out_dir.mkdir()

        response = _build_pack_use_case().execute(
            PackSkillRequest(
                skill_dirs=[skill_dir],
                output_path=out_dir,
                version="1.2.3",
            )
        )

        assert response.pack_path.name == "python-tdd-1.2.3.skillpack"
        assert response.pack_path.parent == out_dir

    def test_explicit_pack_name_overrides_skill_name(self, tmp_path: Path):
        skill_dir = _make_skill(tmp_path, "dev", "python-tdd")

        response = _build_pack_use_case().execute(
            PackSkillRequest(
                skill_dirs=[skill_dir],
                output_path=tmp_path / "out",
                pack_name="my-team-bundle",
            )
        )

        assert response.manifest.name == "my-team-bundle"
        assert "my-team-bundle" in response.pack_path.name

    def test_packs_multiple_skills(self, tmp_path: Path):
        a = _make_skill(tmp_path, "dev", "skill-a")
        b = _make_skill(tmp_path, "ops", "skill-b")

        response = _build_pack_use_case().execute(
            PackSkillRequest(
                skill_dirs=[a, b],
                output_path=tmp_path / "bundle.skillpack",
                pack_name="combo",
            )
        )

        assert response.manifest.skill_count == 2
        categories = {ref.category for ref in response.manifest.skills}
        assert categories == {"dev", "ops"}

    def test_empty_request_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="at least one skill"):
            _build_pack_use_case().execute(
                PackSkillRequest(skill_dirs=[], output_path=tmp_path / "out.skillpack")
            )

    def test_missing_skill_md_raises(self, tmp_path: Path):
        broken = tmp_path / "broken"
        broken.mkdir()
        with pytest.raises(FileNotFoundError, match=r"no SKILL\.md"):
            _build_pack_use_case().execute(
                PackSkillRequest(
                    skill_dirs=[broken],
                    output_path=tmp_path / "out.skillpack",
                )
            )


class TestUnpackSkillUseCase:
    def test_roundtrip_pack_then_unpack(self, tmp_path: Path):
        skill_dir = _make_skill(tmp_path, "dev", "python-tdd")
        pack_response = _build_pack_use_case().execute(
            PackSkillRequest(
                skill_dirs=[skill_dir],
                output_path=tmp_path / "out",
            )
        )

        dest = tmp_path / "extracted"
        unpack_response = _build_unpack_use_case().execute(
            UnpackSkillRequest(pack_path=pack_response.pack_path, dest_dir=dest)
        )

        assert unpack_response.manifest.name == "python-tdd"
        assert len(unpack_response.extracted_paths) == 1
        extracted_skill = unpack_response.extracted_paths[0]
        assert extracted_skill == dest / "dev" / "python-tdd"
        assert (extracted_skill / "SKILL.md").exists()

    def test_roundtrip_multi_skill(self, tmp_path: Path):
        a = _make_skill(tmp_path, "dev", "skill-a")
        b = _make_skill(tmp_path, "ops", "skill-b")
        pack_response = _build_pack_use_case().execute(
            PackSkillRequest(
                skill_dirs=[a, b],
                output_path=tmp_path / "bundle.skillpack",
                pack_name="combo",
            )
        )

        dest = tmp_path / "extracted"
        unpack_response = _build_unpack_use_case().execute(
            UnpackSkillRequest(pack_path=pack_response.pack_path, dest_dir=dest)
        )

        assert unpack_response.manifest.skill_count == 2
        assert (dest / "dev" / "skill-a" / "SKILL.md").exists()
        assert (dest / "ops" / "skill-b" / "SKILL.md").exists()
