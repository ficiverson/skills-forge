"""Export skill use case.

Renders a local skill directory into a platform-native export format
suitable for chatbot / API platforms (OpenAI Custom GPT, Gemini Gems,
AWS Bedrock, MCP hosts) that have no native SKILL.md skill directory.

For agent-CLI tools (Claude Code, Gemini CLI, Codex, VS Code Copilot)
that *do* support SKILL.md natively, use ``install --target`` instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter, SkillPacker, SkillParser

# ── helpers ──────────────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def _strip_frontmatter(raw: str) -> str:
    """Return the SKILL.md body with YAML frontmatter removed."""
    return _FRONTMATTER_RE.sub("", raw, count=1).strip()


# ── request / response DTOs ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ExportSkillRequest:
    """Parameters for the export use case."""

    skill_path: Path
    """Local path to the skill directory (or SKILL.md file)."""

    format: ExportFormat
    """Which export format to render."""

    output: Path | None = None
    """Directory where the exported artifact(s) should be written.
    Defaults to the skill directory itself."""

    bundle: bool = True
    """Whether to bundle linked references, examples, etc. into the output."""


@dataclass(frozen=True)
class ExportSkillResponse:
    """Result of a successful export."""

    output_paths: list[Path]
    """Paths of the artifacts created (files or directories)."""

    format: ExportFormat
    """Format that was applied."""


# ── use case ─────────────────────────────────────────────────────────────────


class ExportSkill:
    """Parse a skill and render it in a platform-native export format.

    Dependencies are injected so each layer stays testable in isolation:

    - ``parser``   — ``SkillParser`` port (markdown_parser in production)
    - ``exporter`` — ``SkillExporter`` port; the factory picks the concrete
                     implementation based on ``ExportSkillRequest.format``
    """

    def __init__(
        self, parser: SkillParser, exporter: SkillExporter, packer: SkillPacker
    ) -> None:
        self._parser = parser
        self._exporter = exporter
        self._packer = packer

    def execute(self, request: ExportSkillRequest) -> ExportSkillResponse:
        if request.skill_path.suffix != ".skillpack":
            raise ValueError(
                f"Invalid source: '{request.skill_path}'. "
                "The export command now requires a .skillpack archive as input. "
                "Run `skills-forge pack` first to bundle your skill into a pack."
            )

        return self._handle_skillpack(request)

    def _export_one(
        self,
        skill_md: Path,
        output_dir_override: Path | None,
        bundle: bool = True,
    ) -> Path:
        raw = skill_md.read_text(encoding="utf-8")
        skill = self._parser.parse(raw, skill_md.parent)
        body = _strip_frontmatter(raw)

        if bundle:
            # Bundle supplements (references, examples, etc.)
            supplements = self._bundle_supplements(skill, skill_md.parent)
            if supplements:
                body = f"{body.strip()}\n\n{supplements}"

        output_dir = output_dir_override or skill_md.parent
        return self._exporter.export(skill, body, output_dir)

    def _bundle_supplements(self, skill: Skill, root: Path) -> str:
        """Bundle all referenced AND local supplemental files into a single string."""
        sections: list[str] = []
        bundled_paths: set[str] = set()

        # We collect paths from two sources:
        # 1. Explicitly linked items in the Skill model (preserves order)
        # 2. Standard directories on disk (catches everything else)

        # Source 1: Explicitly linked items
        links: list[Any] = []
        links.extend(skill.references)
        links.extend(skill.examples)
        links.extend(skill.assets)
        links.extend(skill.scripts)

        for item in links:
            rel_path = str(item.path)
            if rel_path in bundled_paths:
                continue

            section = self._read_supplement_section(root, rel_path)
            if section:
                sections.append(section)
                bundled_paths.add(rel_path)

        # Source 2: Standard directories (auto-discovery)
        for subdir in ["references", "examples", "assets", "scripts"]:
            dir_path = root / subdir
            if not dir_path.is_dir():
                continue

            # Sort files for deterministic output
            for file_path in sorted(dir_path.rglob("*")):
                if not file_path.is_file():
                    continue

                rel_path = file_path.relative_to(root).as_posix()
                if rel_path in bundled_paths:
                    continue

                section = self._read_supplement_section(root, rel_path)
                if section:
                    sections.append(section)
                    bundled_paths.add(rel_path)

        if not sections:
            return ""

        return "\n\n".join(
            [
                "---",
                "# BUNDLED SUPPLEMENTS",
                "The following sections contain the full content of files referenced "
                "in the skill.",
                "",
                *sections,
            ]
        )

    def _read_supplement_section(self, root: Path, rel_path: str) -> str | None:
        """Read a file and wrap it in a markdown supplement section."""
        file_path = root / rel_path
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8")
            # Use the file extension for syntax highlighting in the block
            ext = file_path.suffix.lstrip(".") or "text"

            return (
                f"## Supplement: {rel_path}\n"
                f"\n"
                f"``` {ext}\n"
                f"{content.strip()}\n"
                f"```"
            )
        except (UnicodeDecodeError, OSError):
            # Skip binary files or unreadable files
            return None

    def _handle_skillpack(self, request: ExportSkillRequest) -> ExportSkillResponse:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            self._packer.unpack(request.skill_path, tmp_path)

            # Find all SKILL.md files in the unpacked pack
            skill_mds = list(tmp_path.rglob("SKILL.md"))
            if not skill_mds:
                raise FileNotFoundError(
                    f"No skills found inside pack '{request.skill_path.name}'"
                )

            output_base = (request.output or Path(".")) / request.skill_path.stem
            output_base.mkdir(parents=True, exist_ok=True)

            output_paths: list[Path] = []
            for skill_md in skill_mds:
                # When exporting from a pack, we MUST have an output directory
                # specified, otherwise they'd land in the temp dir and be deleted.
                path = self._export_one(
                    skill_md, output_base, bundle=request.bundle
                )
                output_paths.append(path)

            return ExportSkillResponse(output_paths=output_paths, format=request.format)
