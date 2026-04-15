"""Vertex AI / Gemini API exporter.

Produces a Gemini API ``GenerateContentRequest``-compatible JSON config
with a ``system_instruction`` field.  This format is accepted by both the
Gemini Developer API and the Vertex AI ``generateContent`` endpoint.

Output filename: ``<slug>.gemini-api.json``

Usage
-----
Gemini Developer API (google.generativeai SDK):

  import google.generativeai as genai, json
  cfg = json.load(open("<slug>.gemini-api.json"))
  model = genai.GenerativeModel(
      model_name=cfg["model"],
      system_instruction=cfg["system_instruction"]["parts"][0]["text"],
  )

Vertex AI REST:

  POST https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/
       locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent

  Body: { "system_instruction": { "parts": [...] }, "contents": [...] }

Reference: https://ai.google.dev/api/generate-content#v1beta.GenerateContentRequest
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.domain.ports import SkillExporter


class GeminiApiExporter(SkillExporter):
    """Export a skill as a Vertex AI / Gemini API system instruction JSON."""

    format = ExportFormat.GEMINI_API

    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)

        system_text = (
            f"You are a specialist assistant for {skill.identity.name}.\n"
            f"{skill.description.text.strip()}\n\n"
            f"---\n\n"
            f"{body}"
        )

        config: dict[str, object] = {
            "schema_version": "v1",
            "model": "gemini-2.0-flash",
            "system_instruction": {
                "parts": [{"text": system_text}],
            },
            "generation_config": {
                "temperature": 1.0,
                "top_p": 0.95,
                "max_output_tokens": 8192,
            },
            "metadata": {
                "source": "skills-forge",
                "version": skill.version,
                "category": skill.identity.category,
                "name": skill.identity.name,
                "description": skill.description.text.strip(),
            },
        }

        # Include allowed_tools as function declarations when present
        if skill.has_allowed_tools:
            config["tools"] = [
                {
                    "function_declarations": [
                        {
                            "name": tool_name,
                            "description": f"Tool: {tool_name}",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                            },
                        }
                        for tool_name in skill.allowed_tools
                    ]
                }
            ]

        out = output_dir / f"{skill.identity.slug}.gemini-api.json"
        out.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        return out
