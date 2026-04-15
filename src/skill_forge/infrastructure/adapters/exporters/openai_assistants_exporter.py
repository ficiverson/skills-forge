"""OpenAI Assistants API exporter.

Produces an OpenAI Assistants API ``CreateAssistant``-compatible JSON
configuration.  The ``instructions`` field contains the full skill body.
When the skill declares ``allowed-tools``, stub function tool definitions
are included; when it does not, the ``tools`` array defaults to an empty
list (no code_interpreter or file_search unless the caller adds them).

Output filename: ``<slug>.assistants.json``

Usage
-----
Create an assistant via the REST API:

  POST https://api.openai.com/v1/assistants
  Content-Type: application/json
  OpenAI-Beta: assistants=v2
  Authorization: Bearer $OPENAI_API_KEY

  {
    "model": "gpt-4o",
    "instructions": "...",
    "tools": [...],
    ...
  }

Or via the Python SDK:

  from openai import OpenAI
  import json
  client = OpenAI()
  cfg = json.load(open("<slug>.assistants.json"))
  assistant = client.beta.assistants.create(**cfg["assistant_config"])

Reference: https://platform.openai.com/docs/api-reference/assistants/createAssistant
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter


class OpenAIAssistantsExporter(SkillExporter):
    """Export a skill as an OpenAI Assistants API configuration JSON."""

    format = ExportFormat.OPENAI_ASSISTANTS

    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        instructions = (
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
                            "strict": False,
                        },
                    }
                )

        assistant_config: dict[str, object] = {
            "model": "gpt-4o",
            "name": skill.identity.name,
            "description": skill.description.text.strip()[:512],  # API limit
            "instructions": instructions,
            "tools": tools,
            "metadata": {
                "source": "skills-forge",
                "version": skill.version,
                "category": skill.identity.category,
            },
            "response_format": "auto",
            "temperature": 1.0,
            "top_p": 1.0,
        }

        config = {
            "schema_version": "v1",
            "assistant_config": assistant_config,
        }

        out = output_dir / f"{skill.identity.slug}.assistants.json"
        out.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
