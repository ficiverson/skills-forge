# skills-forge

A clean-architecture toolkit for crafting high-quality Claude Code skills.

![Forge](skills-forge.png)

## Why

Writing a Claude Code skill is easy. Writing a **good** one is not. Skills that trigger unreliably, consume too much context, or try to do everything at once make Claude less effective, not more.

skills-forge applies software engineering principles (SRP, OCP, DIP) to the skill authoring process. It gives you a CLI to scaffold, lint, test, and install skills — with built-in validators that catch common anti-patterns before they reach production.

> **New here?** Read [`docs/getting-started.md`](docs/getting-started.md) for a step-by-step walkthrough of the full authoring loop.

## Quick start

```bash
pip install -e ".[dev]"

# Initialize a workspace (also creates ~/.skills-forge/config.toml)
skills-forge init

# 1. Scaffold a skill (generates SKILL.md + evals/ directory)
skills-forge create \
  --name python-tdd \
  --category development \
  --description "Use for TDD with Python. Triggers: pytest, test-first, red-green-refactor, .py files." \
  --emoji 🔴

# 2. Open the generated SKILL.md and write the actual content
$EDITOR output_skills/development/python-tdd/SKILL.md

# 3. Lint until clean
skills-forge lint output_skills/development/python-tdd

# 4. Run evals (optional but recommended)
skills-forge test output_skills/development/python-tdd

# 5. Install — default (Claude Code, global)
skills-forge install output_skills/development/python-tdd

# Or: universal project install — works with Gemini CLI, Codex, VS Code Copilot too
skills-forge install output_skills/development/python-tdd --target agents --scope project

# Or: write to every supported tool at once
skills-forge install output_skills/development/python-tdd --target all

# 6. Bundle and share with your team
skills-forge pack output_skills/development/python-tdd
skills-forge publish ./python-tdd-0.1.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --push

# Or try installing a real pack from the live registry right now:
skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack \
  --sha256 10d16ba0db7b768219d0adb6c3dd8ea68b62e9f719a0132fdcd2bcf10271c0e6
```

The `install` command creates a symlink from your skill directory into the target tool's skills directory. Because it's a symlink, you edit the source in `output_skills/`, re-lint, and the installed version updates without reinstalling.

All targets share the same SKILL.md format — the [agentskills.io](https://agentskills.io/specification) open standard adopted by Claude Code, Gemini CLI, OpenAI Codex, VS Code Copilot, and 20+ other tools.

| `--target` | Global path | Project path |
|---|---|---|
| `claude` *(default)* | `~/.claude/skills/` | `.claude/skills/` |
| `gemini` | `~/.gemini/skills/` | `.gemini/skills/` |
| `codex` | `~/.codex/skills/` | `.codex/skills/` |
| `vscode` | *(no global)* | `.github/skills/` |
| `agents` | `~/.agents/skills/` | `.agents/skills/` |
| `all` | all of the above | all of the above |

`agents` is the recommended target for shared repos — every conforming tool scans `.agents/skills/` at project scope, so teammates on Gemini CLI, Codex, or VS Code Copilot all pick up the same skills without any per-tool setup.

## Authoring workflow

The authoring loop has six steps. Step 2 (the actual writing) is the one that matters most.

1. **Scaffold** with `skills-forge create`. This writes a starter `SKILL.md` plus empty companion directories (`references/`, `examples/`, `assets/`, `scripts/`, `evals/`).
2. **Author the content.** Open `SKILL.md` and fill in the description, principles, workflow, and constraints. Drop reference docs into `references/`, sample outputs into `examples/`, and static files into `assets/`.
3. **Lint** with `skills-forge lint <path>`. Fix every error and warning.
4. **Write evals** (recommended). Add cases to `evals/evals.json` and run `skills-forge test <path>` to verify the skill produces the right output.
5. **Install** with `skills-forge install <path>`. Use `--scope project` for a project-local install, or omit it for global. Add `--target agents` for the universal cross-vendor path.
6. **Test and iterate.** Open Claude Code, trigger the skill with a realistic prompt, and watch how it activates. Tweak the description and triggers until activation is reliable.

### A complete minimal SKILL.md

```markdown
---
name: python-tdd
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

### Writing a good description

The description is the skill's interface — Claude uses it to decide whether to activate. Aim for 30–150 tokens (≈ 20–100 words) and follow this formula:

> *Use this skill when [situation]. Triggers on: [keywords, file extensions, action verbs].*

Good:

> Use this skill when reviewing pull requests for security issues. Triggers on: PR review, security audit, OWASP, SQL injection, XSS, .py, .js, .ts files.

Bad:

> A skill for code stuff. Use it for any kind of code review or whatever.

The bad example trips four validators at once: too short, vague language ("stuff", "whatever"), overly broad ("any kind"), and missing triggers (no extensions or action verbs).

## For AI agents authoring skills

If you are an AI agent (e.g. Claude) creating a skill on a user's behalf, follow this deterministic playbook:

1. **Clarify the skill's single responsibility.** Ask the user what trigger condition should activate the skill and what concrete action it should produce. If the answer covers more than one responsibility, split it into multiple skills.
2. **Pick a category and a kebab-case name.** Names must contain no spaces. Categories live under `output_skills/<category>/<name>/`.
3. **Run `skills-forge create`** with `--name`, `--category`, `--description`, and `--emoji`. The description must follow the formula above (30–150 tokens, includes triggers).
4. **Write the SKILL.md body** using the [minimal example](#a-complete-minimal-skillmd) as a structural template. Required sections: Principles, Workflow (or Instructions), Constraints. Optional but recommended: Hints, References, Examples, Assets.
5. **Add companion files** when referenced from SKILL.md. Every link in `## References`, `## Examples`, `## Assets`, and `## Scripts` must resolve to a real file on disk — the linter will fail otherwise.
6. **Run `skills-forge lint <path>`** and fix every issue. Iterate until the linter reports clean.
7. **Add at least one eval** in `evals/evals.json` with a realistic prompt and a `contains` or `regex` assertion. Run `skills-forge test <path>` to verify it passes.
8. **Stop and report.** Hand the skill back to the user with the path and a one-line summary. Do not install it without explicit user permission.

### Definition of done

A skill is ready when **all** of these are true:

- [ ] `skills-forge lint <path>` reports clean (zero errors, zero warnings)
- [ ] Description is 30–150 tokens and follows the *Use when... Triggers on...* formula
- [ ] At least three concrete trigger keywords (file extensions, action verbs, or domain terms)
- [ ] Principles section has 3–7 imperative bullets
- [ ] Workflow has numbered steps that a junior could follow without guessing
- [ ] Constraints lists what the skill must **never** do
- [ ] Every link in References/Examples/Assets/Scripts resolves to a real file
- [ ] Total token estimate is under 1200 (warning threshold)
- [ ] `evals/evals.json` has at least one test case and `skills-forge test` passes

### When to use which section

- **Principles** — universal rules that always apply ("write tests first")
- **Workflow** — the ordered steps Claude should follow when the skill activates
- **Constraints** — hard "never" rules ("never commit on red")
- **Hints** — situational branching ("if no tests directory exists, score code_quality ≤ 4"). Use hints, not principles, when guidance is conditional.
- **References** — long-form docs Claude reads only when a workflow step needs them. Use this to keep SKILL.md under the token budget.
- **Examples** — sample outputs that calibrate Claude's quality bar. The single highest-leverage thing you can add.
- **Assets** — static files (CSVs, templates, configs) that scripts or Claude reference at runtime.
- **depends_on** — declare another skill that should also be loaded when this one activates.
- **evals/** — test cases that verify skill output quality. See [Evals](#evals) below.

## Architecture

The project follows clean architecture with four layers:

```
src/skill_forge/
├── domain/           # Core: models, validators, ports (zero dependencies)
├── application/      # Use cases: create, lint, install, test, pack/unpack, publish, install-from-url
├── infrastructure/   # Adapters: filesystem, markdown, symlinks, zip packer, git registry, http fetcher
└── cli/              # Entry point: typer CLI + composition root
```

**Dependency rule:** dependencies point inward. Domain knows nothing about infrastructure. Use cases depend on ports (abstractions), not adapters (implementations). The CLI's `factory.py` is the composition root that wires everything together.

## Skill anatomy

A skill is a directory with this structure:

```
my-skill/
├── SKILL.md              # Core: description, principles, workflow, constraints
├── evals/                # NEW in v0.4.0: test suite
│   ├── evals.json        # Eval cases array
│   └── fixtures/         # Input files referenced by eval cases
├── references/           # On-demand docs loaded only when a step needs them
├── scripts/              # Executable automation (generators, validators)
├── examples/             # Sample outputs showing expected format and quality
└── assets/               # Static files (CSVs, templates, images, config)
```

The `SKILL.md` frontmatter supports these fields:

```yaml
---
name: my-skill
version: 1.0.0
description: |
  What this skill does and when to trigger it.
depends_on: other-skill (reason for dependency)
requires-forge: ">=0.4.0"
---
```

The body supports these sections: **Principles**, **Workflow/Instructions**, **Constraints**, **Hints**, **References**, **Examples**, **Assets**.

### requires-forge

Skills that use v0.4.0+ features (`depends_on`, evals) should declare a minimum version constraint:

```yaml
requires-forge: ">=0.4.0"
```

Supported operators: `>=`, `>`, `==`, `<=`, `<`, `!=`. Multiple comma-separated specifiers use AND logic (PEP 440 style). `skills-forge install` enforces the constraint before writing any files and prints a clear error with an upgrade command if the running version is too old.

### Hints

The `## Hints` section contains conditional guidance that Claude applies only when relevant. Unlike principles (always apply) or constraints (hard rules), hints are situational branching logic:

```markdown
## Hints

- If the repo has no tests directory, score code_quality <= 4
- If the project uses TypeScript, look for tsconfig.json instead of mypy
- If this is a monorepo, evaluate each service separately
```

### depends_on

Skills can declare dependencies on other skills. This tells Claude to also read the dependency's SKILL.md when the skill activates:

```yaml
depends_on: pdf (PDF generation for the final report)
```

Multiple dependencies use comma separation:

```yaml
depends_on: pdf (report output), xlsx (data export)
```

### Examples

The `## Examples` section links to sample outputs in `examples/`. These are the single most useful calibration tool for Claude — an example output is worth more than a page of specification:

```markdown
## Examples

- [Sample evaluation JSON](examples/example-eval.json)
- [Example test report](examples/example-report.md)
```

### Assets

The `## Assets` section links to static files that scripts or Claude can reference at runtime:

```markdown
## Assets

- [Level thresholds](assets/level-thresholds.csv)
- [Docker reference](assets/docker-cypress.md)
```

## Evals

Skills can ship their own test suite inside `evals/evals.json`. Run them with:

```bash
skills-forge test output_skills/development/python-tdd
skills-forge test output_skills/development/python-tdd -t 60   # 60s per eval
```

`evals/evals.json` is a JSON array of eval case objects:

```json
[
  {
    "id": 1,
    "prompt": "Write a failing test for a function that adds two numbers.",
    "expected_output": "A pytest test function that asserts the result of add(2, 3) equals 5.",
    "assertions": [
      {
        "id": "a1",
        "text": "Response contains a pytest import or def test_",
        "type": "regex",
        "expected": "(import pytest|def test_)"
      },
      {
        "id": "a2",
        "text": "Response does not contain production code before the test",
        "type": "not-contains",
        "expected": "def add("
      }
    ],
    "files": []
  }
]
```

Supported assertion types: `contains`, `not-contains`, `regex` (all graded programmatically), and `llm-judge` (invokes a second Claude call for open-ended quality assessment).

Place input fixture files referenced in `files[]` under `evals/fixtures/`. The `evals/` directory is excluded from all export formats — it's developer tooling, not user-facing content.

`skills-forge create` generates a starter `evals.json` with placeholder cases. `skills-forge list` shows an `[evals]` tag for skills that have at least one case defined.

## Multi-registry configuration

`skills-forge init` creates `~/.skills-forge/config.toml` with the public registry pre-populated:

```toml
[defaults]
registry = "public"
target   = "claude"

[registries.public]
url = "https://raw.githubusercontent.com/ficiverson/skill-registry/main"
```

Manage registries with:

```bash
skills-forge registry list
skills-forge registry add internal https://registry.example.com --token "${INTERNAL_TOKEN}"
skills-forge registry remove internal
skills-forge registry set-default internal
```

Per-registry tokens support `${VAR}` / `$VAR` env-var expansion at call time. Token resolution priority for remote fetches: config file → `GITHUB_TOKEN` env var → unauthenticated.

## Validators

The linter runs two types of validators:

**Pure validators** (check the Skill object):

| Rule | Severity | What it checks |
|------|----------|---------------|
| `description-too-short` | warning | Description < 30 tokens |
| `description-too-long` | error | Description > 150 tokens |
| `description-vague-language` | warning | Vague words like "stuff", "things" |
| `description-overly-broad` | error | Phrases like "any task", "everything" |
| `description-missing-triggers` | warning | No file extensions or action verbs |
| `missing-principles` | warning | No principles section |
| `context-budget-exceeded` | error | Total tokens > 2000 |
| `context-budget-high` | warning | Total tokens > 1200 |
| `reference-too-deep` | warning | Nested references (> 1 level) |
| `possible-srp-violation` | info | Instructions > 800 words |
| `missing-starter-character` | info | No STARTER_CHARACTER defined |
| `missing-examples` | info | Has scripts but no example outputs |
| `invalid-dependency-name` | error | Malformed depends_on entry |
| `missing-requires-forge` | warning | Uses depends_on/evals without requires-forge |
| `missing-evals` | info | No evals defined in evals/evals.json |

**Path-aware validators** (check the filesystem):

| Rule | Severity | What it checks |
|------|----------|---------------|
| `broken-reference-link` | error | Reference file doesn't exist on disk |
| `broken-example-link` | error | Example file doesn't exist on disk |
| `broken-asset-link` | error | Asset file doesn't exist on disk |
| `broken-script-link` | error | Script file doesn't exist on disk |
| `evals-not-array` | error | evals.json is not a JSON array |
| `eval-invalid-assertion-type` | error | Unknown assertion type in evals.json |
| `eval-missing-fixture` | warning | Fixture file referenced in evals.json is missing |

> **Severity model:** `is_clean` returns `True` when there are zero ERRORs and zero WARNINGs. INFO-level issues are informational only and do not block clean status.

## Sharing skills across teams

Once a skill is good, you'll want to share it with your team. skills-forge ships with a `.skillpack` format — a single zip file containing one or more skills plus a JSON manifest — so you can distribute skills via Slack, Notion, email, GitHub releases, or any other channel that can move a file.

### Per-skill versioning

Each skill carries its own semantic version in frontmatter:

```yaml
---
name: ai-eng-evaluator
version: 1.0.0
description: |
  ...
---
```

The pack command auto-derives its version from the skill itself, so you don't need to pass `--version` for single-skill packs. Bump the skill's frontmatter version when you ship a change, and the next `pack` will use the new value.

```bash
# Bundle a single skill — version auto-derived from frontmatter
skills-forge pack output_skills/evaluation/ai-eng-evaluator \
  --output ./packs/
# → ./packs/ai-eng-evaluator-1.0.0.skillpack

# Bundle multiple skills together
skills-forge pack \
  output_skills/evaluation/ai-eng-evaluator \
  output_skills/evaluation/user-story-test-cases \
  --name evaluation-bundle \
  --version 1.0.0 \
  --output evaluation-bundle.skillpack

# A teammate receives the file and unpacks it
skills-forge unpack evaluation-bundle.skillpack --output output_skills/

# Then lints and installs as usual
skills-forge lint output_skills/evaluation/ai-eng-evaluator
skills-forge install output_skills/evaluation/ai-eng-evaluator
```

A `.skillpack` is just a zip. The manifest at the root looks like:

```json
{
  "format_version": "1",
  "name": "evaluation-bundle",
  "version": "1.0.0",
  "author": "me@fernandosouto.dev",
  "created_at": "2026-04-10T18:09:56+00:00",
  "skills": [
    {"category": "evaluation", "name": "ai-eng-evaluator", "version": "1.0.0"},
    {"category": "evaluation", "name": "user-story-test-cases", "version": "0.1.0"}
  ]
}
```

### Publishing to a git-backed registry

`skills-forge publish` turns any git repo into a free, CDN-backed skill registry.

```
skill-registry/
├── index.json
└── packs/
    └── <category>/
        └── <name>-<version>.skillpack
```

```bash
skills-forge pack output_skills/evaluation/ai-eng-evaluator
skills-forge publish ./ai-eng-evaluator-1.0.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --push
```

**Install from a URL:**

```bash
# Without verification (prints a SHA256 warning)
skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack

# With SHA256 verification (recommended)
skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack \
  --sha256 10d16ba0db7b768219d0adb6c3dd8ea68b62e9f719a0132fdcd2bcf10271c0e6
```

When installing from a URL without `--sha256`, a warning is printed to stderr. Providing a wrong digest exits non-zero before any files are written.

**Multi-platform install (`--target`):**

```bash
skills-forge install output_skills/development/python-tdd --target gemini
skills-forge install output_skills/development/python-tdd --target codex
skills-forge install output_skills/development/python-tdd --target agents --scope project
skills-forge install output_skills/development/python-tdd --target vscode --scope project
skills-forge install output_skills/development/python-tdd --target all
```

**Export to chatbot / API platforms:**

| `--format` | Output file | Target platform |
|---|---|---|
| `system-prompt` (default) | `<name>.system-prompt.md` | Any chat UI |
| `gpt-json` | `<name>.gpt.json` | OpenAI Custom GPT / Assistants API |
| `gem-txt` | `<name>.gem.txt` | Google Gemini Gems |
| `bedrock-xml` | `<name>.bedrock.xml` | AWS Bedrock agent prompt template |
| `mcp-server` | `<name>-mcp-server.py` | Any MCP-capable host |

```bash
skills-forge export ./packs/productivity-1.0.0.skillpack
skills-forge export ./packs/productivity-1.0.0.skillpack -f gpt-json
skills-forge export ./packs/productivity-1.0.0.skillpack -f mcp-server -o ./exports/
```

The MCP server format generates a single runnable Python file exposing the skill as an MCP `Prompts` primitive. Any MCP-compatible host (Claude Desktop, Cursor, VS Code, OpenAI desktop app) can connect via stdio — no installation on the end user's machine.

## Templates

Four templates in `templates/`:

- **minimal** — Just frontmatter, principles, instructions, constraints
- **with-references** — Adds references, examples, hints, and depends_on
- **with-scripts** — Adds scripts, examples, assets, and validation
- **full-featured** — All sections: workflow steps, references, examples, assets, hints, depends_on, validation scripts

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (383 tests)
pytest

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## License

MIT

---

_I decided to create this repo after reading [this eferro post on encoding experience into AI skills](https://www.eferro.net/2026/03/encoding-experience-into-ai-skills.html)._
