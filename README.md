# skills-forge

[![PyPI version](https://img.shields.io/pypi/v/skills-forge.svg)](https://pypi.org/project/skills-forge/)
[![Python](https://img.shields.io/pypi/pyversions/skills-forge.svg)](https://pypi.org/project/skills-forge/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/ficiverson/skills-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/ficiverson/skills-forge/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](https://github.com/ficiverson/skills-forge)

A clean-architecture toolkit for crafting, validating, packing, and distributing Claude Code skills — and exporting them to any AI platform.

![Forge](skills-forge.png)

---

## Why

Writing a Claude Code skill is easy. Writing a **good** one is not. Skills that trigger unreliably, consume too much context, or try to do everything at once make Claude less effective, not more.

skills-forge applies software engineering principles (SRP, OCP, DIP) to the skill authoring process. It gives you a CLI to scaffold, lint, test, pack, and install skills — with built-in validators that catch common anti-patterns before they reach production.

> **New here?** Read [`docs/guide/commands.md`](docs/guide/commands.md) for the full command reference, or [`docs/index.md`](docs/index.md) for a high-level overview.

---

## Install

```bash
pip install skills-forge
```

Or install from source with dev tools:

```bash
git clone https://github.com/ficiverson/skills-forge
cd skills-forge
pip install -e ".[dev]"
```

---

## Quick start

```bash
# Initialize workspace (creates ~/.skills-forge/config.toml with public registry)
skills-forge init

# 1. Scaffold a skill
skills-forge create \
  --name python-tdd \
  --category development \
  --description "Use for TDD with Python. Triggers: pytest, test-first, red-green-refactor, .py files." \
  --emoji 🔴

# 2. Author SKILL.md
$EDITOR output_skills/development/python-tdd/SKILL.md

# 3. Lint until clean
skills-forge lint output_skills/development/python-tdd

# 4. Run evals (optional but recommended)
skills-forge test output_skills/development/python-tdd

# 5. Install — Claude Code global (default)
skills-forge install output_skills/development/python-tdd

# Universal project install — works with Gemini CLI, Codex, VS Code Copilot too
skills-forge install output_skills/development/python-tdd --target agents --scope project

# Install into every supported tool at once
skills-forge install output_skills/development/python-tdd --target all

# 6. Bundle and share
skills-forge pack output_skills/development/python-tdd
skills-forge publish ./python-tdd-1.0.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --push
```

Or install a skill directly from the public registry:

```bash
skills-forge install \
  https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack \
  --sha256 10d16ba0db7b768219d0adb6c3dd8ea68b62e9f719a0132fdcd2bcf10271c0e6
```

---

## Features

| Feature | Command | Notes |
|---------|---------|-------|
| Scaffold | `create` | Generates SKILL.md + evals/ + companion dirs |
| Validate | `lint` | 20+ validators — name, description, tokens, links |
| Evals | `test` | Run skill evals against Claude, verify assertions |
| Install | `install` | Symlink into Claude Code, Gemini CLI, Codex, VS Code Copilot, or all |
| Info | `info` | Show install locations, registry version, deps |
| Health | `doctor` | Diagnose broken links, missing deps, outdated versions |
| Pack | `pack` | Bundle into a portable `.skillpack` archive |
| Unpack | `unpack` | Extract a `.skillpack` to a directory |
| Publish | `publish` | Push pack to a Git-backed registry |
| Update | `update` | Upgrade installed skills to latest registry version |
| Diff | `diff` | Show changes between installed and registry latest |
| Export | `export` | Emit for OpenAI GPTs, Gemini Gems, Bedrock, MCP server, and more |
| Registry | `registry` | Add / remove / set-default registry configs |
| Yank | `yank` | Mark a registry version as unsafe to install |
| Deprecate | `deprecate` | Mark a skill as superseded |
| Workspace | `init` | Initialize config.toml with public registry |

---

## Install targets

The `install` command creates a symlink from your skill directory into the target tool's skills folder. Because it's a symlink, edits to the source are instantly reflected — no reinstall needed.

| `--target` | Global path | Project path | Notes |
|---|---|---|---|
| `claude` *(default)* | `~/.claude/skills/` | `.claude/skills/` | Claude Code |
| `gemini` | `~/.gemini/skills/` | `.gemini/skills/` | Gemini CLI |
| `codex` | `~/.codex/skills/` | `.codex/skills/` | OpenAI Codex |
| `vscode` | *(no global)* | `.github/skills/` | VS Code Copilot |
| `agents` | `~/.agents/skills/` | `.agents/skills/` | Universal cross-vendor alias |
| `all` | all of the above | all of the above | Every applicable target |

`agents` is the recommended target for shared repos — every [agentskills.io](https://agentskills.io/specification)-conforming tool scans `.agents/skills/` automatically, so teammates on Gemini CLI, Codex, or VS Code Copilot pick up the same skills without any per-tool setup.

---

## Export formats

Export any `.skillpack` to the format your platform expects:

```bash
skills-forge export ./python-tdd-1.0.0.skillpack                       # system-prompt (default)
skills-forge export ./python-tdd-1.0.0.skillpack -f gpt-json            # OpenAI Custom GPT / Assistants API
skills-forge export ./python-tdd-1.0.0.skillpack -f gem-txt             # Google Gemini Gems
skills-forge export ./python-tdd-1.0.0.skillpack -f bedrock-xml         # AWS Bedrock agent prompt
skills-forge export ./python-tdd-1.0.0.skillpack -f mcp-server          # Self-contained MCP server (stdio)
skills-forge export ./python-tdd-1.0.0.skillpack -f mistral-json        # Mistral Agents API
skills-forge export ./python-tdd-1.0.0.skillpack -f gemini-api          # Vertex AI / Gemini Developer API
skills-forge export ./python-tdd-1.0.0.skillpack -f openai-assistants   # OpenAI Assistants API
```

The MCP server format generates a single runnable Python file exposing the skill as an MCP `Prompts` primitive — no extra installation required on the end user's machine.

---

## Skill anatomy

A skill is a directory containing:

```
my-skill/
├── SKILL.md              # Description, principles, workflow, constraints
├── evals/
│   ├── evals.json        # Test cases with assertions
│   └── fixtures/         # Input files referenced by eval cases
├── references/           # On-demand docs (loaded only when a step needs them)
├── scripts/              # Executable automation (generators, validators)
├── examples/             # Sample outputs that calibrate Claude's quality bar
└── assets/               # Static files (CSVs, templates, configs)
```

Minimal `SKILL.md`:

```markdown
---
name: python-tdd
version: 1.0.0
description: |
  Use this skill when writing Python code with a test-first workflow.
  Triggers on: pytest, unittest, TDD, red-green-refactor, test-driven,
  .py files, "write tests first", "add a failing test".
---

STARTER_CHARACTER = 🔴

## Principles

- Write a failing test before any production code
- One assertion per test where possible
- Keep the red-green-refactor cycle under 5 minutes

## Workflow

1. Write the smallest failing test that captures the next behavior
2. Run pytest and confirm it fails for the right reason
3. Write the minimum code to make it pass
4. Refactor with the test as a safety net
5. Commit on green

## Constraints

- Never write production code without a failing test
- Never commit on red
- Never skip the refactor step
```

### Description formula

The description is the skill's activation interface — Claude uses it to decide whether to load the skill. Aim for 30–150 tokens:

> *Use this skill when [situation]. Triggers on: [keywords, file extensions, action verbs].*

### Frontmatter fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Kebab-case identifier |
| `version` | no | Semantic version (default: `0.1.0`) |
| `description` | yes | 30–150 token trigger description |
| `emoji` | no | Skill icon shown in `list` |
| `depends_on` | no | Dependency on another skill |
| `requires-forge` | no | Minimum skills-forge version (e.g. `>=1.0.0`) |

---

## Evals

Skills can ship their own test suite in `evals/evals.json`:

```json
[
  {
    "id": 1,
    "prompt": "Write a failing test for a function that adds two numbers.",
    "expected_output": "A pytest test that asserts add(2, 3) == 5.",
    "assertions": [
      {
        "id": "a1",
        "text": "Response contains a test function",
        "type": "regex",
        "expected": "(import pytest|def test_)"
      }
    ],
    "files": []
  }
]
```

Supported assertion types: `contains`, `not-contains`, `regex`, `llm-judge`.

Run evals:

```bash
skills-forge test output_skills/development/python-tdd
skills-forge test output_skills/development/python-tdd --id 1 --id 3  # specific cases
```

---

## Validators

20+ rules across two categories:

**Pure validators** (check the Skill object):

| Rule | Severity | What it checks |
|------|----------|----------------|
| `description-too-short` | warning | Description < 30 tokens |
| `description-too-long` | error | Description > 150 tokens |
| `description-vague-language` | warning | Vague words ("stuff", "things") |
| `description-overly-broad` | error | Phrases like "any task", "everything" |
| `description-missing-triggers` | warning | No file extensions or action verbs |
| `missing-principles` | warning | No Principles section |
| `context-budget-exceeded` | error | Total tokens > 2000 |
| `context-budget-high` | warning | Total tokens > 1200 |
| `possible-srp-violation` | info | Instructions > 800 words |
| `missing-starter-character` | info | No STARTER_CHARACTER defined |
| `invalid-dependency-name` | error | Malformed depends_on entry |
| `missing-requires-forge` | warning | Uses depends_on/evals without requires-forge |
| `missing-evals` | info | No evals defined |

**Path-aware validators** (check the filesystem):

| Rule | Severity | What it checks |
|------|----------|----------------|
| `broken-reference-link` | error | Reference file missing on disk |
| `broken-example-link` | error | Example file missing on disk |
| `broken-asset-link` | error | Asset file missing on disk |
| `broken-script-link` | error | Script file missing on disk |
| `evals-not-array` | error | evals.json is not a JSON array |
| `eval-invalid-assertion-type` | error | Unknown assertion type |
| `eval-missing-fixture` | warning | Fixture file referenced but missing |

---

## Architecture

Clean architecture with four layers — dependencies point strictly inward:

```
src/skill_forge/
├── domain/           # Models, validators, ports — zero external dependencies
├── application/      # Use cases: create, lint, install, test, pack, publish, export …
├── infrastructure/   # Adapters: filesystem, markdown, symlinks, zip, git, http, exporters
└── cli/              # Typer CLI + composition root (factory.py)
```

`factory.py` is the only file that knows about concrete implementations. All use cases depend on ports (abstractions), not adapters.

---

## Multi-registry configuration

`skills-forge init` creates `~/.skills-forge/config.toml` with the public registry pre-populated:

```toml
[defaults]
registry = "public"
target   = "claude"

[registries.public]
url = "https://raw.githubusercontent.com/ficiverson/skill-registry/main"
```

Manage registries:

```bash
skills-forge registry list
skills-forge registry add internal https://registry.example.com --token "${INTERNAL_TOKEN}"
skills-forge registry remove internal
skills-forge registry set-default internal
```

Tokens support `${VAR}` / `$VAR` env-var expansion at call time.

---

## Git-backed registry

`skills-forge publish` turns any git repo into a free, CDN-backed skill registry:

```
skill-registry/
├── index.json
└── packs/
    └── <category>/
        └── <name>-<version>.skillpack
```

```bash
# Pack with owner metadata
skills-forge pack output_skills/evaluation/ai-eng-evaluator \
  --tag evaluation --owner-name "Fernando Souto" --owner-email "me@fernandosouto.dev"

# Publish to registry
skills-forge publish ./ai-eng-evaluator-1.0.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --push

# Install from registry URL with SHA256 verification
skills-forge install \
  https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack \
  --sha256 10d16ba0db7b768219d0adb6c3dd8ea68b62e9f719a0132fdcd2bcf10271c0e6

# Update all installed skills
skills-forge update --registry https://raw.githubusercontent.com/ficiverson/skill-registry/main

# Yank a bad version
skills-forge yank ai-eng-evaluator@0.2.0 \
  --registry ~/code/skill-registry \
  --reason "Critical bug in assertion logic"
```

---

## For AI agents authoring skills

If you are an AI agent (e.g. Claude) creating a skill on a user's behalf, follow this playbook:

1. **Clarify single responsibility.** Ask what trigger condition activates the skill and what concrete action it produces. Split multi-responsibility requests into multiple skills.
2. **Pick a category and kebab-case name.** No spaces. Layout: `output_skills/<category>/<name>/`.
3. **Run `skills-forge create`** with `--name`, `--category`, `--description`, `--emoji`. Description must follow the formula (30–150 tokens, includes triggers).
4. **Write the SKILL.md body.** Required sections: Principles, Workflow/Instructions, Constraints.
5. **Add companion files** for every link in References, Examples, Assets, Scripts — the linter will fail on missing files.
6. **Run `skills-forge lint <path>`** and fix every issue.
7. **Add at least one eval** and run `skills-forge test <path>`.
8. **Stop and report.** Do not install without explicit user permission.

### Definition of done

- [ ] `skills-forge lint <path>` reports zero errors and zero warnings
- [ ] Description is 30–150 tokens and follows the *Use when… Triggers on…* formula
- [ ] At least three concrete trigger keywords
- [ ] Principles: 3–7 imperative bullets
- [ ] Workflow: numbered steps
- [ ] Constraints: explicit "never" rules
- [ ] Every link resolves to a real file on disk
- [ ] Total token estimate < 1200
- [ ] `evals/evals.json` has at least one case and `skills-forge test` passes

---

## Development

```bash
pip install -e ".[dev]"

pytest --cov=skill_forge --cov-fail-under=95   # 665 tests, 97% coverage
ruff check src/ tests/
mypy src/
```

Full CI runs on Python 3.10, 3.11, and 3.12 on every push via GitHub Actions.

---

## License

MIT

---

_Inspired by [eferro's post on encoding experience into AI skills](https://www.eferro.net/2026/03/encoding-experience-into-ai-skills.html)._
