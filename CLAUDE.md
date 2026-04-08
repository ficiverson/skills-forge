# Skill Forge

A clean-architecture toolkit for crafting, validating, and installing Claude Code skills.

## Project structure

```
src/skill_forge/
├── domain/           # Core models, validators, ports (zero dependencies)
├── application/      # Use cases: create, lint, install, pack/unpack, publish, install-from-url
├── infrastructure/   # Adapters: filesystem, markdown, symlinks, zip packer, git registry, http fetcher
└── cli/              # Typer CLI + composition root (factory.py)

output_skills/        # Authored skills organized by category
templates/            # Skill scaffolding templates
tests/                # pytest suite (mirrors src/ layout)
docs/                 # Guides: getting-started, clean-principles
```

## Commands

```bash
skills-forge create -n <name> -c <category> -d "<description>" -e <emoji> [-v 0.1.0]
skills-forge lint <path>                       # Validate a skill or directory
skills-forge install <path>                    # Symlink into ~/.claude/skills/ (global)
skills-forge install <path> -s project         # Symlink into .claude/skills/ (project)
skills-forge install <https-url> [--sha256 …]  # Fetch a remote .skillpack and install it
skills-forge list [directory]                  # List skills with token estimates
skills-forge pack <skill-dir...> [-o out]      # Bundle skill(s) into a .skillpack archive
skills-forge unpack <pack> [-o dest]           # Extract a .skillpack into a directory
skills-forge publish <pack> -r <registry-clone> -u <base-url> [--push]
skills-forge init                              # Initialize a new workspace
```

## Development

```bash
pip install -e ".[dev]"
pytest                           # 168 tests
ruff check src/ tests/           # Linting
mypy src/                        # Type checking
```

## Key conventions

- Python >= 3.10, dependencies: typer >= 0.12
- Clean architecture: dependencies point inward (domain ← application ← infrastructure ← cli)
- Domain layer has zero external dependencies
- factory.py is the only file that knows about concrete implementations
- Skills follow progressive disclosure: description (~100 tokens) → body (~1000 tokens) → references (on-demand)
- All validators are pure functions: Skill in, list[LintIssue] out
- Path-aware validators additionally receive the skill directory for filesystem checks
