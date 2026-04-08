"""Tests for the ExportSkill supplement bundling logic."""

from __future__ import annotations

from pathlib import Path
import pytest
from unittest.mock import patch

from skill_forge.application.use_cases.export_skill import (
    ExportSkill,
    ExportSkillRequest,
)
from skill_forge.domain.model import ExportFormat, Skill, SkillPackManifest, SkillRef
from skill_forge.domain.ports import SkillExporter, SkillPacker
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

# ── helpers ───────────────────────────────────────────────────────────────────

_SKILL_MD = """\
---
name: bundle-test
description: test
---
## References
- [Guide](references/guide.md)
## Examples
- [Sample](examples/sample.json)
"""

def _make_skill_structure(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_text(_SKILL_MD, encoding="utf-8")
    
    ref_dir = root / "references"
    ref_dir.mkdir()
    (ref_dir / "guide.md").write_text("Reference content", encoding="utf-8")
    
    ex_dir = root / "examples"
    ex_dir.mkdir()
    (ex_dir / "sample.json").write_text('{"test": true}', encoding="utf-8")
    
    return root

class _RecordingExporter(SkillExporter):
    format = ExportFormat.SYSTEM_PROMPT
    def __init__(self) -> None:
        self.recorded_body: str | None = None
    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        self.recorded_body = body
        output_dir.mkdir(parents=True, exist_ok=True)
        out = output_dir / "out.md"
        out.write_text(body, encoding="utf-8")
        return out

class _StubPacker(SkillPacker):
    def __init__(self, skill_root: Path) -> None:
        self.skill_root = skill_root
    def pack(self, skill_dirs: list[Path], manifest: SkillPackManifest, output: Path) -> Path:
        return output
    def unpack(self, pack_path: Path, dest_dir: Path) -> SkillPackManifest:
        # Simulate unpacking our prepared skill root into dest_dir
        import shutil
        shutil.copytree(self.skill_root, dest_dir, dirs_exist_ok=True)
        return SkillPackManifest(
            name="test", version="1.0.0", author="me", created_at="2024",
            skills=(SkillRef(category="test", name="bundle-test"),)
        )
    def read_manifest(self, pack_path: Path) -> SkillPackManifest:
        raise NotImplementedError()

# ── Tests ──────────────────────────────────────────────────────────────────────

class TestExportSkillBundling:
    def test_bundles_references_and_examples(self, tmp_path: Path):
        skill_root = _make_skill_structure(tmp_path / "source")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker(skill_root)
        use_case = ExportSkill(
            parser=MarkdownSkillParser(),
            exporter=exporter,
            packer=packer
        )

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
                output=tmp_path / "out"
            )
        )

        body = exporter.recorded_body
        assert body is not None
        assert "# BUNDLED SUPPLEMENTS" in body
        assert "## Supplement: references/guide.md" in body
        assert "Reference content" in body
        assert "## Supplement: examples/sample.json" in body
        assert '{"test": true}' in body
        assert "``` md" in body
        assert "``` json" in body

    def test_handles_missing_files_gracefully(self, tmp_path: Path):
        # Create SKILL.md but no supporting files
        skill_root = tmp_path / "source"
        skill_root.mkdir()
        (skill_root / "SKILL.md").write_text(_SKILL_MD, encoding="utf-8")
        
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker(skill_root)
        use_case = ExportSkill(
            parser=MarkdownSkillParser(),
            exporter=exporter,
            packer=packer
        )

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
                output=tmp_path / "out"
            )
        )

        body = exporter.recorded_body
        assert body is not None
        assert "# BUNDLED SUPPLEMENTS" not in body

    def test_bundles_scripts_and_assets(self, tmp_path: Path):
        skill_md = _SKILL_MD + "## Scripts\n- [Run](scripts/run.py)\n## Assets\n- [Data](assets/data.csv)\n"
        skill_root = tmp_path / "source"
        skill_root.mkdir()
        (skill_root / "SKILL.md").write_text(skill_md, encoding="utf-8")
        
        (skill_root / "scripts").mkdir()
        (skill_root / "scripts" / "run.py").write_text("print('hi')", encoding="utf-8")
        (skill_root / "assets").mkdir()
        (skill_root / "assets" / "data.csv").write_text("a,b,c", encoding="utf-8")

        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker(skill_root)
        use_case = ExportSkill(
            parser=MarkdownSkillParser(),
            exporter=exporter,
            packer=packer
        )

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
                output=tmp_path / "out"
            )
        )

        body = exporter.recorded_body
        assert "## Supplement: scripts/run.py" in body
        assert "print('hi')" in body
        assert "## Supplement: assets/data.csv" in body
        assert "a,b,c" in body

    def test_skips_bundling_when_requested(self, tmp_path: Path):
        skill_root = _make_skill_structure(tmp_path / "source")
        pack_path = tmp_path / "test.skillpack"
        pack_path.touch()

        exporter = _RecordingExporter()
        packer = _StubPacker(skill_root)
        use_case = ExportSkill(
            parser=MarkdownSkillParser(),
            exporter=exporter,
            packer=packer
        )

        use_case.execute(
            ExportSkillRequest(
                skill_path=pack_path,
                format=ExportFormat.SYSTEM_PROMPT,
                output=tmp_path / "out",
                bundle=False
            )
        )

        body = exporter.recorded_body
        assert body is not None
        assert "# BUNDLED SUPPLEMENTS" not in body
        assert "Reference content" not in body
