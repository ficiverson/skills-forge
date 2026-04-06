"""Integration tests: lint use case with path-aware validators."""

from __future__ import annotations

from pathlib import Path

from skill_forge.application.use_cases.lint_skill import LintSkill, LintSkillRequest
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer
from skill_forge.domain.model import Skill


class TestLintWithFilesystem:
    """Test that path-aware validators run when a path is provided."""

    def test_broken_reference_detected_via_path(self, tmp_path: Path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""\
---
name: test-skill
description: |
  A test skill for linting. Triggers on: test, validate, lint.
---

STARTER_CHARACTER = 🧪

## Principles

- Test everything

## References

- [Missing guide](references/guide.md)
""", encoding="utf-8")

        lint = LintSkill(parser=MarkdownSkillParser())
        request = LintSkillRequest(path=skill_md)
        response = lint.execute(request)

        broken = [i for i in response.report.issues if i.rule == "broken-reference-link"]
        assert len(broken) == 1
        assert "guide.md" in broken[0].message

    def test_valid_reference_passes_via_path(self, tmp_path: Path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "guide.md").write_text("# Guide\n")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""\
---
name: test-skill
description: |
  A test skill for linting. Triggers on: test, validate, lint.
---

STARTER_CHARACTER = 🧪

## Principles

- Test everything

## References

- [Guide](references/guide.md)
""", encoding="utf-8")

        lint = LintSkill(parser=MarkdownSkillParser())
        request = LintSkillRequest(path=skill_md)
        response = lint.execute(request)

        broken = [i for i in response.report.issues if i.rule == "broken-reference-link"]
        assert len(broken) == 0

    def test_broken_example_detected_via_path(self, tmp_path: Path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""\
---
name: test-skill
description: |
  A test skill. Triggers on: test, validate.
---

## Principles

- Be thorough

## Examples

- [Sample output](examples/output.json)
""", encoding="utf-8")

        lint = LintSkill(parser=MarkdownSkillParser())
        request = LintSkillRequest(path=skill_md)
        response = lint.execute(request)

        broken = [i for i in response.report.issues if i.rule == "broken-example-link"]
        assert len(broken) == 1

    def test_full_featured_skill_roundtrip_lint(
        self, tmp_path: Path, full_featured_skill: Skill,
    ):
        """Render a full-featured skill, write to disk, create all files, lint clean."""
        renderer = MarkdownSkillRenderer()
        md_content = renderer.render_skill_md(full_featured_skill)

        skill_dir = tmp_path / "eval-runner"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(md_content, encoding="utf-8")

        # Create all referenced files
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "scoring-guide.md").write_text("# Guide\n")
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "generate_report.py").write_text("print('ok')\n")
        (skill_dir / "scripts" / "validate_output.py").write_text("print('ok')\n")
        (skill_dir / "examples").mkdir()
        (skill_dir / "examples" / "sample-eval.json").write_text("{}\n")
        (skill_dir / "assets").mkdir()
        (skill_dir / "assets" / "thresholds.csv").write_text("a,b\n")

        lint = LintSkill(parser=MarkdownSkillParser())
        request = LintSkillRequest(path=skill_dir / "SKILL.md")
        response = lint.execute(request)

        # No broken links
        broken = [
            i for i in response.report.issues
            if i.rule.startswith("broken-")
        ]
        assert len(broken) == 0, f"Broken links found: {broken}"
