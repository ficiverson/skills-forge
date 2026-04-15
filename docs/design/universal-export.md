# Universal Export Architecture

> Research conducted: April 2026

---

## Overview

The `.skillpack` format is designed for universal portability across all major LLM platforms. This page explains the architecture behind `skills-forge export` and how skills map to each platform's native concepts.

---

## Platform categories

### Agent-CLI tools (native SKILL.md support)

These tools natively understand SKILL.md and `.agents/skills/`:

| Tool | Install path |
|------|-------------|
| Claude Code | `~/.claude/skills/` or `.claude/skills/` |
| Gemini CLI | `~/.gemini/skills/` or `.gemini/skills/` |
| OpenAI Codex | `~/.codex/skills/` or `.codex/skills/` |
| VS Code Copilot | `.github/skills/` (project) |

Use `skills-forge install --target <tool>` for these.

### Chat/API platforms (need export)

These platforms don't have a filesystem skill concept — they need the skill content exported as a system prompt or native config:

| Platform | Export format | Mechanism |
|----------|---------------|-----------|
| OpenAI Custom GPTs | `gpt-json` | JSON configuration |
| Google Gemini Gems | `gem-txt` | Instruction text |
| AWS Bedrock Agents | `bedrock-xml` | XML prompt template |
| Mistral AI | `mistral-json` | System prompt JSON |
| OpenAI Assistants | `openai-assistants` | Assistants API JSON |
| Any API | `system-prompt` | Plain text |

### MCP (Model Context Protocol)

MCP is the emerging universal layer. A skill exported as an MCP server can be consumed by any MCP-compatible host:

```bash
skills-forge export my-skill.skillpack -f mcp-server -o ./mcp/
```

The generated server exposes the skill as an MCP `Prompt` primitive.

---

## Export pipeline

```
.skillpack archive
       │
       ├─ read manifest.json
       ├─ read SKILL.md
       └─ render body text
              │
              ▼
       SkillExporter (port)
              │
              ├─ SystemPromptExporter   → .system-prompt.txt
              ├─ GptJsonExporter        → .gpt.json
              ├─ GemTxtExporter         → .gem.txt
              ├─ BedrockXmlExporter     → .bedrock.xml
              ├─ MistralJsonExporter    → .mistral.json
              ├─ GeminiApiExporter      → .gemini-api.json
              ├─ OpenAIAssistantsExporter → .assistants.json
              └─ McpServerExporter     → _mcp_server.py
```

Each exporter implements `SkillExporter.export(skill, body, output_dir) → Path`.

---

## The body renderer

Before exporting, `MarkdownRenderer` renders the full skill body as a string, resolving references inline:

```
## Instructions
{instructions}

## Principles
{principles}

## Constraints
{constraints}

## References
{resolved content of each reference file}
```

This rendered body is passed to every exporter, ensuring consistent content regardless of target format.

---

## Token budget considerations

Different platforms have different context limits:

| Platform | System prompt limit |
|----------|-------------------|
| Claude (claude.ai) | 200k tokens (model context) |
| OpenAI Custom GPTs | ~32k tokens |
| Google Gemini Gems | ~32k tokens |
| AWS Bedrock | Model-specific |

The progressive disclosure pattern (description → body → references) naturally keeps skills lean. Reference content is inlined at export time, so monitor total token count after export for constrained platforms.

---

## MCP server export

The MCP server exporter produces a self-contained Python module:

```python
# python-tdd_mcp_server.py (generated)
from mcp.server import Server, stdio_server
from mcp.types import Prompt, GetPromptResult, PromptMessage, TextContent, Role

server = Server("python-tdd")

@server.list_prompts()
async def list_prompts():
    return [Prompt(name="python-tdd", description="...")]

@server.get_prompt()
async def get_prompt(name, arguments):
    return GetPromptResult(messages=[
        PromptMessage(role=Role.user, content=TextContent(type="text", text=SKILL_CONTENT))
    ])

if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(server))
```

Run with `python python-tdd_mcp_server.py` and add to your MCP host config.
