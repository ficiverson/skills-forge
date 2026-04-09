"""System-prompt exporter.

Strips YAML frontmatter and prepends a concise role declaration built from
the skill's ``description`` field.  The output is plain Markdown that can be
pasted into the system-prompt / custom-instructions field of any chat UI:
Claude.ai, ChatGPT, Google Gemini, Mistral Le Chat, Cohere Coral, etc.
"""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter


class SystemPromptExporter(SkillExporter):
    """Export a skill as a plain-Markdown system prompt.

    Output filename: ``<name>.system-prompt.md``
    """

    format = ExportFormat.SYSTEM_PROMPT

    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        role_line = (
            f"You are a specialist assistant for **{skill.identity.name}**.\n"
            f"{skill.description.text.strip()}\n"
        )

        content = "\n".join(
            [
                role_line,
                "---",
                "",
                body,
            ]
        )

        out = output_dir / f"{skill.identity.slug}.system-prompt.md"
        out.write_text(content, encoding="utf-8")
        return out
