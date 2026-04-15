"""Tests for the evals parser integration in MarkdownSkillParser."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

MINIMAL_SKILL_MD = textwrap.dedent("""\
    ---
    name: test-skill
    version: 0.1.0
    description: |
      Test skill for parsing evals.
    ---

    STARTER_CHARACTER = 🧪

    ## Principles

    - Test everything
""")


@pytest.fixture
def parser() -> MarkdownSkillParser:
    return MarkdownSkillParser()


@pytest.fixture
def skill_dir(tmp_path: Path) -> Path:
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(MINIMAL_SKILL_MD, encoding="utf-8")
    return skill_dir


class TestEvalsParserNoFile:
    def test_no_base_path_returns_empty(self, parser: MarkdownSkillParser) -> None:
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=None)
        assert skill.evals == []

    def test_no_evals_dir_returns_empty(
        self, parser: MarkdownSkillParser, skill_dir: Path
    ) -> None:
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert skill.evals == []

    def test_empty_evals_dir_returns_empty(
        self, parser: MarkdownSkillParser, skill_dir: Path
    ) -> None:
        (skill_dir / "evals").mkdir()
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert skill.evals == []


class TestEvalsParserValid:
    def _write_evals(self, skill_dir: Path, data: object) -> None:
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir(exist_ok=True)
        (evals_dir / "evals.json").write_text(json.dumps(data), encoding="utf-8")

    def test_empty_array(self, parser: MarkdownSkillParser, skill_dir: Path) -> None:
        self._write_evals(skill_dir, [])
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert skill.evals == []

    def test_single_case_no_assertions(self, parser: MarkdownSkillParser, skill_dir: Path) -> None:
        self._write_evals(
            skill_dir,
            [
                {
                    "id": 1,
                    "prompt": "Hello",
                    "expected_output": "World",
                    "assertions": [],
                    "files": [],
                }
            ],
        )
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert len(skill.evals) == 1
        case = skill.evals[0]
        assert case.id == 1
        assert case.prompt == "Hello"
        assert case.expected_output == "World"
        assert case.assertions == ()
        assert case.files == ()

    def test_case_with_contains_assertion(
        self, parser: MarkdownSkillParser, skill_dir: Path
    ) -> None:
        self._write_evals(
            skill_dir,
            [
                {
                    "id": 1,
                    "prompt": "What is 2+2?",
                    "expected_output": "4",
                    "assertions": [
                        {
                            "id": "has-answer",
                            "text": "Response contains 4",
                            "type": "contains",
                            "expected": "4",
                        }
                    ],
                }
            ],
        )
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert len(skill.evals) == 1
        assertion = skill.evals[0].assertions[0]
        assert assertion.id == "has-answer"
        assert assertion.type == "contains"
        assert assertion.expected == "4"

    def test_case_with_files(self, parser: MarkdownSkillParser, skill_dir: Path) -> None:
        self._write_evals(
            skill_dir,
            [
                {
                    "id": 1,
                    "prompt": "Analyse",
                    "expected_output": "...",
                    "files": ["fixtures/sample.py"],
                }
            ],
        )
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert skill.evals[0].files == ("fixtures/sample.py",)

    def test_multiple_cases(self, parser: MarkdownSkillParser, skill_dir: Path) -> None:
        self._write_evals(
            skill_dir,
            [
                {"id": 1, "prompt": "p1", "expected_output": "o1"},
                {"id": 2, "prompt": "p2", "expected_output": "o2"},
            ],
        )
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert len(skill.evals) == 2


class TestEvalsParserMalformed:
    def _write_evals(self, skill_dir: Path, text: str) -> None:
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir(exist_ok=True)
        (evals_dir / "evals.json").write_text(text, encoding="utf-8")

    def test_invalid_json_returns_empty(
        self, parser: MarkdownSkillParser, skill_dir: Path
    ) -> None:
        self._write_evals(skill_dir, "{not valid json")
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        # Parser swallows parse errors; linter catches them
        assert skill.evals == []

    def test_non_array_returns_empty(self, parser: MarkdownSkillParser, skill_dir: Path) -> None:
        self._write_evals(skill_dir, '{"key": "value"}')
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        assert skill.evals == []

    def test_invalid_assertion_type_skipped(
        self, parser: MarkdownSkillParser, skill_dir: Path
    ) -> None:
        """Cases with invalid assertion types are silently skipped in the parser
        (linter surfaces them as actionable errors)."""
        self._write_evals(
            skill_dir,
            '[{"id": 1, "prompt": "p", "expected_output": "o",'
            ' "assertions": [{"id": "a", "text": "t", "type": "invalid-type"}]}]',
        )
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=skill_dir)
        # Case is skipped because assertion construction raises ValueError
        assert skill.evals == []


class TestFrontmatterHyphenatedKeys:
    """Parser correctly handles hyphenated frontmatter keys like requires-forge."""

    def test_requires_forge_double_quoted(self, parser: MarkdownSkillParser) -> None:
        md = (
            "---\nname: my-skill\ndescription: |\n  A skill.\n"
            'requires-forge: ">=0.4.0"\n---\n## Principles\n- p\n'
        )
        skill = parser.parse(md, base_path=None)
        assert skill.requires_forge == ">=0.4.0"

    def test_requires_forge_single_quoted(self, parser: MarkdownSkillParser) -> None:
        md = (
            "---\nname: my-skill\ndescription: |\n  A skill.\n"
            "requires-forge: '>=0.4.0'\n---\n## Principles\n- p\n"
        )
        skill = parser.parse(md, base_path=None)
        assert skill.requires_forge == ">=0.4.0"

    def test_requires_forge_unquoted(self, parser: MarkdownSkillParser) -> None:
        md = (
            "---\nname: my-skill\ndescription: |\n  A skill.\n"
            "requires-forge: >=0.4.0\n---\n## Principles\n- p\n"
        )
        skill = parser.parse(md, base_path=None)
        assert skill.requires_forge == ">=0.4.0"

    def test_requires_forge_absent(self, parser: MarkdownSkillParser) -> None:
        skill = parser.parse(MINIMAL_SKILL_MD, base_path=None)
        assert skill.requires_forge is None
