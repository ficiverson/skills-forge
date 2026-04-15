# Skill Forge

A clean-architecture toolkit for crafting, validating, installing, and exporting Claude Code skills.

## Project structure

```
src/skill_forge/
├── domain/           # Core models, validators, ports (zero dependencies)
├── application/      # Use cases: create, lint, install, pack/unpack, publish, install-from-url, export
├── infrastructure/   # Adapters: filesystem, markdown, symlinks, zip packer, git registry, http fetcher, exporters
└── cli/              # Typer CLI + composition root (factory.py)

output_skills/        # Authored skills organized by category
templates/            # Skill scaffolding templates
tests/                # pytest suite (mirrors src/ layout)
docs/                 # Guides: getting-started, clean-principles, universal-export-research
```

## Commands

```bash
skills-forge init                                 # Initialize workspace + config.toml
skills-forge create -n <name> -c <category> -d "<description>" -e <emoji> [-v 0.1.0]
skills-forge lint <path>                          # Validate a skill or directory
skills-forge install <path>                       # Symlink into ~/.claude/skills/ (global)
skills-forge install <path> -s project            # Symlink into .claude/skills/ (project)
skills-forge install <path> -t agents -s project  # Universal .agents/skills/ (all tools)
skills-forge install <path> -t gemini             # ~/.gemini/skills/ (Gemini CLI)
skills-forge install <path> -t codex              # ~/.codex/skills/ (OpenAI Codex)
skills-forge install <path> -t vscode -s project  # .github/skills/ (VS Code Copilot)
skills-forge install <path> -t all                # Every supported tool at once
skills-forge install <https-url> [--sha256 …]     # Fetch a remote .skillpack and install it
skills-forge uninstall <name> [-t <target>]       # Remove installed skill symlinks
skills-forge info <name> [--registry <url>]       # Show install locations, version, deps
skills-forge list [directory]                     # List skills with token estimates
skills-forge list --category <cat>                # Filter by category
skills-forge list --filter <substr>               # Filter by name/description substring
skills-forge doctor [--no-registry]              # Health sweep: broken links, outdated versions
skills-forge test <path>                          # Run skill evals against Claude
skills-forge pack <skill-dir...> [-o out]         # Bundle skill(s) into a .skillpack archive
skills-forge unpack <pack> [-o dest]              # Extract a .skillpack into a directory
skills-forge export <path>                        # Export as system-prompt (default)
skills-forge export <path> -f gpt-json            # OpenAI Custom GPT JSON config
skills-forge export <path> -f gem-txt             # Google Gemini Gem instructions
skills-forge export <path> -f bedrock-xml         # AWS Bedrock agent prompt XML
skills-forge export <path> -f mcp-server [-o dir] # Self-contained Python MCP server
skills-forge export <path> -f mistral-json        # Mistral Agents API JSON
skills-forge export <path> -f gemini-api          # Vertex AI / Gemini Developer API JSON
skills-forge export <path> -f openai-assistants   # OpenAI Assistants API JSON
skills-forge publish <pack> -r <registry-clone> -u <base-url> [--push]
skills-forge update [name] [--dry-run] [--yes]    # Upgrade installed skills from registry
skills-forge diff <name> --registry <url>         # Unified diff vs registry latest
skills-forge yank <name>@<version> -r <registry> --reason <msg>
skills-forge deprecate <name> -r <registry> [--replaced-by <name>]
skills-forge registry list|add|remove|set-default # Manage named registry configs
```

### `--target` / `-t` values

| Target | Global path | Project path | Notes |
|--------|-------------|--------------|-------|
| `claude` (default) | `~/.claude/skills/` | `.claude/skills/` | Claude Code |
| `gemini` | `~/.gemini/skills/` | `.gemini/skills/` | Gemini CLI |
| `codex` | `~/.codex/skills/` | `.codex/skills/` | OpenAI Codex |
| `vscode` | *(not supported)* | `.github/skills/` | VS Code Copilot |
| `agents` | `~/.agents/skills/` | `.agents/skills/` | Universal cross-vendor alias |
| `all` | all of the above | all of the above | Writes every applicable path |

`agents` is the recommended target for **project-level** installs on teams that mix editors — every agentskills.io-conforming tool scans `.agents/skills/` automatically.

## Development

```bash
pip install -e ".[dev]"
pytest --cov=skill_forge --cov-fail-under=95   # 826 tests, 97% coverage
ruff check src/ tests/           # Linting
ruff format --check src/ tests/  # Format check (same as CI)
mypy src/                        # Type checking (strict)
```

## Key conventions

- Python >= 3.10, dependencies: typer >= 0.12
- Clean architecture: dependencies point inward (domain ← application ← infrastructure ← cli)
- Domain layer has zero external dependencies
- factory.py is the only file that knows about concrete implementations
- Skills follow progressive disclosure: description (~100 tokens) → body (~1000 tokens) → references (on-demand)
- All validators are pure functions: Skill in, list[LintIssue] out
- Path-aware validators additionally receive the skill directory for filesystem checks
