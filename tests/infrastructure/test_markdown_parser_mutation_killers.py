"""Mutation-killing tests for MarkdownSkillParser.

Targets _parse_frontmatter, _parse_content, _parse_references,
_parse_link_section, _parse_dependencies, _parse_allowed_tools, _parse_evals.
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

PARSER = MarkdownSkillParser()


FULL_SKILL_MD = """\
---
name: python-tdd
category: dev
version: 2.1.0
description: Generate and validate .py unit tests using TDD
requires-forge: ">=0.4.0"
depends_on: pdf-export (PDF reports), csv-reader
allowed-tools: [Bash, Read, Write]
---

STARTER_CHARACTER = 🧪

## Principles

- Write tests first
- Keep functions small

## Instructions

Always run pytest before committing.

## Constraints

- No global mutable state

## Hints

Use fixtures for repeated setup.

## References

- [Style Guide](references/style.md)
- [Python Docs](references/python.md)

## Scripts

- [Run Tests](scripts/run_tests.sh)

## Examples

- [Sample Output](examples/output.json)

## Assets

- [Test Data](assets/data.csv)
"""


class TestParseName:
    def test_name_is_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.identity.name == "python-tdd"

    def test_unknown_name_when_missing(self) -> None:
        skill = PARSER.parse("---\ndescription: test\n---\n\n## Principles\n")
        assert skill.identity.name == "unknown"


class TestParseVersion:
    def test_version_is_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.version == "2.1.0"

    def test_version_defaults_to_default_when_absent(self) -> None:
        from skill_forge.domain.model import DEFAULT_SKILL_VERSION
        md = "---\nname: x\ndescription: test\n---\n"
        skill = PARSER.parse(md)
        assert skill.version == DEFAULT_SKILL_VERSION

    def test_version_stripped_of_whitespace(self) -> None:
        md = "---\nname: x\nversion:  1.0.0  \ndescription: test\n---\n"
        skill = PARSER.parse(md)
        assert skill.version == "1.0.0"


class TestParseDescription:
    def test_description_is_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert "Generate" in skill.description.text
        assert ".py" in skill.description.text

    def test_description_stripped(self) -> None:
        md = "---\nname: x\ndescription:   trimmed  \n---\n"
        skill = PARSER.parse(md)
        assert skill.description.text == "trimmed"


class TestParseRequiresForge:
    def test_requires_forge_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.requires_forge == ">=0.4.0"

    def test_requires_forge_none_when_absent(self) -> None:
        md = "---\nname: x\ndescription: test\n---\n"
        skill = PARSER.parse(md)
        assert skill.requires_forge is None

    def test_requires_forge_none_when_empty_string(self) -> None:
        md = "---\nname: x\ndescription: test\nrequires-forge:   \n---\n"
        skill = PARSER.parse(md)
        assert skill.requires_forge is None


class TestParseStarterCharacter:
    def test_starter_character_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.starter_character is not None
        assert skill.starter_character.emoji == "🧪"

    def test_no_starter_character_when_absent(self) -> None:
        md = "---\nname: x\ndescription: test\n---\n\n## Principles\n- Be good\n"
        skill = PARSER.parse(md)
        assert skill.starter_character is None


class TestParseContent:
    def test_principles_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert "Write tests first" in skill.content.principles
        assert "Keep functions small" in skill.content.principles

    def test_instructions_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert "pytest" in skill.content.instructions

    def test_constraints_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert "No global mutable state" in skill.content.constraints

    def test_hints_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert "fixtures" in skill.content.hints


class TestParseReferences:
    def test_references_count(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert len(skill.references) == 2

    def test_reference_path(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        paths = [str(r.path) for r in skill.references]
        assert "references/style.md" in paths

    def test_reference_purpose(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        purposes = [r.purpose for r in skill.references]
        assert "Style Guide" in purposes

    def test_reference_second_item(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert str(skill.references[1].path) == "references/python.md"
        assert skill.references[1].purpose == "Python Docs"


class TestParseScripts:
    def test_scripts_count(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert len(skill.scripts) == 1

    def test_script_path(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert str(skill.scripts[0].path) == "scripts/run_tests.sh"

    def test_script_description(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.scripts[0].description == "Run Tests"


class TestParseExamples:
    def test_examples_count(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert len(skill.examples) == 1

    def test_example_path(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert str(skill.examples[0].path) == "examples/output.json"


class TestParseAssets:
    def test_assets_count(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert len(skill.assets) == 1

    def test_asset_path(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert str(skill.assets[0].path) == "assets/data.csv"

    def test_asset_description(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.assets[0].description == "Test Data"


class TestParseAllowedTools:
    def test_allowed_tools_inline_list(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert "Bash" in skill.allowed_tools
        assert "Read" in skill.allowed_tools
        assert "Write" in skill.allowed_tools

    def test_no_allowed_tools_when_absent(self) -> None:
        md = "---\nname: x\ndescription: test\n---\n"
        skill = PARSER.parse(md)
        assert skill.allowed_tools == []

    def test_newline_separated_tools(self) -> None:
        md = "---\nname: x\ndescription: test\nallowed-tools: |\n  Bash\n  Read\n---\n"
        skill = PARSER.parse(md)
        assert "Bash" in skill.allowed_tools


class TestParseDependencies:
    def test_dependencies_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        names = [d.skill_name for d in skill.depends_on]
        assert "pdf-export" in names
        assert "csv-reader" in names

    def test_dependency_reason_extracted(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        pdf_dep = next(d for d in skill.depends_on if d.skill_name == "pdf-export")
        assert pdf_dep.reason == "PDF reports"

    def test_dependency_no_reason(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        csv_dep = next(d for d in skill.depends_on if d.skill_name == "csv-reader")
        assert csv_dep.reason == ""

    def test_no_deps_when_absent(self) -> None:
        md = "---\nname: x\ndescription: test\n---\n"
        skill = PARSER.parse(md)
        assert skill.depends_on == []


class TestParseEvalsFromFile:
    def test_evals_loaded_from_file(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "python-tdd"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(FULL_SKILL_MD, encoding="utf-8")
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir()
        (evals_dir / "evals.json").write_text(json.dumps([
            {
                "id": 1, "prompt": "Write a test", "expected_output": "def test_",
                "assertions": [
                    {
                        "id": "a1", "text": "Has test", "type": "contains",
                        "expected": "def test_"
                    }
                ]
            },
        ]), encoding="utf-8")

        skill = PARSER.parse(FULL_SKILL_MD, base_path=skill_dir)
        assert len(skill.evals) == 1
        assert skill.evals[0].id == 1
        assert skill.evals[0].prompt == "Write a test"
        assert skill.evals[0].expected_output == "def test_"

    def test_evals_assertion_fields_loaded(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "s"
        skill_dir.mkdir()
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir()
        (evals_dir / "evals.json").write_text(json.dumps([
            {
                "id": 2, "prompt": "p", "expected_output": "o",
                "assertions": [
                    {"id": "x1", "text": "Has output", "type": "llm-judge", "expected": ""}
                ]
            },
        ]), encoding="utf-8")
        skill = PARSER.parse(FULL_SKILL_MD, base_path=skill_dir)
        assert len(skill.evals[0].assertions) == 1
        assert skill.evals[0].assertions[0].id == "x1"
        assert skill.evals[0].assertions[0].text == "Has output"
        assert skill.evals[0].assertions[0].type == "llm-judge"

    def test_no_evals_when_no_base_path(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.evals == []

    def test_no_evals_when_file_missing(self, tmp_path: Path) -> None:
        skill = PARSER.parse(FULL_SKILL_MD, base_path=tmp_path)
        assert skill.evals == []


class TestInferCategory:
    def test_category_from_output_skills_path(self, tmp_path: Path) -> None:
        base = tmp_path / "output_skills" / "backend" / "my-skill"
        base.mkdir(parents=True)
        skill = PARSER.parse(FULL_SKILL_MD, base_path=base)
        assert skill.identity.category == "backend"

    def test_category_from_output_skills_path_shallow(self, tmp_path: Path) -> None:
        """Verify index logic in _infer_category with a shallow path."""
        base = Path("output_skills") / "frontend" / "s"
        # We don't need actual directory creation if we just pass the Path object
        skill = PARSER.parse(FULL_SKILL_MD, base_path=base)
        assert skill.identity.category == "frontend"

    def test_category_falls_back_to_dir_name(self, tmp_path: Path) -> None:
        base = tmp_path / "my-category"
        base.mkdir()
        skill = PARSER.parse(FULL_SKILL_MD, base_path=base)
        assert skill.identity.category == "my-category"

    def test_uncategorized_when_no_path(self) -> None:
        skill = PARSER.parse(FULL_SKILL_MD)
        assert skill.identity.category == "uncategorized"

class TestStripFrontmatter:
    def test_strip_handles_no_match_gracefully(self) -> None:
        """Verify that _strip_frontmatter returns full content if no match."""
        content = "## No Frontmatter\nJust content."
        stripped = PARSER._strip_frontmatter(content)
        assert stripped == content

    def test_strip_handles_empty_content(self) -> None:
        assert PARSER._strip_frontmatter("") == ""

class TestParseFrontmatterLogic:
    def test_parse_empty_content_returns_empty_dict(self) -> None:
        assert PARSER._parse_frontmatter("") == {}

    def test_parse_invalid_frontmatter_returns_empty_dict(self) -> None:
        assert PARSER._parse_frontmatter("not---frontmatter") == {}
