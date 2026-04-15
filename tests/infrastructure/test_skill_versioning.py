"""Tests for per-skill versioning: parser, renderer, and roundtrip."""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import (
    DEFAULT_SKILL_VERSION,
    Description,
    Skill,
    SkillIdentity,
)
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer


class TestParserVersion:
    def test_parses_explicit_version(self):
        content = "---\nname: my-skill\nversion: 1.2.3\ndescription: Test description\n---\n"
        skill = MarkdownSkillParser().parse(content)
        assert skill.version == "1.2.3"

    def test_parses_missing_version_as_default(self):
        content = "---\nname: my-skill\ndescription: Test description\n---\n"
        skill = MarkdownSkillParser().parse(content)
        assert skill.version == DEFAULT_SKILL_VERSION

    def test_parses_blank_version_as_default(self):
        content = "---\nname: my-skill\nversion:\ndescription: Test\n---\n"
        skill = MarkdownSkillParser().parse(content)
        assert skill.version == DEFAULT_SKILL_VERSION


class TestRendererVersion:
    def test_renders_version_in_frontmatter(self):
        skill = Skill(
            identity=SkillIdentity(name="my-skill", category="dev"),
            description=Description(text="Test"),
            version="2.0.0",
        )
        rendered = MarkdownSkillRenderer().render_skill_md(skill)
        assert "version: 2.0.0" in rendered

    def test_renders_default_version_when_unset(self):
        skill = Skill(
            identity=SkillIdentity(name="my-skill", category="dev"),
            description=Description(text="Test"),
        )
        rendered = MarkdownSkillRenderer().render_skill_md(skill)
        assert f"version: {DEFAULT_SKILL_VERSION}" in rendered


class TestVersionRoundtrip:
    def test_render_then_parse_preserves_version(self):
        original = Skill(
            identity=SkillIdentity(name="round-trip", category="dev"),
            description=Description(text="A test"),
            version="3.4.5",
        )
        rendered = MarkdownSkillRenderer().render_skill_md(original)
        parsed = MarkdownSkillParser().parse(rendered)
        assert parsed.version == "3.4.5"

    def test_version_survives_filesystem_roundtrip(self, tmp_path: Path):
        skill_dir = tmp_path / "dev" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\nversion: 9.9.9\ndescription: x\n---\n",
            encoding="utf-8",
        )
        skill = MarkdownSkillParser().parse(
            (skill_dir / "SKILL.md").read_text(encoding="utf-8"),
            base_path=skill_dir / "SKILL.md",
        )
        assert skill.version == "9.9.9"
