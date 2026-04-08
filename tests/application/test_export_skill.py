"""Tests for the ExportSkill use case."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_forge.application.use_cases.export_skill import (
    ExportSkill,
    ExportSkillRequest,
    _strip_frontmatter,
)
from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

# ── helpers ───────────────────────────────────────────────────────────────────


_FRONTMATTER = """\
---
name: sprint-grooming
description: |
  Convert ideas to user stories.
---
"""

_BODY_ONLY = "## Workflow\n\nStep 1: do it.\n"
_FULL_SKILL_MD = _FRONTMATTER + _BODY_ONLY


def _make_skill_dir(tmp_path: Path, content: str = _FULL_SKILL_MD) -> Path:
    """Create a skill directory with a SKILL.md and return it."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "SKILL.md").write_text(content, encoding="utf-8")
    return tmp_path


# ── _strip_frontmatter ────────────────────────────────────────────────────────


class TestStripFrontmatter:
    def test_strips_frontmatter(self) -> None:
        result = _strip_frontmatter(_FULL_SKILL_MD)
        assert "---" not in result
        assert "## Workflow" in result

    def test_no_frontmatter_returns_unchanged(self) -> None:
        text = "## Just a body\n\nSome content.\n"
        result = _strip_frontmatter(text)
        assert "## Just a body" in result

    def test_strips_only_leading_frontmatter(self) -> None:
        content = "---\nname: x\n---\n## Body\n---\nstill body\n"
        result = _strip_frontmatter(content)
        assert "---" in result  # the trailing --- is kept
        assert "name: x" not in result


# ── stub ──────────────────────────────────────────────────────────────────────


class _RecordingExporter(SkillExporter):
    """Stub that records calls and writes a sentinel file."""

    format = ExportFormat.SYSTEM_PROMPT

    def __init__(self) -> None:
        self.calls: list[tuple[Skill, str, Path]] = []

    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        self.calls.append((skill, body, output_dir))
        sentinel = output_dir / "exported.md"
        output_dir.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("ok", encoding="utf-8")
        return sentinel


# ── ExportSkill use case ──────────────────────────────────────────────────────


class TestExportSkillUseCase:
    def _make_use_case(self, exporter: SkillExporter) -> ExportSkill:
        return ExportSkill(parser=MarkdownSkillParser(), exporter=exporter)

    def test_calls_exporter(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        use_case.execute(
            ExportSkillRequest(
                skill_path=skill_dir,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        assert len(exporter.calls) == 1

    def test_exporter_receives_parsed_skill(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        use_case.execute(
            ExportSkillRequest(
                skill_path=skill_dir,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        skill, _body, _out = exporter.calls[0]
        assert skill.identity.name == "sprint-grooming"

    def test_exporter_receives_stripped_body(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        use_case.execute(
            ExportSkillRequest(
                skill_path=skill_dir,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        _skill, body, _out = exporter.calls[0]
        assert "## Workflow" in body
        assert "name: sprint-grooming" not in body

    def test_default_output_is_skill_dir(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        use_case.execute(
            ExportSkillRequest(
                skill_path=skill_dir,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        _skill, _body, out = exporter.calls[0]
        assert out == skill_dir

    def test_explicit_output_overrides_default(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        custom_out = tmp_path / "exports"
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        use_case.execute(
            ExportSkillRequest(
                skill_path=skill_dir,
                format=ExportFormat.SYSTEM_PROMPT,
                output=custom_out,
            )
        )
        _skill, _body, out = exporter.calls[0]
        assert out == custom_out

    def test_response_contains_output_path(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        resp = use_case.execute(
            ExportSkillRequest(
                skill_path=skill_dir,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        assert resp.output_path.name == "exported.md"

    def test_response_format_matches_request(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        resp = use_case.execute(
            ExportSkillRequest(
                skill_path=skill_dir,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        assert resp.format == ExportFormat.SYSTEM_PROMPT

    def test_accepts_skill_md_file_directly(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        skill_md = skill_dir / "SKILL.md"
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        resp = use_case.execute(
            ExportSkillRequest(
                skill_path=skill_md,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        assert resp.output_path.exists()

    def test_raises_file_not_found_for_missing_skill_md(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        with pytest.raises(FileNotFoundError):
            use_case.execute(
                ExportSkillRequest(
                    skill_path=empty,
                    format=ExportFormat.SYSTEM_PROMPT,
                )
            )
