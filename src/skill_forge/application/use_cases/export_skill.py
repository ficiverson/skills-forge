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

from skill_forge.domain.model import ExportFormat
from skill_forge.domain.ports import SkillExporter, SkillParser

# ── helpers ──────────────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)


def _strip_frontmatter(raw: str) -> str:
    """Return the SKILL.md body with YAML frontmatter removed."""
    return _FRONTMATTER_RE.sub("", raw, count=1).strip()


def _find_skill_md(skill_path: Path) -> Path:
    """Resolve path to the SKILL.md file inside ``skill_path``.

    Accepts either a direct path to ``SKILL.md`` or a skill directory that
    contains one.
    """
    if skill_path.is_file() and skill_path.name == "SKILL.md":
        return skill_path
    candidate = skill_path / "SKILL.md"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"No SKILL.md found at '{skill_path}'. "
        "Pass either the skill directory or the SKILL.md file directly."
    )


# ── request / response DTOs ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ExportSkillRequest:
    """Parameters for the export use case."""

    skill_path: Path
    """Local path to the skill directory (or SKILL.md file)."""

    format: ExportFormat
    """Which export format to render."""

    output: Path | None = None
    """Directory where the exported artifact should be written.
    Defaults to the skill directory itself."""


@dataclass(frozen=True)
class ExportSkillResponse:
    """Result of a successful export."""

    output_path: Path
    """Path of the artifact created (file or directory)."""

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

    def __init__(self, parser: SkillParser, exporter: SkillExporter) -> None:
        self._parser = parser
        self._exporter = exporter

    def execute(self, request: ExportSkillRequest) -> ExportSkillResponse:
        skill_md = _find_skill_md(request.skill_path)
        raw = skill_md.read_text(encoding="utf-8")

        # Parse the frontmatter → domain Skill object (name, description, …)
        skill = self._parser.parse(raw, skill_md.parent)

        # Extract body (everything below the opening frontmatter block)
        body = _strip_frontmatter(raw)

        # Output directory: explicit arg > skill directory
        output_dir = request.output or skill_md.parent

        artifact = self._exporter.export(skill, body, output_dir)

        return ExportSkillResponse(output_path=artifact, format=request.format)
