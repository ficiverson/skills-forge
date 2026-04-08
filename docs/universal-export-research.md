# Universal Skillpack Export — Research & Architecture Proposal

> Research date: April 2026  
> Scope: How to make skills-forge skillpacks portable across every major LLM platform

---

## TL;DR

The `.skillpack` format is already 90 % of the way to being universal. The underlying `SKILL.md` file is an open standard (agentskills.io, ratified December 2025) adopted by Claude Code, Gemini CLI, OpenAI Codex, VS Code Copilot, and 20+ other tools. The gaps that remain are:

1. **Install paths differ per tool** — a trivial `--target` flag on `install` closes this for all agent-style tools.
2. **Chat-only platforms (Custom GPTs, Gemini Gems, Bedrock, Mistral agents) have no file-system skill concept** — they need a dedicated `export` command that renders the skill body as a system prompt, or as the platform's native config format.
3. **MCP (Model Context Protocol) is the other universal layer** — a skill can be wrapped as an MCP `Prompt` primitive and consumed by any MCP-compatible host regardless of vendor.

---

## 1. The Landscape: Two Categories of LLM Platform

### 1a. Agent-CLI tools (already SKILL.md-native)

These tools have adopted the agentskills.io open standard and load skills from a well-known directory path. A `.skillpack` unpacked into the right directory just works.

| Platform | Global skills path | Project skills path | Notes |
|---|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` | Original spec creator |
| **Gemini CLI** | `~/.gemini/skills/` | `.gemini/skills/` | Full adoption, Dec 2025 |
| **OpenAI Codex** | `~/.codex/skills/` | `.codex/skills/` | Adopted Dec 2025 |
| **VS Code Copilot** | n/a | `.github/skills/` | Experimental, v1.108+ |
| **Universal alias** | `~/.agents/skills/` | `.agents/skills/` | Works across all above |

**Action required in skills-forge**: The `install` command currently hardcodes `~/.claude/skills/`. Adding a `--target` flag covers all of these with zero changes to the SKILL.md format itself.

### 1b. Chatbot / API platforms (no native skill directory)

These platforms have custom instruction or system-prompt concepts, but no file-system path for SKILL.md. Content must be _rendered_ into platform-native formats.

| Platform | Instruction mechanism | File support | Max system prompt |
|---|---|---|---|
| **OpenAI Custom GPT** | "Instructions" text field (Configure tab) | Up to 20 knowledge files (any format) | 256,000 chars |
| **OpenAI Assistants API** | `instructions` parameter string | Vector store file search | 256,000 chars |
| **Google Gemini Gems** | Custom instructions text | Up to 10 reference files | ~100k chars |
| **Gemini API (Vertex AI)** | `system_instruction` field | Via RAG / knowledge base | Model-dependent |
| **AWS Bedrock Agents** | Agent `instruction` string + XML prompt templates | Knowledge base (S3) | Template-limited |
| **Mistral Agents** | `system` prompt + `tools` JSON array | n/a | Model-dependent |
| **Cohere Command R+** | `preamble` field + `tools` JSON | n/a | Model-dependent |
| **Anthropic API (raw)** | `system` string or array | n/a | 200k tokens |

---

## 2. The Agent Skills Open Standard (agentskills.io)

In December 2025 Anthropic open-sourced the Skills specification under the Agentic AI Foundation (AAIF, a Linux Foundation directed fund, co-founded by Anthropic, Block, and OpenAI). This is the same `SKILL.md` format skills-forge already produces.

### Canonical SKILL.md frontmatter

```yaml
---
name: my-skill               # required; max 64 chars; lowercase + hyphens; matches dir name
description: "..."           # required; max 1024 chars; the primary trigger signal
license: MIT                 # optional
allowed-tools: [Bash, Read]  # optional; restricts which tools are available when skill is active
mode: false                  # optional; marks skill as a "mode command"
metadata:                    # optional; arbitrary key-value
  author: Fernando Souto
  version: 1.0.0
---
```

**Key design principles from the spec:**
- Body is plain Markdown — no vendor lock-in, no proprietary syntax
- Progressive disclosure: description (~100 tokens) → body (~1 000 tokens) → references (on-demand)
- Scripts in `scripts/`, reference docs in `references/`, static assets in `assets/`
- Context window is a shared resource: keep skills lean; reference, don't embed

This means **a skill authored for skills-forge is already a valid Agent Skill** on every platform that has adopted the spec. The only work is delivery.

---

## 3. MCP as the Second Universal Layer

The Model Context Protocol (now governed by AAIF alongside Agent Skills) defines three primitives a server can offer:

- **Tools** — callable functions
- **Resources** — structured readable data
- **Prompts** — parameterisable instruction templates

A `.skillpack` maps cleanly onto **Prompts** (the SKILL.md body becomes the prompt template) and optionally **Resources** (the `references/` directory). An MCP server wrapping a skillpack registry would let any MCP-capable host (Claude Desktop, Cursor, VS Code, OpenAI's desktop app, etc.) browse and inject skills on demand — without any platform-specific export step.

---

## 4. Proposed Architecture for skills-forge

### 4a. Short-term: `--target` flag on `install`

The simplest win. No new use-cases, just parameterise the destination path.

```
skills-forge install <path-or-url> [--sha256 ...] [--target <platform>] [--scope user|project]
```

| `--target` | `--scope user` writes to | `--scope project` writes to |
|---|---|---|
| `claude` (default) | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` |
| `gemini` | `~/.gemini/skills/<name>/` | `.gemini/skills/<name>/` |
| `codex` | `~/.codex/skills/<name>/` | `.codex/skills/<name>/` |
| `vscode` | `~/.vscode/skills/<name>/` | `.github/skills/<name>/` |
| `agents` | `~/.agents/skills/<name>/` | `.agents/skills/<name>/` |
| `all` | writes to all above global paths simultaneously | — |

**Clean architecture placement:**
- Domain: extend `InstallScope` enum → add `InstallTarget` enum
- Application: `InstallPack.execute()` receives `target: InstallTarget`
- Infrastructure: `SymlinkInstaller` already takes a path; pass the resolved target path
- CLI: add `--target` / `-t` option to the `install` command

### 4b. Medium-term: `export` command for chatbot platforms

```
skills-forge export <pack-or-skill-dir> [--format <fmt>] [--output <file>]
```

| `--format` | Output | Use case |
|---|---|---|
| `system-prompt` (default) | Plain `.md` with frontmatter stripped | Paste into any chat UI system field |
| `gpt-json` | OpenAI Custom GPT config JSON | Import into GPT Builder or Assistants API |
| `gem-txt` | Plain text file per Gem instructions | Upload to Google Gemini Gem builder |
| `bedrock-xml` | AWS Bedrock agent prompt XML template | Drop into Bedrock Agent configuration |
| `mcp-server` | A self-contained Node.js/Python MCP server | Run locally; any MCP host connects to it |
| `openapi` | OpenAPI 3.1 schema describing skill actions | For GPT Actions / Assistants function calling |

#### Format details

**`system-prompt`** — strips YAML frontmatter, prepends a one-line role declaration from `description`, outputs the body verbatim. Any model, any chat interface.

```markdown
You are an expert in sprint grooming. Use this skill when transforming rough ideas 
into production-ready user stories.

## Workflow
...
```

**`gpt-json`** — matches OpenAI's GPT configuration schema:

```json
{
  "name": "sprint-grooming",
  "description": "Transforms rough ideas into production-ready user stories...",
  "instructions": "<SKILL.md body>",
  "knowledge_files": ["references/invest-criteria.md", "references/dod-checklist.md"],
  "capabilities": { "code_interpreter": false, "browsing": false, "dalle": false }
}
```

**`mcp-server`** — generates a minimal MCP server that exposes all skills in the pack as `Prompts`. The server can be run with `npx` or `uvx`:

```bash
# generated output
skills-forge export ./sprint-grooming-1.0.0.skillpack --format mcp-server -o ./sprint-grooming-mcp/

# usage: add to Claude Desktop, Cursor, VS Code MCP config
npx tsx ./sprint-grooming-mcp/index.ts
```

The MCP Prompts spec maps perfectly:

```typescript
server.setRequestHandler(ListPromptsRequestSchema, async () => ({
  prompts: [{
    name: "sprint-grooming",
    description: "...",   // from SKILL.md description frontmatter
    arguments: []
  }]
}));

server.setRequestHandler(GetPromptRequestSchema, async (request) => ({
  messages: [{
    role: "user",
    content: { type: "text", text: skillBody }  // SKILL.md body
  }]
}));
```

**Clean architecture placement for `export`:**

```
domain/
  model.py          ← add ExportFormat enum, ExportRequest, ExportResult
application/
  use_cases/
    export_skill.py ← ExportSkill use case; pure: ExportRequest in, ExportResult out
infrastructure/
  adapters/
    exporters/
      system_prompt_exporter.py
      gpt_json_exporter.py
      gem_txt_exporter.py
      bedrock_xml_exporter.py
      mcp_server_exporter.py
cli/
  main.py           ← add `export` command; factory.py wires the right exporter
```

### 4c. Long-term: `registry serve --mcp`

A single command that stands up an MCP server in front of an existing registry (local clone or remote `index.json`). Any MCP-capable host can then:
- `ListPrompts` → browse all published skills
- `GetPrompt(name)` → receive the full skill body, injected as a system message
- No installation step needed — the skill is delivered at inference time

```
skills-forge registry serve \
  --registry ./skill-registry \
  --transport stdio          # or --transport http --port 3000
```

This turns the registry into a universal plugin layer for any LLM that speaks MCP — currently: Claude, Cursor, VS Code Copilot, and (as of March 2025) OpenAI's products.

---

## 5. Implementation Roadmap

| Release | Feature | Effort |
|---|---|---|
| **v0.2.0** | `install --target <platform>` covering claude / gemini / codex / vscode / agents / all | Small — path resolution only |
| **v0.2.0** | `export --format system-prompt` | Small — strip frontmatter, prepend description |
| **v0.2.0** | `export --format gpt-json` | Small — JSON serialisation of manifest + body |
| **v0.3.0** | `export --format gem-txt` | Trivial — same as system-prompt with Gem conventions |
| **v0.3.0** | `export --format mcp-server` | Medium — code generation for an MCP Prompts server |
| **v0.3.0** | `export --format bedrock-xml` | Medium — XML template generation |
| **v0.4.0** | `registry serve --mcp` | Large — MCP server wrapping registry `index.json` |
| **v0.4.0** | `export --format openapi` | Large — infer Actions schema from skill scripts |

---

## 6. What Changes in the Registry

The `index.json` already has all the metadata needed. One addition would be useful: a `platforms` field per skill indicating which export formats have been tested and verified:

```json
{
  "name": "sprint-grooming",
  "platforms": ["claude", "gemini", "codex", "gpt-json", "mcp"],
  ...
}
```

The `regenerate-readme.py` script and `index.html` can then surface this as badges on each card, giving users confidence before they export.

---

## 7. Key Insight: skills-forge is ahead, not behind

The concern about "how do we support other platforms" has been answered by the open standard. Most competing platforms have converged on the same `SKILL.md` format. skills-forge's main differentiation is:

- **The `.skillpack` distribution format** — a single, versioned, sha256-verified artifact for safe transport
- **The registry + publish workflow** — git-backed, CDN-served, zero infrastructure
- **The linting / quality gates** — validator pipeline that enforces description quality, token budget, file existence
- **The export layer (proposed)** — the bridge between the agent-native world and the chatbot-API world

None of the agent-native tools (Gemini CLI, Codex) have a registry + publish + lint + distribute pipeline. That is skills-forge's unique value. Export formats are an additive feature, not a fundamental redesign.

---

## Sources

- [Agent Skills specification — agentskills.io](https://agentskills.io/specification)
- [Model Context Protocol specification — modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-11-25)
- [Introducing MCP — Anthropic](https://www.anthropic.com/news/model-context-protocol)
- [Use Agent Skills in VS Code — code.visualstudio.com](https://code.visualstudio.com/docs/copilot/customization/agent-skills)
- [Agent Skills — Gemini CLI docs](https://geminicli.com/docs/cli/skills/)
- [Agent Skills — OpenAI Codex docs](https://developers.openai.com/codex/skills)
- [Google Gemini Gems guide — support.google.com](https://support.google.com/gemini/answer/15235603)
- [OpenAI Assistants API — platform.openai.com](https://platform.openai.com/docs/assistants/tools/file-search)
- [AWS Bedrock advanced prompts — docs.aws.amazon.com](https://docs.aws.amazon.com/bedrock/latest/userguide/advanced-prompts-templates.html)
- [Mistral Agents — docs.mistral.ai](https://docs.mistral.ai/agents/agents)
- [Cohere Command R+ — docs.cohere.com](https://docs.cohere.com/docs/command-r-plus)
- [GitHub Copilot Agent Skills changelog — github.blog](https://github.blog/changelog/2025-12-18-github-copilot-now-supports-agent-skills/)
- [SKILL.md Pattern guide — bibek-poudel.medium.com](https://bibek-poudel.medium.com/the-skill-md-pattern-how-to-write-ai-agent-skills-that-actually-work-72a3169dd7ee)
- [Gemini CLI built-in skill-creator SKILL.md — github.com/google-gemini](https://github.com/google-gemini/gemini-cli/blob/main/packages/core/src/skills/builtin/skill-creator/SKILL.md)
