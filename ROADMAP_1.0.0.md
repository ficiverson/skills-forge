# skills-forge — Roadmap to v1.0.0

> **Current stable:** v0.3.0  
> **Target GA:** v1.0.0  
> **Approach:** Five milestone releases (v0.4 → v0.8) converging on a production-grade,
> fully documented, 95%-covered toolkit with a stable public API contract.

---

## What changed from the v0.2.0 roadmap

**Removed from scope (post-v1.0 parking lot):**
- *BKL-006 · Registry search* — The registry is a static GitHub repo; discovery belongs
  to the website (`index.html`) and GitHub search, not the CLI. A client-side search
  wrapper adds no value that `grep` on a local `index.json` doesn't already provide.
- *BKL-009 · Registry index caching* — Only meaningful as infrastructure for search.
  Removed with it.
- *BKL-014 · OpenAPI/Actions exporter* — Inspecting Python type annotations to
  auto-generate a FastAPI server is a different product (skills-forge as a deployment
  platform). Excellent long-term vision; not right for v1.0.
- *BKL-020 · Pre/post install hooks* — Arbitrary script execution at install time
  requires a sandboxing model that deserves its own design phase. Security-first approach
  means this ships only when the model is right.

**Corrected scopes based on code audit:**
- *BKL-010 · Private auth* — `GITHUB_TOKEN` env-var support already exists in
  `http_pack_fetcher.py`. Scope reduced to first-class config file support.
- *BKL-013 · SHA256 on install-from-url* — Verification logic already exists in
  the use case; gap is a missing warning when `--sha256` is omitted and no E2E test.

**New items added:**
- *NEW-001 · `skills-forge info`* — Per-skill detail view (version, targets, deps).
- *NEW-002 · `list --filter`* — Local filtering of installed skills; replaces the
  registry search use case for the installed-skills workflow.
- *NEW-003 · `requires-forge` frontmatter* — Minimum CLI version constraint in
  `SKILL.md` so old CLI versions fail fast instead of silently misbehaving.
- *NEW-004 · `skills-forge diff`* — Show what changed between the installed version
  and the registry latest before running `update`.
- *NEW-005 · Evals as first-class skill component* — `evals/evals.json` becomes a
  formal part of the skill spec: domain model, parser, linter, scaffold, and a new
  `skills-forge test` command that executes evals against Claude and grades assertions.

---

## Milestones Overview

| Version | Theme | Scope |
|---------|-------|-------|
| v0.4.0 | **Quality & Configuration Baseline** | Evals first-class + `test` command, multi-registry config, SHA256 warning, `requires-forge` |
| v0.5.0 | **Developer Experience** | `update`, `doctor`, `info`, `list --filter`, `init` improvements |
| v0.6.0 | **Universal Platform Support** | 3 new export formats, `allowed-tools`, `diff` command |
| v0.7.0 | **Registry Governance** | Yank, deprecation, private auth config |
| v0.8.0 | **Production Hardening** | 95% coverage, E2E tests, error quality, docs site, CI |
| **v1.0.0** | **General Availability** | Stable API, CHANGELOG, migration guide, PyPI release |

---

## v0.4.0 — Quality & Configuration Baseline

The goal of this milestone is to formalise skill quality (evals) and make
skills-forge safe and ergonomic for teams with multiple registries and CI environments.

### NEW-005 · Evals as first-class skill component + `skills-forge test`
**Priority:** High · **Effort:** M

`evals/` is the missing fourth pillar alongside `scripts/`, `references/`, and
`assets/`. The packer already bundles whatever it finds in the skill directory, so
`evals/evals.json` is technically in every `.skillpack` today — but it is invisible
to the domain model, parser, linter, and CLI. This item makes it real.

**Skill directory layout after this change:**
```
skill-name/
├── SKILL.md               # instructions (required)
├── evals/
│   ├── evals.json         # test cases with assertions (new, formal)
│   └── fixtures/          # input files referenced by test cases
├── scripts/               # automation scripts
├── references/            # on-demand reference docs
└── assets/                # templates, icons, fonts
```

**Domain model additions:**
```python
@dataclass(frozen=True)
class EvalAssertion:
    id: str
    text: str            # human-readable criterion (used by llm-judge)
    type: str            # "contains" | "not-contains" | "regex" | "llm-judge"
    expected: str = ""   # pattern/string for contains/not-contains/regex

@dataclass(frozen=True)
class EvalCase:
    id: int
    prompt: str
    expected_output: str        # narrative description of the ideal output
    assertions: list[EvalAssertion] = field(default_factory=list)
    files: list[str] = field(default_factory=list)  # fixture paths

# Added to Skill:
evals: list[EvalCase] = field(default_factory=list)
```

**`evals/evals.json` schema:**
```json
{
  "skill_name": "my-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "The user prompt to test",
      "expected_output": "Narrative description of what a good response looks like",
      "assertions": [
        {
          "id": "summary-present",
          "text": "Response includes a summary section",
          "type": "contains",
          "expected": "## Summary"
        },
        {
          "id": "quality-check",
          "text": "Response is professional and complete",
          "type": "llm-judge"
        }
      ],
      "files": ["fixtures/sample.pdf"]
    }
  ]
}
```

**New `skills-forge test` command:**
```bash
skills-forge test output_skills/evaluation/ai-eng-evaluator/
# Running 3 evals for ai-eng-evaluator…
#   eval-1 basic-submission      ✅  4/4 assertions  (12.3s)
#   eval-2 senior-candidate      ✅  4/4 assertions  (14.1s)
#   eval-3 edge-case-empty-repo  ⚠️  3/4 assertions  (9.8s)
#     ✘ report-pdf-generated: "output.pdf" not found in outputs
# Pass rate: 92%  (11/12 assertions)  exit 1

skills-forge test output_skills/ --filter "evaluation"   # run evals for a category
skills-forge test my-skill.skillpack                     # run from a packed skill
```

Acceptance criteria:
- `evals/evals.json` is parsed into `Skill.evals`; parse errors produce clear lint issues
- `skills-forge create` scaffolds an `evals/evals.json` with one example eval case
- `lint` warns (not errors) when a skill has zero evals — evals are good practice, not mandatory
- `lint` errors on malformed `evals.json` (invalid JSON, missing required fields)
- `skills-forge test` runs each eval case using Claude CLI (`claude -p`), grades assertions,
  prints per-eval and per-assertion results, exits non-zero if any assertion fails
- `contains` / `not-contains` / `regex` assertions graded programmatically
- `llm-judge` assertions graded by a second Claude call with the assertion text as criterion
- Evals are **excluded** from all platform exports (system-prompt, gpt-json, etc.) —
  they are quality tooling, not instructions
- `list` and `info` show eval count: `(3 evals)` alongside token estimate

---

### BKL-007 · Multi-registry config file
**Priority:** High · **Effort:** M

A config file at `~/.skills-forge/config.toml` persists named registries so users
never have to pass a full URL again.

```toml
[registries]
public   = "https://raw.githubusercontent.com/ficiverson/skill-registry/main"
internal = "https://raw.githubusercontent.com/yourorg/skills/main"

[defaults]
registry = "public"
target   = "claude"
```

New commands:
```bash
skills-forge registry add internal https://…
skills-forge registry list
skills-forge registry remove internal
skills-forge registry set-default internal
```

Acceptance criteria:
- All commands that currently accept `-r <url>` or `-u <url>` read from config when
  the flag is omitted
- Config validated on load; clear errors for malformed TOML or unknown fields
- `~/.skills-forge/config.toml` created with public registry pre-configured on first
  `skills-forge init`

### BKL-010 · Private registry auth (first-class config)
**Priority:** High · **Effort:** S

`GITHUB_TOKEN` env-var support already exists in `http_pack_fetcher.py`. This item
promotes it to a first-class config option so teams can configure auth per-registry
without exporting env vars in every shell.

```toml
[registries.internal]
url   = "https://raw.githubusercontent.com/yourorg/skills/main"
token = "${SKILLS_FORGE_INTERNAL_TOKEN}"   # env-var expansion supported
```

Acceptance criteria:
- Token read from config (with env-var expansion), then env var, then CLI flag
- Token never written to log output, error messages, or stack traces
- Auth failure distinguishes 401 from 404 from network error with actionable message

### BKL-013 · SHA256 warning + E2E test for install-from-url
**Priority:** High · **Effort:** S

The `--sha256` flag exists and verification fires when provided. Two gaps remain:

1. When `--sha256` is omitted for a remote install, the CLI silently proceeds.
   A prominent warning should appear — remote installs without digest verification
   are a supply-chain risk.
2. No end-to-end test exercises the full fetch → verify → install path.

Acceptance criteria:
- `skills-forge install <https-url>` without `--sha256` prints a visible warning:
  `⚠ Installing without SHA256 verification — supply the digest with --sha256 for
  secure installs`
- `--sha256 <wrong>` prints a clear mismatch error and exits non-zero
- At least two E2E tests: correct digest succeeds, wrong digest fails

### NEW-003 · `requires-forge` frontmatter field
**Priority:** Medium · **Effort:** S

Skills that use frontmatter fields introduced in a specific CLI version should declare
a minimum version requirement. Without this, an old CLI silently ignores new fields.

```yaml
---
name: my-skill
requires-forge: ">=0.4.0"
---
```

Acceptance criteria:
- Parser stores the constraint in the domain model (`Skill.requires_forge: str | None`)
- `install` checks the running CLI version and exits with a clear upgrade message if
  the constraint is not satisfied
- `lint` warns when `requires-forge` is absent on a skill that uses fields added after
  v0.3.0 (`depends_on`, `allowed-tools`)

---

## v0.5.0 — Developer Experience

The commands that developers run every day: checking what's installed, keeping skills
up-to-date, diagnosing problems.

### BKL-019 · `skills-forge update` command
**Priority:** High · **Effort:** L

```bash
skills-forge update                        # update all installed skills
skills-forge update python-tdd             # update one skill
skills-forge update --dry-run              # show what would change
skills-forge update --registry internal    # target a specific registry
```

Acceptance criteria:
- Compares installed version against registry latest using semantic versioning
- Skips yanked and deprecated versions
- `--pin <version>` prevents a skill from being auto-updated
- Prints what changed (description, version, platforms) before updating, then prompts
  for confirmation unless `--yes` is passed
- Respects `requires-forge` constraints on the candidate version

### BKL-021 · `skills-forge doctor` command
**Priority:** Medium · **Effort:** M

```bash
skills-forge doctor
# ✔ claude target:  4 skills installed, 0 broken symlinks
# ✔ agents target:  4 skills installed, 0 broken symlinks
# ⚠ python-tdd@1.0.0 — registry has 1.2.0 available (run: skills-forge update python-tdd)
# ✘ ai-eng-evaluator: dependency 'pdf-tools@1.0.0' not installed
# ✘ .claude/skills/broken-skill → target does not exist (dangling symlink)
```

Acceptance criteria:
- Scans all target directories for broken symlinks
- Checks `depends_on` resolution for every installed skill
- Compares installed versions against registry and flags available updates
- Exits non-zero if any ✘ items found (useful as a CI health check)

### NEW-001 · `skills-forge info <skill-name>` command
**Priority:** Medium · **Effort:** S

Show full details for a single installed or registry skill without parsing the entire
index.

```bash
skills-forge info ai-eng-evaluator
#   name:        ai-eng-evaluator
#   version:     1.0.0  (latest)
#   category:    evaluation
#   installed:   claude (global), agents (global)
#   depends_on:  (none)
#   platforms:   claude, gemini, codex, vscode, agents
#   description: Evaluates AI engineering submissions …
#   registry:    public
```

Acceptance criteria:
- Works for installed skills (reads from symlink target) and registry skills (reads
  from `index.json`)
- Shows installed targets detected by symlink scan
- Flags when installed version differs from registry latest

### BKL-008 · Improve `list` output + `--filter` flag
**Priority:** Low · **Effort:** S

Current output: name + token estimate. Extended output:

```
  ✔ evaluation/ai-eng-evaluator  @ 1.0.0  (~640 tokens)  [claude, agents]  2026-04-09
  ✔ development/python-tdd       @ 1.2.0  (~180 tokens)  [claude]          2026-04-07
```

New filter flag:
```bash
skills-forge list --filter "api"       # name or description contains "api"
skills-forge list --tag testing        # skills with this tag
skills-forge list --category dev       # skills in this category
```

Replaces the removed registry-search use case for the installed-skills workflow.

### BKL-022 · `skills-forge init` improvements
**Priority:** Low · **Effort:** S

- Detect installed tools (Claude Code, Gemini CLI) and pre-configure default targets
- Write a starter `~/.skills-forge/config.toml` with the public registry
- Offer to install a starter skill from the public registry as a "hello world"

---

## v0.6.0 — Universal Platform Support

Complete the export matrix and honour the full agentskills.io spec.

### BKL-015 · Mistral Agents export format
**Priority:** Medium · **Effort:** M

Mistral Agents use a `system` prompt + `tools` JSON array. Adds `--format mistral-json`
to the export command. Reference: `docs/universal-export-research.md`.

### BKL-016 · Vertex AI / Gemini API export format
**Priority:** Medium · **Effort:** S

Gemini API uses a `system_instruction` field. Adds `--format gemini-api`.

### BKL-017 · OpenAI Assistants API export format
**Priority:** Low · **Effort:** S

The Assistants API uses an `instructions` parameter + optional knowledge-base file
upload. Adds `--format openai-assistants`.

### BKL-018 · `allowed-tools` frontmatter support
**Priority:** Medium · **Effort:** S

The agentskills.io spec defines `allowed-tools` to restrict which agent tools are
active when a skill is loaded. Parser currently ignores it. Store in domain model,
write through to installed `SKILL.md`, and include in all export formats that support
a tool-restriction concept.

### NEW-004 · `skills-forge diff <skill-name>` command
**Priority:** Low · **Effort:** S

```bash
skills-forge diff python-tdd
# python-tdd: installed 1.0.0 → registry 1.2.0
# --- description (1.0.0)
# +++ description (1.2.0)
#  Use for TDD with Python.
# +Triggers: pytest, test-first, red-green-refactor, coverage.
```

Shows a human-readable diff of SKILL.md frontmatter and description between the
installed version and the registry latest. Pairs with `update` to let developers
review changes before accepting them.

---

## v0.7.0 — Registry Governance

Tools for registry maintainers to manage the health of the published skill catalogue.

### BKL-011 · Skill yank
**Priority:** Medium · **Effort:** M

A published version containing a critical bug should be removable from discovery
without destroying the binary (to preserve reproducible installs).

```bash
skills-forge yank my-skill@1.0.0 \
  --registry internal \
  --reason "Security: prompt injection vector"
```

Acceptance criteria:
- Yanked versions hidden from `list --remote` and `update` resolution
- `install my-skill` skips yanked versions when resolving latest
- `install my-skill@1.0.0` installs a yanked version with a prominent warning
- `index.json` carries `yanked: true` and `yank_reason` per version entry
- `doctor` flags installed skills that are yanked

### BKL-012 · Skill deprecation
**Priority:** Low · **Effort:** S

Soft deprecation for skills that are superseded but not harmful. Deprecated skills
still appear in listings with a notice and a `replaced_by` pointer.

```bash
skills-forge deprecate my-skill@1.x \
  --replaced-by my-skill@2.0.0 \
  --message "Replaced by my-skill v2 which supports all platforms"
```

---

## v0.8.0 — Production Hardening

The quality bar that justifies a stable `v1.0.0` label.

### BKL-023 · Reach 95% test coverage
**Priority:** High · **Effort:** L

Current coverage: 92%. Key modules below target:
- `export_skill.py` — error branches
- `install_skill.py` — URL install path
- `http_pack_fetcher.py` — network error handling
- `registry_index_codec.py` — codec edge cases and error paths
- `lint_service.py` — audit whether it is exercised or delete it *(folds BKL-027)*

Acceptance criteria:
- `pytest --cov=skill_forge --cov-fail-under=95` passes in CI
- All new code added in v0.4–v0.7 covered to the same bar

### BKL-024 · End-to-end integration test suite
**Priority:** High · **Effort:** L

The current suite is unit-only with stub adapters. Add an integration layer that
exercises the full pipeline against a real filesystem and a local mock HTTP registry
(no network):

1. `create → lint → pack → publish` to temp registry → `info` → `install` → `export`
   (all formats) → `uninstall`
2. `install-from-url` with correct SHA256 passes; wrong SHA256 fails
3. Dependency resolution with a two-skill dependency graph
4. `update` detects newer version, updates, `diff` shows the change
5. `yank` hides a version; `update` skips it

### BKL-025 · Error message quality audit
**Priority:** Medium · **Effort:** M

Systematically review all `ValueError`, `FileNotFoundError`, and `typer.Exit` call
sites. Every user-facing error must:
- State what went wrong in plain English (no raw tracebacks for user errors)
- Say what the user should do next
- Include the relevant path, version, or flag in the message
- Follow a consistent format: `✘ <what went wrong> — <how to fix it>`

### BKL-026 · Documentation site
**Priority:** High · **Effort:** L

Publish `docs/` to GitHub Pages (MkDocs Material). Required pages:
- Getting started (working in < 5 minutes)
- CLI reference (all commands, flags, exit codes, examples)
- `SKILL.md` format reference (all frontmatter fields, their types, defaults)
- Registry setup guide (public + private)
- Export formats guide (all formats, when to use each)
- Migration guide (v0.x → v1.0)
- Contributing guide

### BKL-028 · GitHub Actions CI pipeline hardening
**Priority:** Medium · **Effort:** M

- Run ruff + mypy + pytest on every PR against Python 3.10, 3.11, and 3.12
- Enforce 95% coverage as a required check
- Run integration test suite against a mock registry (no network access)
- Auto-publish to PyPI on tagged releases via OIDC trusted publishing
- Release preflight skill runs as a pre-release gate check

---

## v1.0.0 — General Availability

### BKL-029 · Stable public API contract
**Priority:** High · **Effort:** M

Define and document the public Python API surface: use cases, domain model, port
interfaces. Mark internal implementation details with `_` prefixes. Commit to
semantic versioning from this point: no breaking changes without a major bump.

The public surface is:
- All classes in `skill_forge/domain/model.py`
- All use case request/response dataclasses
- All port interfaces in `skill_forge/domain/ports.py`
- The `skills-forge` CLI (all commands and flags documented here)

### BKL-030 · CHANGELOG.md
**Priority:** Medium · **Effort:** S

Full changelog from v0.1.0 through v1.0.0 following the
[Keep a Changelog](https://keepachangelog.com) format. Linked from README and docs.

### BKL-031 · v0.x → v1.0 migration guide
**Priority:** Medium · **Effort:** S

Document every breaking change from v0.2 through v0.9 with before/after examples.
Key changes to document:
- `export` now requires `.skillpack` input (v0.2.0)
- Multi-registry config replaces bare URL flags (v0.4.0)
- `requires-forge` constraint enforcement (v0.4.0)

### BKL-032 · PyPI release and announcement
**Priority:** High · **Effort:** S

Tag `v1.0.0`, publish to PyPI via OIDC trusted publishing, post release notes to
GitHub Releases, publish the LinkedIn + blog post campaign.

---

## Post-v1.0 Parking Lot

Items deferred because they represent significant scope expansion or require design
work not appropriate for a GA release:

| Item | Why deferred |
|------|-------------|
| OpenAPI/Actions exporter | Turns skills-forge into a deployment platform; different product surface |
| Pre/post install hooks | Arbitrary script execution requires a sandboxing model to be designed first |
| Registry search CLI | Discovery belongs to website/clients; the static registry model is intentional |
| Registry index caching | Was only meaningful as search infrastructure |

---

## Backlog Summary

| ID | Title | Milestone | Priority | Effort |
|----|-------|-----------|----------|--------|
| NEW-005 | Evals first-class + `skills-forge test` | v0.4.0 | High | M |
| BKL-007 | Multi-registry config file | v0.4.0 | High | M |
| BKL-010 | Private registry auth (config first-class) | v0.4.0 | High | S |
| BKL-013 | SHA256 warning + E2E test | v0.4.0 | High | S |
| NEW-003 | `requires-forge` frontmatter field | v0.4.0 | Medium | S |
| BKL-019 | `skills-forge update` command | v0.5.0 | High | L |
| BKL-021 | `skills-forge doctor` command | v0.5.0 | Medium | M |
| NEW-001 | `skills-forge info` command | v0.5.0 | Medium | S |
| BKL-008 | Improve `list` output + `--filter` | v0.5.0 | Low | S |
| BKL-022 | `skills-forge init` improvements | v0.5.0 | Low | S |
| BKL-015 | Mistral Agents export format | v0.6.0 | Medium | M |
| BKL-016 | Vertex AI / Gemini API export format | v0.6.0 | Medium | S |
| BKL-017 | OpenAI Assistants API export format | v0.6.0 | Low | S |
| BKL-018 | `allowed-tools` frontmatter support | v0.6.0 | Medium | S |
| NEW-004 | `skills-forge diff` command | v0.6.0 | Low | S |
| BKL-011 | Skill yank | v0.7.0 | Medium | M |
| BKL-012 | Skill deprecation | v0.7.0 | Low | S |
| BKL-023 | Reach 95% test coverage (incl. lint_service audit) | v0.8.0 | High | L |
| BKL-024 | End-to-end integration test suite | v0.8.0 | High | L |
| BKL-025 | Error message quality audit | v0.8.0 | Medium | M |
| BKL-026 | Documentation site | v0.8.0 | High | L |
| BKL-028 | GitHub Actions CI pipeline hardening | v0.8.0 | Medium | M |
| BKL-029 | Stable public API contract | v1.0.0 | High | M |
| BKL-030 | CHANGELOG.md | v1.0.0 | Medium | S |
| BKL-031 | v0.x → v1.0 migration guide | v1.0.0 | Medium | S |
| BKL-032 | PyPI release and announcement | v1.0.0 | High | S |

**Total in scope:** 26 items across 6 milestones  
**Deferred to post-v1.0:** 4 items  
**Effort key:** S = 1–2 days · M = 3–5 days · L = 1–2 weeks
