"""Tests for the markdown renderer adapter."""

from skill_forge.domain.model import Skill
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer


class TestMarkdownSkillRenderer:
    def setup_method(self):
        self.renderer = MarkdownSkillRenderer()

    def test_renders_frontmatter(self, minimal_skill: Skill):
        output = self.renderer.render_skill_md(minimal_skill)
        assert output.startswith("---\n")
        assert "name: python-tdd" in output
        assert "description: |" in output

    def test_renders_starter_character(self, minimal_skill: Skill):
        output = self.renderer.render_skill_md(minimal_skill)
        assert "STARTER_CHARACTER = 🔴" in output

    def test_renders_principles(self, minimal_skill: Skill):
        output = self.renderer.render_skill_md(minimal_skill)
        assert "## Principles" in output
        assert "- Write the failing test first" in output

    def test_renders_references(self, skill_with_references: Skill):
        output = self.renderer.render_skill_md(skill_with_references)
        assert "## References" in output
        assert "[REST naming conventions]" in output

    def test_roundtrip_preserves_identity(self, minimal_skill: Skill):
        """Render then parse should preserve the skill's identity."""
        from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

        output = self.renderer.render_skill_md(minimal_skill)
        parser = MarkdownSkillParser()
        parsed = parser.parse(output)

        assert parsed.identity.name == minimal_skill.identity.name
