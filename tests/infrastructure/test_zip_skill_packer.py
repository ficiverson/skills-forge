"""Tests for the ZipSkillPacker adapter."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from skill_forge.domain.model import SkillPackManifest, SkillRef
from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker


def _make_skill_dir(base: Path, category: str, name: str) -> Path:
    skill_dir = base / category / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n---\n\n## Principles\n\n- Be good\n",
        encoding="utf-8",
    )
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "guide.md").write_text("# Guide", encoding="utf-8")
    return skill_dir


def _make_manifest(refs: tuple[SkillRef, ...]) -> SkillPackManifest:
    return SkillPackManifest(
        name="test-pack",
        version="0.1.0",
        author="tester",
        created_at="2026-04-06T00:00:00+00:00",
        description="A test pack",
        skills=refs,
    )


class TestPack:
    def test_pack_creates_zip_with_manifest(self, tmp_path: Path):
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "test-skill")
        manifest = _make_manifest((SkillRef(category="dev", name="test-skill"),))
        output = tmp_path / "out.skillpack"

        packer = ZipSkillPacker()
        result = packer.pack([skill_dir], manifest, output)

        assert result == output
        assert output.exists()
        with zipfile.ZipFile(output, "r") as zf:
            assert "manifest.json" in zf.namelist()
            data = json.loads(zf.read("manifest.json").decode())
            assert data["name"] == "test-pack"
            assert data["format_version"] == "1"
            assert data["skills"] == [
                {"category": "dev", "name": "test-skill", "version": "0.1.0"}
            ]

    def test_pack_includes_skill_files(self, tmp_path: Path):
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "test-skill")
        manifest = _make_manifest((SkillRef(category="dev", name="test-skill"),))
        output = tmp_path / "out.skillpack"

        ZipSkillPacker().pack([skill_dir], manifest, output)

        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
        assert "skills/dev/test-skill/SKILL.md" in names
        assert "skills/dev/test-skill/references/guide.md" in names

    def test_pack_excludes_dot_files_and_pycache(self, tmp_path: Path):
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "test-skill")
        (skill_dir / "__pycache__").mkdir()
        (skill_dir / "__pycache__" / "junk.pyc").write_bytes(b"junk")
        (skill_dir / ".DS_Store").write_bytes(b"junk")
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "real.py").write_text("# real")
        (skill_dir / "scripts" / "compiled.pyc").write_bytes(b"junk")

        manifest = _make_manifest((SkillRef(category="dev", name="test-skill"),))
        output = tmp_path / "out.skillpack"
        ZipSkillPacker().pack([skill_dir], manifest, output)

        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
        assert not any("__pycache__" in n for n in names)
        assert not any(".DS_Store" in n for n in names)
        assert not any(n.endswith(".pyc") for n in names)
        assert "skills/dev/test-skill/scripts/real.py" in names

    def test_pack_multiple_skills(self, tmp_path: Path):
        a = _make_skill_dir(tmp_path / "src", "dev", "skill-a")
        b = _make_skill_dir(tmp_path / "src", "ops", "skill-b")
        manifest = SkillPackManifest(
            name="bundle",
            version="0.2.0",
            author="",
            created_at="2026-04-06",
            skills=(
                SkillRef(category="dev", name="skill-a"),
                SkillRef(category="ops", name="skill-b"),
            ),
        )
        output = tmp_path / "bundle.skillpack"
        ZipSkillPacker().pack([a, b], manifest, output)

        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
        assert "skills/dev/skill-a/SKILL.md" in names
        assert "skills/ops/skill-b/SKILL.md" in names

    def test_pack_zero_skills_raises(self, tmp_path: Path):
        manifest = _make_manifest((SkillRef(category="dev", name="x"),))
        with pytest.raises(ValueError, match="zero skills"):
            ZipSkillPacker().pack([], manifest, tmp_path / "out.skillpack")

    def test_pack_count_mismatch_raises(self, tmp_path: Path):
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "a")
        manifest = SkillPackManifest(
            name="x",
            version="1",
            author="",
            created_at="",
            skills=(
                SkillRef(category="dev", name="a"),
                SkillRef(category="dev", name="b"),
            ),
        )
        with pytest.raises(ValueError, match="references 2 skills but 1"):
            ZipSkillPacker().pack([skill_dir], manifest, tmp_path / "out.skillpack")

    def test_pack_missing_skill_md_raises(self, tmp_path: Path):
        skill_dir = tmp_path / "broken"
        skill_dir.mkdir()
        manifest = _make_manifest((SkillRef(category="dev", name="broken"),))
        with pytest.raises(FileNotFoundError, match=r"no SKILL\.md"):
            ZipSkillPacker().pack([skill_dir], manifest, tmp_path / "out.skillpack")


class TestUnpack:
    def test_unpack_extracts_files(self, tmp_path: Path):
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "test-skill")
        manifest = _make_manifest((SkillRef(category="dev", name="test-skill"),))
        output = tmp_path / "pack.skillpack"
        packer = ZipSkillPacker()
        packer.pack([skill_dir], manifest, output)

        dest = tmp_path / "extracted"
        result_manifest = packer.unpack(output, dest)

        assert (dest / "dev" / "test-skill" / "SKILL.md").exists()
        assert (dest / "dev" / "test-skill" / "references" / "guide.md").exists()
        assert result_manifest.name == "test-pack"
        assert result_manifest.skill_count == 1

    def test_unpack_roundtrip_preserves_content(self, tmp_path: Path):
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "test-skill")
        original = (skill_dir / "SKILL.md").read_text()
        manifest = _make_manifest((SkillRef(category="dev", name="test-skill"),))
        output = tmp_path / "pack.skillpack"
        packer = ZipSkillPacker()
        packer.pack([skill_dir], manifest, output)

        dest = tmp_path / "extracted"
        packer.unpack(output, dest)
        roundtripped = (dest / "dev" / "test-skill" / "SKILL.md").read_text()
        assert roundtripped == original

    def test_unpack_missing_pack_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            ZipSkillPacker().unpack(tmp_path / "missing.skillpack", tmp_path)

    def test_unpack_missing_manifest_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.skillpack"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("skills/dev/x/SKILL.md", "---\nname: x\n---")
        with pytest.raises(ValueError, match="missing manifest"):
            ZipSkillPacker().unpack(bad, tmp_path / "out")

    def test_unpack_wrong_format_version_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.skillpack"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format_version": "999",
                        "name": "x",
                        "version": "1",
                        "author": "",
                        "created_at": "",
                        "skills": [{"category": "dev", "name": "x"}],
                    }
                ),
            )
        with pytest.raises(ValueError, match="Unsupported pack format"):
            ZipSkillPacker().unpack(bad, tmp_path / "out")

    def test_unpack_rejects_zip_slip(self, tmp_path: Path):
        """Defends against archives with ../ paths trying to escape dest."""
        bad = tmp_path / "evil.skillpack"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format_version": "1",
                        "name": "evil",
                        "version": "1",
                        "author": "",
                        "created_at": "",
                        "skills": [{"category": "dev", "name": "x"}],
                    }
                ),
            )
            zf.writestr("skills/../../escaped.txt", "pwned")

        with pytest.raises(ValueError, match="outside destination"):
            ZipSkillPacker().unpack(bad, tmp_path / "dest")


class TestReadManifest:
    def test_read_manifest_without_extracting(self, tmp_path: Path):
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "test-skill")
        manifest = _make_manifest((SkillRef(category="dev", name="test-skill"),))
        output = tmp_path / "pack.skillpack"
        packer = ZipSkillPacker()
        packer.pack([skill_dir], manifest, output)

        read = packer.read_manifest(output)
        assert read.name == "test-pack"
        assert read.version == "0.1.0"
        assert read.author == "tester"
        assert read.skills == (SkillRef(category="dev", name="test-skill"),)

    def test_read_manifest_missing_pack_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            ZipSkillPacker().read_manifest(tmp_path / "nope.skillpack")
