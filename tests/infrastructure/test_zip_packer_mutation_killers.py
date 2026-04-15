"""Mutation-killing tests for ZipSkillPacker.

Focused on asserting all manifest fields after round-tripping, which is the
main cause of surviving mutants in _serialize_manifest and _read_manifest_from_zip.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from skill_forge.domain.model import Owner, SkillPackManifest, SkillRef
from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker


def _make_skill_dir(base: Path, category: str, name: str) -> Path:
    skill_dir = base / category / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\n---\n\n## Principles\n\n- Be good\n",
        encoding="utf-8",
    )
    return skill_dir


def _pack_one(tmp_path: Path, **manifest_kwargs: object) -> tuple[ZipSkillPacker, Path]:
    skill_dir = _make_skill_dir(tmp_path / "src", "dev", "my-skill")
    manifest = SkillPackManifest(
        name=manifest_kwargs.get("name", "my-pack"),  # type: ignore[arg-type]
        version=manifest_kwargs.get("version", "1.2.3"),  # type: ignore[arg-type]
        author=manifest_kwargs.get("author", "tester"),  # type: ignore[arg-type]
        created_at=manifest_kwargs.get("created_at", "2026-01-15T10:00:00+00:00"),  # type: ignore[arg-type]
        description=manifest_kwargs.get("description", "Test pack description"),  # type: ignore[arg-type]
        skills=(SkillRef(category="dev", name="my-skill"),),
        tags=manifest_kwargs.get("tags", ()),  # type: ignore[arg-type]
        platforms=manifest_kwargs.get("platforms", ()),  # type: ignore[arg-type]
        export_formats=manifest_kwargs.get("export_formats", ()),  # type: ignore[arg-type]
        owner=manifest_kwargs.get("owner"),  # type: ignore[arg-type]
        deprecated=manifest_kwargs.get("deprecated", False),  # type: ignore[arg-type]
    )
    out = tmp_path / "out.skillpack"
    packer = ZipSkillPacker()
    packer.pack([skill_dir], manifest, out)
    return packer, out


class TestSerializeManifestAllFields:
    """All manifest JSON keys must be written with exact names."""

    def test_name_is_serialized(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, name="specific-name")
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["name"] == "specific-name"

    def test_version_is_serialized(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, version="3.1.4")
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["version"] == "3.1.4"

    def test_author_is_serialized(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, author="alice@example.com")
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["author"] == "alice@example.com"

    def test_created_at_key_name_is_exact(self, tmp_path: Path) -> None:
        """Mutation: 'XXcreated_atXX' key must be killed by checking key presence."""
        _, out = _pack_one(tmp_path, created_at="2026-03-20T08:00:00+00:00")
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert "created_at" in data
        assert "XXcreated_atXX" not in data
        assert data["created_at"] == "2026-03-20T08:00:00+00:00"

    def test_description_is_serialized(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, description="A very specific description")
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["description"] == "A very specific description"

    def test_format_version_is_1(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path)
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["format_version"] == "1"

    def test_skills_list_contains_category_name_version(self, tmp_path: Path) -> None:
        """The skills array must include each SkillRef's version field."""
        skill_dir = _make_skill_dir(tmp_path / "src", "dev", "my-skill")
        ref = SkillRef(category="dev", name="my-skill", version="2.0.0")
        manifest = SkillPackManifest(
            name="test",
            version="2.0.0",
            author="",
            created_at="",
            description="",
            skills=(ref,),
        )
        out = tmp_path / "out.skillpack"
        ZipSkillPacker().pack([skill_dir], manifest, out)
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["skills"] == [{"category": "dev", "name": "my-skill", "version": "2.0.0"}]

    def test_tags_serialized_when_present(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, tags=("python", "tdd"))
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert "tags" in data
        assert set(data["tags"]) == {"python", "tdd"}

    def test_tags_omitted_when_empty(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, tags=())
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert "tags" not in data

    def test_platforms_serialized_when_present(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, platforms=("macos", "linux"))
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert set(data["platforms"]) == {"macos", "linux"}

    def test_export_formats_serialized_when_present(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, export_formats=("openai",))
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["export_formats"] == ["openai"]

    def test_owner_name_and_email_serialized(self, tmp_path: Path) -> None:
        owner = Owner(name="Bob", email="bob@example.com")
        _, out = _pack_one(tmp_path, owner=owner)
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["owner"]["name"] == "Bob"
        assert data["owner"]["email"] == "bob@example.com"

    def test_deprecated_flag_serialized(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, deprecated=True)
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert data["deprecated"] is True

    def test_deprecated_omitted_when_false(self, tmp_path: Path) -> None:
        _, out = _pack_one(tmp_path, deprecated=False)
        with zipfile.ZipFile(out) as zf:
            data = json.loads(zf.read("manifest.json"))
        assert "deprecated" not in data

    def test_serialization_indentation(self, tmp_path: Path) -> None:
        """Verify that manifest.json is indented (kills indent=None mutation)."""
        _, out = _pack_one(tmp_path)
        with zipfile.ZipFile(out) as zf:
            raw = zf.read("manifest.json").decode("utf-8")
        # If indented, it should contain a newline and spaces
        assert "\n  " in raw

    def test_pack_zero_skills_exact_message(self, tmp_path: Path) -> None:
        """Verify exact error message for empty skill_dirs."""
        manifest = SkillPackManifest(
            name="test",
            version="1",
            author="",
            created_at="",
            description="",
            skills=(SkillRef(category="c", name="n"),),
        )
        with pytest.raises(ValueError, match=r"^Cannot pack zero skills$"):
            ZipSkillPacker().pack([], manifest, tmp_path / "out.zip")

    def test_pack_file_instead_of_dir_raises(self, tmp_path: Path) -> None:
        """Verify that a file raises FileNotFoundError (kills is_dir() mutation)."""
        fake_dir = tmp_path / "not-a-dir.txt"
        fake_dir.write_text("mostly-harmless")
        manifest = SkillPackManifest(
            name="test",
            version="1",
            author="",
            created_at="",
            description="",
            skills=(SkillRef(category="c", name="n"),),
        )
        with pytest.raises(FileNotFoundError, match="Skill directory not found"):
            ZipSkillPacker().pack([fake_dir], manifest, tmp_path / "out.zip")


class TestReadManifestAllFields:
    """Round-trip: every field must survive the serialize → deserialize cycle."""

    def test_created_at_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, created_at="2026-04-15T09:30:00+00:00")
        manifest = packer.read_manifest(out)
        assert manifest.created_at == "2026-04-15T09:30:00+00:00"

    def test_name_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, name="roundtrip-pack")
        assert packer.read_manifest(out).name == "roundtrip-pack"

    def test_version_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, version="4.5.6")
        assert packer.read_manifest(out).version == "4.5.6"

    def test_author_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, author="charlie")
        assert packer.read_manifest(out).author == "charlie"

    def test_description_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, description="Exact description string")
        assert packer.read_manifest(out).description == "Exact description string"

    def test_skill_ref_category_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path)
        assert packer.read_manifest(out).skills[0].category == "dev"

    def test_skill_ref_name_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path)
        assert packer.read_manifest(out).skills[0].name == "my-skill"

    def test_tags_survive_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, tags=("rust", "webdev"))
        assert set(packer.read_manifest(out).tags) == {"rust", "webdev"}

    def test_platforms_survive_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, platforms=("linux",))
        assert packer.read_manifest(out).platforms == ("linux",)

    def test_export_formats_survive_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, export_formats=("bedrock",))
        assert packer.read_manifest(out).export_formats == ("bedrock",)

    def test_owner_name_survives_roundtrip(self, tmp_path: Path) -> None:
        owner = Owner(name="Dana", email="dana@example.com")
        packer, out = _pack_one(tmp_path, owner=owner)
        read = packer.read_manifest(out)
        assert read.owner is not None
        assert read.owner.name == "Dana"

    def test_owner_email_survives_roundtrip(self, tmp_path: Path) -> None:
        owner = Owner(name="Eve", email="eve@test.com")
        packer, out = _pack_one(tmp_path, owner=owner)
        assert packer.read_manifest(out).owner.email == "eve@test.com"

    def test_owner_email_defaults_to_empty_string(self, tmp_path: Path) -> None:
        """Verify that missing email defaults to empty string, not None."""
        _make_skill_dir(tmp_path / "src", "dev", "s")
        # Manually create a zip with a manifest missing email key
        out = tmp_path / "missing_email.zip"
        with zipfile.ZipFile(out, "w") as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format_version": "1",
                        "name": "x",
                        "version": "1",
                        "author": "",
                        "created_at": "",
                        "skills": [{"category": "dev", "name": "s"}],
                        "owner": {"name": "Bob"},
                    }
                ),
            )
        read = ZipSkillPacker().read_manifest(out)
        assert read.owner.email == ""
        assert read.owner.email is not None

    def test_unpack_missing_pack_exact_message(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match=r"^Pack not found:"):
            ZipSkillPacker().unpack(tmp_path / "missing.zip", tmp_path / "dest")

    def test_unpack_nested_destination_creation(self, tmp_path: Path) -> None:
        """Verify mkdir(parents=True) works by unpacking to a deep path."""
        _, out = _pack_one(tmp_path)
        dest = tmp_path / "very" / "deep" / "path"
        ZipSkillPacker().unpack(out, dest)
        assert (dest / "dev" / "my-skill" / "SKILL.md").exists()

    def test_unpack_skips_non_skill_files_properly(self, tmp_path: Path) -> None:
        """Verify that files outside skills/ are skipped (kills continue vs break mutation)."""
        pack = tmp_path / "mixed.zip"
        with zipfile.ZipFile(pack, "w") as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format_version": "1",
                        "name": "x",
                        "version": "1",
                        "author": "",
                        "created_at": "",
                        "skills": [{"category": "dev", "name": "s"}],
                    }
                ),
            )
            zf.writestr("root.txt", "should-be-ignored")
            zf.writestr("skills/dev/s/SKILL.md", "---\nname: s\n---")
            zf.writestr("other.txt", "should-also-be-ignored")

        dest = tmp_path / "output"
        ZipSkillPacker().unpack(pack, dest)
        assert (dest / "dev" / "s" / "SKILL.md").exists()
        assert not (dest / "root.txt").exists()
        assert not (dest / "other.txt").exists()

    def test_deprecated_true_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, deprecated=True)
        assert packer.read_manifest(out).deprecated is True

    def test_deprecated_false_survives_roundtrip(self, tmp_path: Path) -> None:
        packer, out = _pack_one(tmp_path, deprecated=False)
        assert packer.read_manifest(out).deprecated is False

    def test_missing_manifest_raises_value_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.skillpack"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("README.txt", "no manifest here")
        with pytest.raises(ValueError, match="missing manifest"):
            ZipSkillPacker().read_manifest(bad)

    def test_invalid_format_version_raises(self, tmp_path: Path) -> None:
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
                        "skills": [{"category": "d", "name": "x"}],
                    }
                ),
            )
        with pytest.raises(ValueError, match="Unsupported"):
            ZipSkillPacker().read_manifest(bad)

    def test_zero_skills_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.skillpack"
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format_version": "1",
                        "name": "x",
                        "version": "1",
                        "author": "",
                        "created_at": "",
                        "skills": [],
                    }
                ),
            )
        with pytest.raises(ValueError, match="zero skills"):
            ZipSkillPacker().read_manifest(bad)

    def test_skill_version_falls_back_to_pack_version(self, tmp_path: Path) -> None:
        """Older packs without per-skill version must use pack-level version."""
        old_pack = tmp_path / "legacy.skillpack"
        with zipfile.ZipFile(old_pack, "w") as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "format_version": "1",
                        "name": "legacy",
                        "version": "0.5.0",
                        "author": "",
                        "created_at": "",
                        "skills": [{"category": "d", "name": "s"}],
                    }
                ),
            )
        m = ZipSkillPacker().read_manifest(old_pack)
        # falls back: version=s.get('version') or data.get('version', '0.1.0')
        assert m.skills[0].version == "0.5.0"
