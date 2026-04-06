# skill-forge

A clean-architecture toolkit for crafting high-quality Claude Code skills.

![Forge](skills-forge.png)

## Why

Writing a Claude Code skill is easy. Writing a **good** one is not. Skills that trigger unreliably, consume too much context, or try to do everything at once make Claude less effective, not more.

skill-forge applies software engineering principles (SRP, OCP, DIP) to the skill authoring process. It gives you a CLI to scaffold, lint, and install skills — with built-in validators that catch common anti-patterns before they reach production.

> **New here?** Read [`docs/getting-started.md`](docs/getting-started.md) for a step-by-step walkthrough of the full authoring loop.

## Quick start

```bash
pip install -e ".[dev]"

# Initialize a workspace
skill-forge init

# 1. Scaffold a skill
skill-forge create \
  --name python-tdd \
  --category development \
  --description "Use for TDD with Python. Triggers: pytest, test-first, red-green-refactor, .py files." \
  --emoji 🔴

# 2. Open the generated SKILL.md and write the actual content
#    (principles, workflow, constraints, hints, references...)
$EDITOR output_skills/development/python-tdd/SKILL.md

# 3. Lint until clean (fix every error, then warnings)
skill-forge lint output_skills/development/python-tdd

# 4. Install (symlinks into ~/.claude/skills/)
skill-forge install output_skills/development/python-tdd

# 5. Iterate: edit → re-lint → Claude picks up changes instantly

# 6. Bundle and share with your team
skill-forge pack output_skills/development/python-tdd
skill-forge publish ./python-tdd-0.1.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --push

# Or try installing a real pack from the live registry right now:
skill-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack \
  --sha256 10d16ba0db7b768219d0adb6c3dd8ea68b62e9f719a0132fdcd2bcf10271c0e6
```

The `install` command creates a symlink from your skill directory into `~/.claude/skills/` (global) or `.claude/skills/` (project-scoped), so Claude Code discovers it automatically. Because it's a symlink, you edit the source in `output_skills/`, re-lint, and the installed version updates without reinstalling.

## Authoring workflow

The authoring loop has five steps. Step 2 (the actual writing) is the one that matters most.

1. **Scaffold** with `skill-forge create`. This writes a starter `SKILL.md` plus empty companion directories (`references/`, `examples/`, `assets/`, `scripts/`) when the relevant fields are present.
2. **Author the content.** Open `SKILL.md` and fill in the description, principles, workflow, and constraints. Drop reference docs into `references/`, sample outputs into `examples/`, and static files into `assets/`.
3. **Lint** with `skill-forge lint <path>`. Fix every error and warning. The linter checks both the SKILL.md content (description length, vague language, token budget) and the filesystem (do all linked files actually exist?).
4. **Install** with `skill-forge install <path>`. Use `--scope project` for a project-local install, or omit it for global.
5. **Test and iterate.** Open Claude Code, trigger the skill with a realistic prompt, and watch how it activates. Tweak the description and triggers until activation is reliable.

### A complete minimal SKILL.md

This is what you should aim for when authoring a basic skill — copy this as a starting point:

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
3. **Run `skill-forge create`** with `--name`, `--category`, `--description`, and `--emoji`. The description must follow the formula above (30–150 tokens, includes triggers).
4. **Write the SKILL.md body** using the [minimal example](#a-complete-minimal-skillmd) as a structural template. Required sections: Principles, Workflow (or Instructions), Constraints. Optional but recommended: Hints, References, Examples, Assets.
5. **Add companion files** when referenced from SKILL.md. Every link in `## References`, `## Examples`, `## Assets`, and `## Scripts` must resolve to a real file on disk — the linter will fail otherwise.
6. **Run `skill-forge lint <path>`** and fix every issue. Iterate until the linter reports clean. Do not stop on the first warning — fix all of them.
7. **Stop and report.** Hand the skill back to the user with the path and a one-line summary. Do not install it without explicit user permission.

### Definition of done

A skill is ready when **all** of these are true:

- [ ] `skill-forge lint <path>` reports clean (zero errors, zero warnings)
- [ ] Description is 30–150 tokens and follows the *Use when... Triggers on...* formula
- [ ] At least three concrete trigger keywords (file extensions, action verbs, or domain terms)
- [ ] Principles section has 3–7 imperative bullets
- [ ] Workflow has numbered steps that a junior could follow without guessing
- [ ] Constraints lists what the skill must **never** do
- [ ] Every link in References/Examples/Assets/Scripts resolves to a real file
- [ ] Total token estimate is under 1200 (warning threshold)

### When to use which section

- **Principles** — universal rules that always apply ("write tests first")
- **Workflow** — the ordered steps Claude should follow when the skill activates
- **Constraints** — hard "never" rules ("never commit on red")
- **Hints** — situational branching ("if no tests directory exists, score code_quality ≤ 4"). Use hints, not principles, when guidance is conditional.
- **References** — long-form docs Claude reads only when a workflow step needs them. Use this to keep SKILL.md under the token budget.
- **Examples** — sample outputs that calibrate Claude's quality bar. The single highest-leverage thing you can add.
- **Assets** — static files (CSVs, templates, configs) that scripts or Claude reference at runtime.
- **depends_on** — declare another skill that should also be loaded when this one activates.

## Architecture

The project follows clean architecture with four layers:

```
src/skill_forge/
├── domain/           # Core: models, validators, ports (zero dependencies)
├── application/      # Use cases: create, lint, install, pack/unpack, publish, install-from-url
├── infrastructure/   # Adapters: filesystem, markdown, symlinks, zip packer, git registry, http fetcher
└── cli/              # Entry point: typer CLI + composition root
```

**Dependency rule:** dependencies point inward. Domain knows nothing about infrastructure. Use cases depend on ports (abstractions), not adapters (implementations). The CLI's `factory.py` is the composition root that wires everything together.

## Skill anatomy

A skill is a directory with this structure:

```
my-skill/
├── SKILL.md              # Core: description, principles, workflow, constraints
├── references/           # On-demand docs loaded only when a step needs them
├── scripts/              # Executable automation (generators, validators)
├── examples/             # Sample outputs showing expected format and quality
└── assets/               # Static files (CSVs, templates, images, config)
```

The `SKILL.md` frontmatter supports these fields:

```yaml
---
name: my-skill
description: |
  What this skill does and when to trigger it.
depends_on: other-skill (reason for dependency)
---
```

The body supports these sections: **Principles**, **Workflow/Instructions**, **Constraints**, **Hints**, **References**, **Examples**, **Assets**.

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

## Clean principles applied to skills

The key insight: the same principles that make code maintainable also make skills effective.

| Principle | Applied to skills |
|-----------|------------------|
| **SRP** | One skill, one responsibility. Split broad skills. |
| **OCP** | Extend via `references/`, don't bloat `SKILL.md`. |
| **ISP** | Keep the description lean — it's the skill's interface. |
| **DIP** | Skills define principles, not tool-specific commands. |

See `docs/clean-principles-for-skills.md` for the full guide, and `docs/getting-started.md` for a step-by-step walkthrough of the complete workflow (create → validate → install → test → iterate).

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

**Path-aware validators** (check the filesystem):

| Rule | Severity | What it checks |
|------|----------|---------------|
| `broken-reference-link` | error | Reference file doesn't exist on disk |
| `broken-example-link` | error | Example file doesn't exist on disk |
| `broken-asset-link` | error | Asset file doesn't exist on disk |
| `broken-script-link` | error | Script file doesn't exist on disk |

## Sharing skills across teams

Once a skill is good, you'll want to share it with your team. skill-forge ships with a `.skillpack` format — a single zip file containing one or more skills plus a JSON manifest — so you can distribute skills via Slack, Notion, email, GitHub releases, or any other channel that can move a file.

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

The pack command auto-derives its version from the skill itself, so you don't need to pass `--version` for single-skill packs. Bump the skill's frontmatter version when you ship a change, and the next `pack` will use the new value. Use `skill-forge create --version 0.1.0` to set an initial version when scaffolding.

```bash
# Bundle a single skill — version auto-derived from frontmatter
skill-forge pack output_skills/evaluation/ai-eng-evaluator \
  --output ./packs/
# → ./packs/ai-eng-evaluator-1.0.0.skillpack

# Bundle multiple skills together (explicit pack version recommended)
skill-forge pack \
  output_skills/evaluation/ai-eng-evaluator \
  output_skills/evaluation/user-story-test-cases \
  --name evaluation-bundle \
  --version 1.0.0 \
  --output evaluation-bundle.skillpack

# A teammate receives the file and unpacks it
skill-forge unpack evaluation-bundle.skillpack --output output_skills/

# Then lints and installs as usual
skill-forge lint output_skills/evaluation/ai-eng-evaluator
skill-forge install output_skills/evaluation/ai-eng-evaluator
```

Pack version precedence: an explicit `--version` always wins; otherwise a single-skill pack takes the skill's own version; multi-skill bundles without `--version` fall back to the default.

A `.skillpack` is just a zip you can inspect with any zip tool. The manifest at the root looks like:

```json
{
  "format_version": "1",
  "name": "evaluation-bundle",
  "version": "1.0.0",
  "author": "me@fernandosouto.dev",
  "created_at": "2026-04-06T13:43:36+00:00",
  "description": "AI engineering evaluator + user-story test-case generator",
  "tags": ["evaluation", "ai-engineering", "test-cases"],
  "owner": {"name": "Fernando Souto", "email": "me@fernandosouto.dev"},
  "skills": [
    {"category": "evaluation", "name": "ai-eng-evaluator", "version": "1.0.0"},
    {"category": "evaluation", "name": "user-story-test-cases", "version": "0.1.0"}
  ]
}
```

Each skill records its own version in the manifest, so a multi-skill bundle can mix and match. The optional `description`, `tags`, `owner`, and `deprecated` fields travel with the pack and become the defaults when you `publish` it to a registry — passing the same flags on `publish` overrides them. Older packs without these fields still unpack and install fine; the codec fills in safe defaults on read.

The packer excludes `__pycache__/`, `.DS_Store`, `.git/`, and `*.pyc` files by default. Unpack rejects archives with `../` paths to defend against zip-slip attacks.

For broader distribution, drop the `.skillpack` into a shared Git repo with CI running `skill-forge lint` on every PR. That gives you version control, code review, and rollback for free without standing up any extra infrastructure.

### Publishing to a git-backed registry

`skill-forge publish` turns any git repo into a free, CDN-backed skill registry. No GitHub Actions, no releases, no API server — just a normal repo where each pack lives at a stable raw URL. Teammates `install` directly from that URL.

A live example registry built with skill-forge lives at [github.com/ficiverson/skill-registry](https://github.com/ficiverson/skill-registry) — every URL in this section points at it, so you can `curl` the index, install a real pack, and see exactly what your own registry will look like.

The registry repo layout is fixed:

```
skill-registry/                 ← any git repo (GitHub, GitLab, self-hosted)
├── index.json                  ← machine catalog (auto-maintained)
└── packs/
    └── <category>/
        └── <name>-<version>.skillpack
```

**One-time setup** — create the registry repo and clone it locally:

```bash
git clone git@github.com:ficiverson/skill-registry.git
```

**Publish a pack** — point at the local clone and the public base URL:

```bash
skill-forge pack output_skills/evaluation/ai-eng-evaluator
# → ./ai-eng-evaluator-1.0.0.skillpack

skill-forge publish ./ai-eng-evaluator-1.0.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --message "ai-eng-evaluator 1.0.0" \
  --push
```

Output:

```
✔ Published ai-eng-evaluator v1.0.0
  path:    packs/evaluation/ai-eng-evaluator-1.0.0.skillpack
  sha256:  10d16ba0…
  git:     committed
  git:     pushed

  Install URL:
  https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack

  Teammates can install with:
    skill-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack --sha256 10d16ba0db7b768219d0adb6c3dd8ea68b62e9f719a0132fdcd2bcf10271c0e6
```

The publisher copies the pack into `packs/<category>/<name>-<version>.skillpack`, regenerates `index.json`, commits, and (with `--push`) pushes. Drop `--push` if you'd rather review the diff first; the commit is already on your local branch.

**Install from a URL** — `skill-forge install` accepts a URL alongside the existing local-path form:

```bash
# Direct URL — works for any https:// pointing at a .skillpack
skill-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack

# With sha256 verification (recommended — digest from index.json)
skill-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/evaluation/ai-eng-evaluator-1.0.0.skillpack \
  --sha256 10d16ba0db7b768219d0adb6c3dd8ea68b62e9f719a0132fdcd2bcf10271c0e6

# Local install still works exactly as before
skill-forge install output_skills/evaluation/ai-eng-evaluator
```

Behind the scenes the URL form fetches the pack to a temp file, verifies the sha256 if you supplied one, unpacks it via the existing `unpack` flow, and then installs each contained skill into `~/.claude/skills/` (or `.claude/skills/` with `--scope project`).

**Private repos** — set `GITHUB_TOKEN` in your environment and the fetcher will pass it as a `token` Authorization header on `raw.githubusercontent.com` requests, so private registries work without any extra configuration.

**Integrity** — every published pack records its sha256 in `index.json`, and `install --sha256 ...` verifies the download against that digest before unpacking. The fetcher also caps downloads at 50 MB by default to refuse runaway responses.

**Why this beats the alternatives**

- vs `gh release`: no per-version release noise, plain file URLs are simpler to share, and the registry is one browsable folder.
- vs S3 / R2: no AWS account, no IAM, no boto3 dependency. Free for public registries.
- vs Slack uploads: discoverable. New teammates find every published skill in one place instead of digging through channel history.
- vs synced folders: works across orgs and works for open-source distribution, not just intra-team.

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

# Run tests (178 tests)
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
