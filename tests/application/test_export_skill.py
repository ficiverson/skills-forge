"""Tests for the ExportSkill use case."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_forge.application.use_cases.export_skill import (
    ExportSkill,
    ExportSkillRequest,
    _strip_frontmatter,
)
from skill_forge.domain.model import ExportFormat, Skill, SkillPackManifest, SkillRef
from skill_forge.domain.ports import SkillExporter, SkillPacker
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


class _StubPacker(SkillPacker):
    """Stub that pretends to unpack a pack into a directory."""

    def __init__(self, skill_mds: list[Path]) -> None:
        self.skill_mds = skill_mds
        self.calls: list[tuple[Path, Path]] = []

    def pack(self, skill_dirs: list[Path], manifest: SkillPackManifest, output: Path) -> Path:
        return output

    def unpack(self, pack_path: Path, dest_dir: Path) -> SkillPackManifest:
        self.calls.append((pack_path, dest_dir))
        # Create the skill files so the rglob in ExportSkill finds them
        for i, _md_path in enumerate(self.skill_mds):
            skill_dir = dest_dir / f"skill-{i}"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(_FULL_SKILL_MD, encoding="utf-8")

        refs = [
            SkillRef(category="dev", name=f"skill-{i}") for i in range(len(self.skill_mds))
        ]
        return SkillPackManifest(
            name="test-pack",
            version="1.0.0",
            author="test",
            created_at="2024-01-01T00:00:00Z",
            skills=tuple(refs),
        )

    def read_manifest(self, pack_path: Path) -> SkillPackManifest:
        raise NotImplementedError()


# ── ExportSkill use case ──────────────────────────────────────────────────────


class TestExportSkillUseCase:
    def _make_use_case(self, exporter: SkillExporter, packer: SkillPacker | None = None) -> ExportSkill:
        return ExportSkill(
            parser=MarkdownSkillParser(),
            exporter=exporter,
            packer=packer or _StubPacker([]),
        )

    def test_calls_exporter(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker([skill_dir / "SKILL.md"])
        use_case = self._make_use_case(exporter, packer)

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        assert len(exporter.calls) == 1

    def test_exporter_receives_parsed_skill(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker([skill_dir / "SKILL.md"])
        use_case = self._make_use_case(exporter, packer)

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        skill, _body, _out = exporter.calls[0]
        assert skill.identity.name == "sprint-grooming"

    def test_exporter_receives_stripped_body(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker([skill_dir / "SKILL.md"])
        use_case = self._make_use_case(exporter, packer)

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        _skill, body, _out = exporter.calls[0]
        assert "## Workflow" in body
        assert "name: sprint-grooming" not in body

    def test_default_output_for_pack_is_current_dir(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker([skill_dir / "SKILL.md"])
        use_case = self._make_use_case(exporter, packer)

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        _skill, _body, out = exporter.calls[0]
        # Now defaults to ./test/
        assert out == Path("test")

    def test_explicit_output_overrides_default(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        custom_out = tmp_path / "exports"
        exporter = _RecordingExporter()
        packer = _StubPacker([skill_dir / "SKILL.md"])
        use_case = self._make_use_case(exporter, packer)

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
                output=custom_out,
            )
        )
        _skill, _body, out = exporter.calls[0]
        # Now overrides to custom_out / test
        assert out == custom_out / "test"

    def test_response_contains_list_of_output_paths(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker([skill_dir / "SKILL.md"])
        use_case = self._make_use_case(exporter, packer)

        resp = use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        assert len(resp.output_paths) == 1
        assert resp.output_paths[0].name == "exported.md"

    def test_response_format_matches_request(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker([skill_dir / "SKILL.md"])
        use_case = self._make_use_case(exporter, packer)

        resp = use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        assert resp.format == ExportFormat.SYSTEM_PROMPT

    def test_raises_value_error_for_direct_directory(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skill")
        exporter = _RecordingExporter()
        use_case = self._make_use_case(exporter)
        with pytest.raises(ValueError, match="requires a .skillpack archive"):
            use_case.execute(
                ExportSkillRequest(
                    skill_path=skill_dir,
                    format=ExportFormat.SYSTEM_PROMPT,
                )
            )

    def test_multi_skill_pack_exports_all(self, tmp_path: Path) -> None:
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        # StubPacker will "create" two skills on unpack
        packer = _StubPacker([Path("dummy1"), Path("dummy2")])
        use_case = self._make_use_case(exporter, packer)
        
        resp = use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
            )
        )
        
        assert len(resp.output_paths) == 2
        assert len(exporter.calls) == 2
