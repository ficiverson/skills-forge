"""Gem-TXT exporter.

Produces a plain-text instructions file for Google Gemini Gems.
A Gem is a customised Gemini persona created at https://gemini.google.com/gems.
The "Instructions" field accepts plain text (not Markdown, though headings
render in the preview).

The output follows Google's recommended Gem instructions structure:
1. Persona / role statement
2. Core task description
3. Detailed workflow (from the SKILL.md body)
4. Response format guidance

Output filename: ``<name>.gem.txt``

Usage
-----
1. Go to https://gemini.google.com/gems → "New Gem"
2. Paste the contents of this file into the "Instructions" textarea.
3. (Optional) Upload up to 10 reference files from the skill's
   ``references/`` directory as knowledge files.
4. Name the Gem and save.
"""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter


class GemTxtExporter(SkillExporter):
    """Export a skill as Google Gemini Gem instructions text."""

    format = ExportFormat.GEM_TXT

    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        gem_name = skill.identity.name.replace("-", " ").title()

        content = "\n".join(
            [
                f"[Gem: {gem_name}]",
                "",
                f"Role: You are {gem_name}, a specialist assistant "
                f"for {skill.identity.category} workflows.",
                "",
                "Activation: "
                + skill.description.text.strip().replace("\n", " "),
                "",
                "---",
                "",
                body,
                "",
                "---",
                "",
                "Always respond in clear, actionable language. "
                "If the user's request is outside your specialty, "
                "acknowledge the limit and redirect them to the relevant workflow above.",
            ]
        )

        out = output_dir / f"{skill.identity.slug}.gem.txt"
        out.write_text(content, encoding="utf-8")
        return out
