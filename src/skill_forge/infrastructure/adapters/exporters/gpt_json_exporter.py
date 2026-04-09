"""GPT-JSON exporter.

Produces an OpenAI Custom GPT / Assistants API configuration JSON file.
The ``instructions`` field combines the role declaration with the full
SKILL.md body.  Knowledge files and capabilities are left at safe defaults;
the caller can edit the JSON before importing.

Output filename: ``<name>.gpt.json``

Usage
-----
Custom GPT (GPT Builder):
  1. Open https://chatgpt.com/gpts/editor
  2. Paste the ``instructions`` string into the "Instructions" textarea in
     the Configure tab.
  3. (Optional) Upload reference files listed in ``knowledge_files``.

Assistants API:
  ``POST /v1/assistants  { "instructions": "<value>", ... }``
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter


class GptJsonExporter(SkillExporter):
    """Export a skill as an OpenAI Custom GPT configuration JSON."""

    format = ExportFormat.GPT_JSON

    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        instructions = (
            f"You are a specialist assistant for {skill.identity.name}.\n"
            f"{skill.description.text.strip()}\n\n"
            f"---\n\n"
            f"{body}"
        )

        config = {
            "schema_version": "v1",
            "name": skill.identity.name,
            "description": skill.description.text.strip(),
            "instructions": instructions,
            "knowledge_files": [
                str(ref.path) for ref in skill.references
            ],
            "capabilities": {
                "code_interpreter": False,
                "browsing": False,
                "dalle": False,
            },
            "metadata": {
                "source": "skills-forge",
                "version": skill.version,
                "category": skill.identity.category,
            },
        }

        out = output_dir / f"{skill.identity.slug}.gpt.json"
        out.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
