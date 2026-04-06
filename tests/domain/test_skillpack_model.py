"""Tests for the SkillPack domain model."""

from __future__ import annotations

import pytest

from skill_forge.domain.model import SkillPackManifest, SkillRef


class TestSkillRef:
    def test_valid_ref(self):
        ref = SkillRef(category="testing", name="cypress-e2e", version="1.2.0")
        assert ref.category == "testing"
        assert ref.name == "cypress-e2e"
        assert ref.version == "1.2.0"
        assert str(ref) == "testing/cypress-e2e@1.2.0"

    def test_default_version(self):
        ref = SkillRef(category="testing", name="cypress-e2e")
        assert ref.version == "0.1.0"

    def test_empty_version_raises(self):
        with pytest.raises(ValueError, match="version cannot be empty"):
            SkillRef(category="testing", name="x", version="")

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            SkillRef(category="testing", name="")

    def test_empty_category_raises(self):
        with pytest.raises(ValueError, match="category cannot be empty"):
            SkillRef(category="", name="cypress-e2e")

    def test_whitespace_only_name_raises(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            SkillRef(category="testing", name="   ")


class TestSkillPackManifest:
    def test_valid_manifest(self):
        manifest = SkillPackManifest(
            name="my-pack",
            version="1.0.0",
            author="fer",
            created_at="2026-04-06T12:00:00+00:00",
            skills=(SkillRef(category="dev", name="python-tdd"),),
        )
        assert manifest.name == "my-pack"
        assert manifest.skill_count == 1
        assert manifest.FORMAT_VERSION == "1"

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name cannot be empty"):
            SkillPackManifest(
                name="",
                version="1.0.0",
                author="",
                created_at="2026-04-06",
                skills=(SkillRef(category="dev", name="x"),),
            )

    def test_empty_version_raises(self):
        with pytest.raises(ValueError, match="version cannot be empty"):
            SkillPackManifest(
                name="x",
                version="",
                author="",
                created_at="2026-04-06",
                skills=(SkillRef(category="dev", name="x"),),
            )

    def test_zero_skills_raises(self):
        with pytest.raises(ValueError, match="at least one skill"):
            SkillPackManifest(
                name="x",
                version="1.0.0",
                author="",
                created_at="2026-04-06",
                skills=(),
            )

    def test_multi_skill_count(self):
        manifest = SkillPackManifest(
            name="bundle",
            version="0.1.0",
            author="",
            created_at="2026-04-06",
            skills=(
                SkillRef(category="dev", name="a"),
                SkillRef(category="dev", name="b"),
                SkillRef(category="ops", name="c"),
            ),
        )
        assert manifest.skill_count == 3

    def test_format_version_is_class_constant(self):
        # Should not be an instance field — same value across instances
        m1 = SkillPackManifest(
            name="a",
            version="1",
            author="",
            created_at="",
            skills=(SkillRef(category="x", name="y"),),
        )
        m2 = SkillPackManifest(
            name="b",
            version="2",
            author="",
            created_at="",
            skills=(SkillRef(category="x", name="z"),),
        )
        assert m1.FORMAT_VERSION == m2.FORMAT_VERSION == "1"
