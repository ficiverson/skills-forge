"""Mistral Agents JSON exporter.

Produces a Mistral Agents API configuration JSON file.  The ``system``
field contains the full skill body.  When the skill declares
``allowed-tools``, a stub ``tools`` array is included so the caller can
flesh out each tool's input schema before deploying.

Output filename: ``<slug>.mistral.json``

Usage
-----
Create a Mistral Agent via the API or Le Chat Agents UI:

  POST https://api.mistral.ai/v1/agents
  Content-Type: application/json
  Authorization: Bearer $MISTRAL_API_KEY

  {
    "name": "...",
    "model": "mistral-medium-latest",
    "instructions": "<system value>",
    ...
  }

Reference: https://docs.mistral.ai/capabilities/agents/
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter


class MistralJsonExporter(SkillExporter):
    """Export a skill as a Mistral Agents API configuration JSON."""

    format = ExportFormat.MISTRAL_JSON

    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        system_prompt = (
            f"You are a specialist assistant for {skill.identity.name}.\n"
            f"{skill.description.text.strip()}\n\n"
            f"---\n\n"
            f"{body}"
        )

        tools: list[dict[str, object]] = []
        if skill.has_allowed_tools:
            for tool_name in skill.allowed_tools:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": f"Tool: {tool_name}",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": [],
                            },
                        },
                    }
                )

        config: dict[str, object] = {
            "schema_version": "v1",
            "name": skill.identity.name,
            "model": "mistral-medium-latest",
            "system": system_prompt,
            "metadata": {
                "source": "skills-forge",
                "version": skill.version,
                "category": skill.identity.category,
                "description": skill.description.text.strip(),
            },
        }
        if tools:
            config["tools"] = tools

        out = output_dir / f"{skill.identity.slug}.mistral.json"
        out.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
