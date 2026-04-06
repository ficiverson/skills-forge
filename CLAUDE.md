# Skill Forge

A clean-architecture toolkit for crafting, validating, and installing Claude Code skills.

## Project structure

```
src/skill_forge/
├── domain/           # Core models, validators, ports (zero dependencies)
├── application/      # Use cases: create, lint, install
├── infrastructure/   # Adapters: filesystem, markdown parser/renderer, symlinks
└── cli/              # Typer CLI + composition root (factory.py)

output_skills/        # Authored skills organized by category
templates/            # Skill scaffolding templates
tests/                # pytest suite (mirrors src/ layout)
docs/                 # Guides: getting-started, clean-principles
```

## Commands

```bash
skill-forge create -n <name> -c <category> -d "<description>" -e <emoji>
skill-forge lint <path>          # Validate a skill or directory
skill-forge install <path>       # Symlink into ~/.claude/skills/ (global)
skill-forge install <path> -s project  # Symlink into .claude/skills/ (project)
skill-forge list [directory]     # List skills with token estimates
skill-forge init                 # Initialize a new workspace
```

## Development

```bash
pip install -e ".[dev]"
pytest                           # 84 tests
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
