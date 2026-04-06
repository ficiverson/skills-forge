"""Tests for new parser/renderer features: examples, assets, depends_on, hints."""

from __future__ import annotations

from pathlib import PurePosixPath

from skill_forge.domain.model import (
    Asset,
    Dependency,
    Description,
    Example,
    Skill,
    SkillContent,
    SkillIdentity,
)
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer


class TestParserNewSections:
    def setup_method(self):
        self.parser = MarkdownSkillParser()

    def test_parses_examples_section(self):
        content = """\
---
name: test-skill
description: A test skill
---

## Examples

Sample outputs:

- [Example JSON](examples/output.json)
- [Example report](examples/report.md)
"""
        skill = self.parser.parse(content)
        assert len(skill.examples) == 2
        assert skill.examples[0].path == PurePosixPath("examples/output.json")
        assert skill.examples[0].description == "Example JSON"
        assert skill.examples[1].description == "Example report"

    def test_parses_assets_section(self):
        content = """\
---
name: test-skill
description: A test skill
---

## Assets

Static files:

- [Data CSV](assets/data.csv)
"""
        skill = self.parser.parse(content)
        assert len(skill.assets) == 1
        assert skill.assets[0].path == PurePosixPath("assets/data.csv")
        assert skill.assets[0].description == "Data CSV"

    def test_parses_depends_on_single(self):
        content = """\
---
name: test-skill
description: A test skill
depends_on: pdf (PDF generation)
---
"""
        skill = self.parser.parse(content)
        assert len(skill.depends_on) == 1
        assert skill.depends_on[0].skill_name == "pdf"
        assert skill.depends_on[0].reason == "PDF generation"

    def test_parses_depends_on_multiple(self):
        content = """\
---
name: test-skill
description: A test skill
depends_on: pdf (PDF generation), xlsx (spreadsheet output)
---
"""
        skill = self.parser.parse(content)
        assert len(skill.depends_on) == 2
        assert skill.depends_on[0].skill_name == "pdf"
        assert skill.depends_on[1].skill_name == "xlsx"

    def test_parses_depends_on_without_reason(self):
        content = """\
---
name: test-skill
description: A test skill
depends_on: pdf
---
"""
        skill = self.parser.parse(content)
        assert len(skill.depends_on) == 1
        assert skill.depends_on[0].skill_name == "pdf"
        assert skill.depends_on[0].reason == ""

    def test_parses_hints_section(self):
        content = """\
---
name: test-skill
description: A test skill
---

## Hints

If the project uses TypeScript, check tsconfig.json.
If no tests exist, score code_quality lower.
"""
        skill = self.parser.parse(content)
        assert "TypeScript" in skill.content.hints
        assert "tsconfig.json" in skill.content.hints

    def test_no_depends_on_returns_empty_list(self):
        content = """\
---
name: test-skill
description: A test skill
---
"""
        skill = self.parser.parse(content)
        assert skill.depends_on == []

    def test_no_examples_returns_empty_list(self):
        content = """\
---
name: test-skill
description: A test skill
---

## References

- [Guide](references/guide.md)
"""
        skill = self.parser.parse(content)
        assert skill.examples == []


class TestRendererNewSections:
    def setup_method(self):
        self.renderer = MarkdownSkillRenderer()

    def test_renders_examples_section(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="testing"),
            description=Description(text="A test skill"),
            examples=[
                Example(
                    path=PurePosixPath("examples/output.json"),
                    description="Example output",
                ),
            ],
        )
        md = self.renderer.render_skill_md(skill)
        assert "## Examples" in md
        assert "[Example output](examples/output.json)" in md

    def test_renders_assets_section(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="testing"),
            description=Description(text="A test skill"),
            assets=[
                Asset(
                    path=PurePosixPath("assets/data.csv"),
                    description="Data file",
                ),
            ],
        )
        md = self.renderer.render_skill_md(skill)
        assert "## Assets" in md
        assert "[Data file](assets/data.csv)" in md

    def test_renders_depends_on_in_frontmatter(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="testing"),
            description=Description(text="A test skill"),
            depends_on=[
                Dependency(skill_name="pdf", reason="PDF generation"),
            ],
        )
        md = self.renderer.render_skill_md(skill)
        assert "depends_on: pdf (PDF generation)" in md

    def test_renders_hints_section(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="testing"),
            description=Description(text="A test skill"),
            content=SkillContent(
                hints="If no tests exist, lower the score.",
            ),
        )
        md = self.renderer.render_skill_md(skill)
        assert "## Hints" in md
        assert "If no tests exist" in md

    def test_omits_sections_when_empty(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="testing"),
            description=Description(text="A test skill"),
        )
        md = self.renderer.render_skill_md(skill)
        assert "## Examples" not in md
        assert "## Assets" not in md
        assert "## Hints" not in md
        assert "depends_on" not in md


class TestNewModelProperties:
    def test_has_assets(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="test"),
            description=Description(text="Test"),
            assets=[Asset(path=PurePosixPath("assets/x.csv"), description="X")],
        )
        assert skill.has_assets is True

    def test_has_examples(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="test"),
            description=Description(text="Test"),
            examples=[Example(path=PurePosixPath("examples/x.json"), description="X")],
        )
        assert skill.has_examples is True

    def test_has_dependencies(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="test"),
            description=Description(text="Test"),
            depends_on=[Dependency(skill_name="pdf", reason="")],
        )
        assert skill.has_dependencies is True

    def test_empty_skill_has_no_new_features(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="test"),
            description=Description(text="Test"),
        )
        assert skill.has_assets is False
        assert skill.has_examples is False
        assert skill.has_dependencies is False

    def test_hints_count_toward_token_estimate(self):
        content_no_hints = SkillContent(instructions="Do this thing.")
        content_with_hints = SkillContent(
            instructions="Do this thing.",
            hints="If TypeScript project check tsconfig for cypress types.",
        )
        assert content_with_hints.estimated_tokens > content_no_hints.estimated_tokens
