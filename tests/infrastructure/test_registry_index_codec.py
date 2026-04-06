"""Tests for the JSON codec used by the git registry publisher and fetcher."""

from __future__ import annotations

import json

import pytest

from skill_forge.domain.model import (
    IndexedSkill,
    IndexedVersion,
    Owner,
    RegistryIndex,
)
from skill_forge.infrastructure.adapters.registry_index_codec import (
    RegistryIndexCodec,
)

SHA = "a" * 64


def _index() -> RegistryIndex:
    return RegistryIndex(
        registry_name="acme-skills",
        base_url="https://raw.githubusercontent.com/acme/skills/main",
        updated_at="2026-04-06T12:00:00+00:00",
        skills=(
            IndexedSkill(
                category="development",
                name="python-tdd",
                latest="0.2.0",
                versions=(
                    IndexedVersion(
                        version="0.1.0",
                        path="packs/development/python-tdd-0.1.0.skillpack",
                        sha256=SHA,
                    ),
                    IndexedVersion(
                        version="0.2.0",
                        path="packs/development/python-tdd-0.2.0.skillpack",
                        sha256="b" * 64,
                    ),
                ),
            ),
        ),
    )


class TestRoundtrip:
    def test_encode_decode_preserves_index(self) -> None:
        codec = RegistryIndexCodec()
        encoded = codec.encode(_index())
        decoded = codec.decode(encoded)
        assert decoded == _index()

    def test_encoded_payload_is_valid_json_with_format_version(self) -> None:
        codec = RegistryIndexCodec()
        encoded = codec.encode(_index())
        data = json.loads(encoded)
        assert data["format_version"] == "1"
        assert data["registry_name"] == "acme-skills"
        assert data["skills"][0]["latest"] == "0.2.0"
        assert len(data["skills"][0]["versions"]) == 2

    def test_roundtrip_with_full_metadata(self) -> None:
        codec = RegistryIndexCodec()
        rich = RegistryIndex(
            registry_name="acme-skills",
            base_url="https://raw.githubusercontent.com/acme/skills/main",
            updated_at="2026-04-06T12:00:00+00:00",
            skills=(
                IndexedSkill(
                    category="development",
                    name="python-tdd",
                    latest="0.2.0",
                    versions=(
                        IndexedVersion(
                            version="0.1.0",
                            path="packs/development/python-tdd-0.1.0.skillpack",
                            sha256=SHA,
                            published_at="2026-04-01T10:00:00+00:00",
                            size_bytes=1234,
                            release_notes="initial cut",
                            yanked=True,
                        ),
                        IndexedVersion(
                            version="0.2.0",
                            path="packs/development/python-tdd-0.2.0.skillpack",
                            sha256="b" * 64,
                            published_at="2026-04-06T12:00:00+00:00",
                            size_bytes=2048,
                            release_notes="bug fixes",
                        ),
                    ),
                    description="Use for TDD with Python.",
                    tags=("tdd", "python"),
                    owner=Owner(name="Acme", email="team@acme.test"),
                    deprecated=False,
                ),
            ),
        )
        decoded = codec.decode(codec.encode(rich))
        assert decoded == rich

    def test_decode_old_index_without_new_fields(self) -> None:
        """Older index.json files (no description/tags/owner/etc) must still decode."""
        legacy = json.dumps(
            {
                "format_version": "1",
                "registry_name": "acme",
                "base_url": "https://example.com",
                "updated_at": "",
                "skills": [
                    {
                        "category": "development",
                        "name": "python-tdd",
                        "latest": "0.1.0",
                        "versions": [
                            {
                                "version": "0.1.0",
                                "path": "packs/development/python-tdd-0.1.0.skillpack",
                                "sha256": SHA,
                            }
                        ],
                    }
                ],
            }
        )
        decoded = RegistryIndexCodec().decode(legacy)
        assert decoded.skills[0].description == ""
        assert decoded.skills[0].tags == ()
        assert decoded.skills[0].owner is None
        assert decoded.skills[0].deprecated is False
        v = decoded.skills[0].versions[0]
        assert v.published_at == ""
        assert v.size_bytes == 0
        assert v.release_notes == ""
        assert v.yanked is False

    def test_decode_rejects_unsupported_format(self) -> None:
        codec = RegistryIndexCodec()
        bogus = json.dumps(
            {
                "format_version": "999",
                "registry_name": "x",
                "base_url": "https://example.com",
                "updated_at": "",
                "skills": [],
            }
        )
        with pytest.raises(ValueError, match="format version"):
            codec.decode(bogus)


class TestUpsert:
    def test_adds_new_skill(self) -> None:
        empty = RegistryIndex(
            registry_name="r",
            base_url="https://example.com",
            updated_at="t",
            skills=(),
        )
        added = empty.upsert(
            "dev",
            "tool",
            IndexedVersion(version="0.1.0", path="packs/dev/tool-0.1.0.skillpack", sha256=SHA),
        )
        assert len(added.skills) == 1
        assert added.skills[0].latest == "0.1.0"

    def test_replaces_existing_version(self) -> None:
        idx = _index().upsert(
            "development",
            "python-tdd",
            IndexedVersion(
                version="0.2.0",
                path="packs/development/python-tdd-0.2.0.skillpack",
                sha256="c" * 64,
            ),
        )
        skill = idx.find("development", "python-tdd")
        assert skill is not None
        assert len(skill.versions) == 2
        assert skill.find("0.2.0").sha256 == "c" * 64  # type: ignore[union-attr]

    def test_preserves_skill_metadata_on_replay(self) -> None:
        seeded = _index().upsert(
            "development",
            "python-tdd",
            IndexedVersion(
                version="0.3.0",
                path="packs/development/python-tdd-0.3.0.skillpack",
                sha256="e" * 64,
            ),
            description="A TDD helper",
            tags=("tdd", "python"),
            owner=Owner(name="Acme", email="team@acme.test"),
        )
        # Re-upsert without metadata: existing skill-level fields should stick.
        replayed = seeded.upsert(
            "development",
            "python-tdd",
            IndexedVersion(
                version="0.4.0",
                path="packs/development/python-tdd-0.4.0.skillpack",
                sha256="f" * 64,
            ),
        )
        skill = replayed.find("development", "python-tdd")
        assert skill is not None
        assert skill.description == "A TDD helper"
        assert skill.tags == ("tdd", "python")
        assert skill.owner is not None and skill.owner.name == "Acme"
        assert skill.latest == "0.4.0"

    def test_yanked_version_does_not_promote_latest(self) -> None:
        idx = _index().upsert(
            "development",
            "python-tdd",
            IndexedVersion(
                version="0.5.0",
                path="packs/development/python-tdd-0.5.0.skillpack",
                sha256="9" * 64,
                yanked=True,
            ),
        )
        skill = idx.find("development", "python-tdd")
        assert skill is not None
        # 0.5.0 is yanked, so latest should remain 0.2.0 (the highest non-yanked).
        assert skill.latest == "0.2.0"

    def test_promotes_latest_when_higher_version_added(self) -> None:
        idx = _index().upsert(
            "development",
            "python-tdd",
            IndexedVersion(
                version="0.10.0",
                path="packs/development/python-tdd-0.10.0.skillpack",
                sha256="d" * 64,
            ),
        )
        skill = idx.find("development", "python-tdd")
        assert skill is not None
        assert skill.latest == "0.10.0"
