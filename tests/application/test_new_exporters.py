"""Tests for the three new v0.6.0 export formats:
  - mistral-json  (MistralJsonExporter)
  - gemini-api    (GeminiApiExporter)
  - openai-assistants (OpenAIAssistantsExporter)

Also tests the allowed-tools roundtrip (parser → model → renderer → parser).
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.domain.model import (
    Description,
    ExportFormat,
    Skill,
    SkillContent,
    SkillIdentity,
)
from skill_forge.infrastructure.adapters.exporters.gemini_api_exporter import (
    GeminiApiExporter,
)
from skill_forge.infrastructure.adapters.exporters.mistral_json_exporter import (
    MistralJsonExporter,
)
from skill_forge.infrastructure.adapters.exporters.openai_assistants_exporter import (
    OpenAIAssistantsExporter,
)
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_skill(
    name: str = "sprint-grooming",
    category: str = "productivity",
    description: str = "Plan sprint work.",
    version: str = "1.0.0",
    body: str = "## Instructions\n\nDo the sprint work.",
    allowed_tools: list[str] | None = None,
) -> tuple[Skill, str]:
    """Return a (Skill, body_text) pair."""
    skill = Skill(
        identity=SkillIdentity(name=name, category=category),
        description=Description(text=description),
        version=version,
        content=SkillContent(instructions=body),
        allowed_tools=allowed_tools or [],
    )
    return skill, body


# ── ExportFormat enum ─────────────────────────────────────────────────────────


class TestExportFormatEnum:
    def test_mistral_json_value(self) -> None:
        assert ExportFormat.MISTRAL_JSON.value == "mistral-json"

    def test_gemini_api_value(self) -> None:
        assert ExportFormat.GEMINI_API.value == "gemini-api"

    def test_openai_assistants_value(self) -> None:
        assert ExportFormat.OPENAI_ASSISTANTS.value == "openai-assistants"

    def test_all_formats_roundtrip(self) -> None:
        for fmt in ExportFormat:
            assert ExportFormat(fmt.value) == fmt


# ── MistralJsonExporter ───────────────────────────────────────────────────────


class TestMistralJsonExporter:
    def test_format_attribute(self) -> None:
        assert MistralJsonExporter.format == ExportFormat.MISTRAL_JSON

    def test_creates_output_file(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = MistralJsonExporter().export(skill, body, tmp_path)
        assert out.exists()
        assert out.suffix == ".json"
        assert out.name == "sprint-grooming.mistral.json"

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = MistralJsonExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_system_field_contains_body(self, tmp_path: Path) -> None:
        skill, body = _make_skill(body="## Instructions\n\nDo the sprint work.")
        out = MistralJsonExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "system" in data
        assert "sprint-grooming" in data["system"]

    def test_no_tools_field_when_no_allowed_tools(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = MistralJsonExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "tools" not in data

    def test_tools_field_populated_from_allowed_tools(self, tmp_path: Path) -> None:
        skill, body = _make_skill(allowed_tools=["Bash", "Read"])
        out = MistralJsonExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "tools" in data
        tool_names = [t["function"]["name"] for t in data["tools"]]
        assert "Bash" in tool_names
        assert "Read" in tool_names

    def test_model_field_present(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = MistralJsonExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "model" in data

    def test_metadata_version(self, tmp_path: Path) -> None:
        skill, body = _make_skill(version="2.3.1")
        out = MistralJsonExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["metadata"]["version"] == "2.3.1"

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        nested = tmp_path / "deep" / "exports"
        MistralJsonExporter().export(skill, body, nested)
        assert nested.exists()


# ── GeminiApiExporter ─────────────────────────────────────────────────────────


class TestGeminiApiExporter:
    def test_format_attribute(self) -> None:
        assert GeminiApiExporter.format == ExportFormat.GEMINI_API

    def test_creates_output_file(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = GeminiApiExporter().export(skill, body, tmp_path)
        assert out.exists()
        assert out.name == "sprint-grooming.gemini-api.json"

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = GeminiApiExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_system_instruction_field_present(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = GeminiApiExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "system_instruction" in data
        assert "parts" in data["system_instruction"]
        assert len(data["system_instruction"]["parts"]) == 1
        assert "text" in data["system_instruction"]["parts"][0]

    def test_system_instruction_contains_body(self, tmp_path: Path) -> None:
        skill, body = _make_skill(body="Step by step process.")
        out = GeminiApiExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "Step by step process." in data["system_instruction"]["parts"][0]["text"]

    def test_no_tools_when_no_allowed_tools(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = GeminiApiExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "tools" not in data

    def test_tools_populated_from_allowed_tools(self, tmp_path: Path) -> None:
        skill, body = _make_skill(allowed_tools=["WebSearch", "Read"])
        out = GeminiApiExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "tools" in data
        function_names = [fd["name"] for t in data["tools"] for fd in t["function_declarations"]]
        assert "WebSearch" in function_names
        assert "Read" in function_names

    def test_generation_config_present(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = GeminiApiExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "generation_config" in data

    def test_model_field_present(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = GeminiApiExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "model" in data


# ── OpenAIAssistantsExporter ──────────────────────────────────────────────────


class TestOpenAIAssistantsExporter:
    def test_format_attribute(self) -> None:
        assert OpenAIAssistantsExporter.format == ExportFormat.OPENAI_ASSISTANTS

    def test_creates_output_file(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        assert out.exists()
        assert out.name == "sprint-grooming.assistants.json"

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_assistant_config_key_present(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "assistant_config" in data

    def test_instructions_contains_body(self, tmp_path: Path) -> None:
        skill, body = _make_skill(body="Run the retrospective process.")
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "Run the retrospective process." in data["assistant_config"]["instructions"]

    def test_empty_tools_when_no_allowed_tools(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["assistant_config"]["tools"] == []

    def test_tools_populated_from_allowed_tools(self, tmp_path: Path) -> None:
        skill, body = _make_skill(allowed_tools=["Bash", "Write"])
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        tools = data["assistant_config"]["tools"]
        names = [t["function"]["name"] for t in tools]
        assert "Bash" in names
        assert "Write" in names

    def test_model_field_present(self, tmp_path: Path) -> None:
        skill, body = _make_skill()
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "model" in data["assistant_config"]

    def test_description_truncated_to_512_chars(self, tmp_path: Path) -> None:
        long_desc = "A" * 1000
        skill, body = _make_skill(description=long_desc)
        out = OpenAIAssistantsExporter().export(skill, body, tmp_path)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data["assistant_config"]["description"]) <= 512


# ── allowed-tools parser ──────────────────────────────────────────────────────


class TestAllowedToolsParsing:
    def test_inline_list_parsed(self) -> None:
        md = "---\nname: x\ndescription: y\nallowed-tools: [Bash, Read, Write]\n---\n"
        skill = MarkdownSkillParser().parse(md)
        assert skill.allowed_tools == ["Bash", "Read", "Write"]

    def test_empty_when_no_field(self) -> None:
        md = "---\nname: x\ndescription: y\n---\n"
        skill = MarkdownSkillParser().parse(md)
        assert skill.allowed_tools == []

    def test_inline_list_with_spaces(self) -> None:
        md = "---\nname: x\ndescription: y\nallowed-tools: [ Bash , Read ]\n---\n"
        skill = MarkdownSkillParser().parse(md)
        assert skill.allowed_tools == ["Bash", "Read"]

    def test_single_tool(self) -> None:
        md = "---\nname: x\ndescription: y\nallowed-tools: [Bash]\n---\n"
        skill = MarkdownSkillParser().parse(md)
        assert skill.allowed_tools == ["Bash"]

    def test_has_allowed_tools_property(self) -> None:
        md = "---\nname: x\ndescription: y\nallowed-tools: [Bash, Read]\n---\n"
        skill = MarkdownSkillParser().parse(md)
        assert skill.has_allowed_tools

    def test_has_allowed_tools_false_when_empty(self) -> None:
        md = "---\nname: x\ndescription: y\n---\n"
        skill = MarkdownSkillParser().parse(md)
        assert not skill.has_allowed_tools


# ── allowed-tools renderer ────────────────────────────────────────────────────


class TestAllowedToolsRenderer:
    def test_renders_allowed_tools_inline(self) -> None:
        skill, _ = _make_skill(allowed_tools=["Bash", "Read"])
        rendered = MarkdownSkillRenderer().render_skill_md(skill)
        assert "allowed-tools: [Bash, Read]" in rendered

    def test_no_allowed_tools_field_when_empty(self) -> None:
        skill, _ = _make_skill(allowed_tools=[])
        rendered = MarkdownSkillRenderer().render_skill_md(skill)
        assert "allowed-tools" not in rendered

    def test_roundtrip_via_parser(self) -> None:
        """Render a skill with allowed_tools, parse the output: values survive."""
        skill, _ = _make_skill(allowed_tools=["Bash", "Write", "Edit"])
        rendered = MarkdownSkillRenderer().render_skill_md(skill)
        parsed = MarkdownSkillParser().parse(rendered)
        assert parsed.allowed_tools == ["Bash", "Write", "Edit"]
