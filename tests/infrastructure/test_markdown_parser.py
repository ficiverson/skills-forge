"""Tests for the markdown parser adapter."""

from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser


class TestMarkdownSkillParser:
    def setup_method(self):
        self.parser = MarkdownSkillParser()

    def test_parses_frontmatter(self):
        content = (
            "---\n"
            "name: python-tdd\n"
            "description: |\n"
            "  Use for TDD with Python.\n"
            "---\n"
            "\n"
            "## Instructions\n"
            "\n"
            "Write tests first.\n"
        )
        skill = self.parser.parse(content)

        assert skill.identity.name == "python-tdd"
        assert "TDD" in skill.description.text

    def test_parses_starter_character(self):
        content = (
            "---\n"
            "name: test\n"
            "description: test\n"
            "---\n"
            "\n"
            "STARTER_CHARACTER = 🔴\n"
            "\n"
            "## Instructions\n"
            "\n"
            "Do things.\n"
        )
        skill = self.parser.parse(content)
        assert skill.starter_character is not None
        assert str(skill.starter_character) == "🔴"

    def test_parses_principles_and_constraints(self):
        content = (
            "---\n"
            "name: test\n"
            "description: test\n"
            "---\n"
            "\n"
            "## Principles\n"
            "\n"
            "- First principle\n"
            "- Second principle\n"
            "\n"
            "## Instructions\n"
            "\n"
            "Some instructions here.\n"
            "\n"
            "## Constraints\n"
            "\n"
            "- Do not do X\n"
            "- Always do Y\n"
        )
        skill = self.parser.parse(content)

        assert len(skill.content.principles) == 2
        assert skill.content.principles[0] == "First principle"
        assert len(skill.content.constraints) == 2
        assert "instructions here" in skill.content.instructions

    def test_parses_references(self):
        content = (
            "---\n"
            "name: test\n"
            "description: test\n"
            "---\n"
            "\n"
            "## References\n"
            "\n"
            "- [REST guide](references/rest.md)\n"
            "- [HTTP codes](references/http.md)\n"
        )
        skill = self.parser.parse(content)

        assert len(skill.references) == 2
        assert skill.references[0].purpose == "REST guide"
        assert str(skill.references[0].path) == "references/rest.md"

    def test_handles_missing_frontmatter(self):
        content = "## Instructions\n\nJust do it.\n"
        skill = self.parser.parse(content)
        assert skill.identity.name == "unknown"
