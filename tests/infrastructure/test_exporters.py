"""Tests for all SkillExporter adapters.

Each exporter test follows the same pattern:
1. Create a minimal Skill + body string
2. Call exporter.export(skill, body, tmp_path)
3. Assert the output file exists and contains the expected content
"""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.domain.model import ExportFormat, Skill
from skill_forge.infrastructure.adapters.exporters.bedrock_xml_exporter import (
    BedrockXmlExporter,
)
from skill_forge.infrastructure.adapters.exporters.gem_txt_exporter import (
    GemTxtExporter,
)
from skill_forge.infrastructure.adapters.exporters.gpt_json_exporter import (
    GptJsonExporter,
)
from skill_forge.infrastructure.adapters.exporters.mcp_server_exporter import (
    McpServerExporter,
)
from skill_forge.infrastructure.adapters.exporters.system_prompt_exporter import (
    SystemPromptExporter,
)

_BODY = """\
## Workflow

1. Read the user story.
2. Derive acceptance criteria.
3. Write test cases.
"""


# ── SystemPromptExporter ──────────────────────────────────────────────────────


class TestSystemPromptExporter:
    def setup_method(self) -> None:
        self.exporter = SystemPromptExporter()

    def test_format_enum(self) -> None:
        assert self.exporter.format == ExportFormat.SYSTEM_PROMPT

    def test_output_filename(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        assert out.name == "python-tdd.system-prompt.md"

    def test_output_exists(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        assert out.exists()

    def test_contains_skill_name(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "python-tdd" in content

    def test_contains_description(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "TDD" in content

    def test_contains_body(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "## Workflow" in content

    def test_creates_output_dir(self, minimal_skill: Skill, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "dir"
        out = self.exporter.export(minimal_skill, _BODY, nested)
        assert nested.exists()
        assert out.exists()


# ── GptJsonExporter ───────────────────────────────────────────────────────────


class TestGptJsonExporter:
    def setup_method(self) -> None:
        self.exporter = GptJsonExporter()

    def test_format_enum(self) -> None:
        assert self.exporter.format == ExportFormat.GPT_JSON

    def test_output_filename(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        assert out.name == "python-tdd.gpt.json"

    def test_valid_json(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        data = json.loads(out.read_text())
        assert isinstance(data, dict)

    def test_json_schema(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        data = json.loads(out.read_text())
        assert data["name"] == "python-tdd"
        assert "description" in data
        assert "instructions" in data
        assert isinstance(data["capabilities"], dict)

    def test_instructions_contain_body(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        data = json.loads(out.read_text())
        assert "## Workflow" in data["instructions"]

    def test_knowledge_files_populated_for_skill_with_refs(
        self, skill_with_references: Skill, tmp_path: Path
    ) -> None:
        out = self.exporter.export(skill_with_references, _BODY, tmp_path)
        data = json.loads(out.read_text())
        assert len(data["knowledge_files"]) == 2

    def test_knowledge_files_empty_for_minimal_skill(
        self, minimal_skill: Skill, tmp_path: Path
    ) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        data = json.loads(out.read_text())
        assert data["knowledge_files"] == []


# ── GemTxtExporter ────────────────────────────────────────────────────────────


class TestGemTxtExporter:
    def setup_method(self) -> None:
        self.exporter = GemTxtExporter()

    def test_format_enum(self) -> None:
        assert self.exporter.format == ExportFormat.GEM_TXT

    def test_output_filename(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        assert out.name == "python-tdd.gem.txt"

    def test_contains_gem_header(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "[Gem:" in content

    def test_contains_body(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "## Workflow" in content

    def test_contains_activation_trigger(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "Activation:" in content

    def test_plain_text_no_leading_frontmatter(
        self, minimal_skill: Skill, tmp_path: Path
    ) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert not content.startswith("---")


# ── BedrockXmlExporter ────────────────────────────────────────────────────────


class TestBedrockXmlExporter:
    def setup_method(self) -> None:
        self.exporter = BedrockXmlExporter()

    def test_format_enum(self) -> None:
        assert self.exporter.format == ExportFormat.BEDROCK_XML

    def test_output_filename(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        assert out.name == "python-tdd.bedrock.xml"

    def test_xml_declaration(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert content.startswith("<?xml")

    def test_has_prompt_template_root(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "<PromptTemplate>" in content
        assert "</PromptTemplate>" in content

    def test_has_system_block(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "<system>" in content
        assert "</system>" in content

    def test_has_human_turn_variable(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "$human_turn$" in content

    def test_body_in_system_block(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "## Workflow" in content

    def test_metadata_block(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "<metadata>" in content
        assert "<skill>python-tdd</skill>" in content


# ── McpServerExporter ─────────────────────────────────────────────────────────


class TestMcpServerExporter:
    def setup_method(self) -> None:
        self.exporter = McpServerExporter()

    def test_format_enum(self) -> None:
        assert self.exporter.format == ExportFormat.MCP_SERVER

    def test_output_filename(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        assert out.name == "python-tdd-mcp-server.py"

    def test_is_python_file(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        assert out.suffix == ".py"

    def test_has_mcp_imports(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "from mcp.server.fastmcp import FastMCP" in content

    def test_has_prompt_decorator(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "@mcp.prompt" in content

    def test_has_run_call(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "mcp.run()" in content

    def test_skill_name_embedded(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "python-tdd" in content

    def test_body_embedded(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert "## Workflow" in content

    def test_has_main_guard(self, minimal_skill: Skill, tmp_path: Path) -> None:
        out = self.exporter.export(minimal_skill, _BODY, tmp_path)
        content = out.read_text()
        assert 'if __name__ == "__main__"' in content
