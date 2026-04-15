# skills-forge — Release Notes

---

## v1.0.0 — 2026-04-15

**First stable release. Production/Stable on PyPI.**

This release promotes skills-forge from Beta to Production/Stable. It closes all
remaining test coverage gaps identified by an independent assessment, bumps all
bundled skills to v1.0.0, and verifies the full registry is consistent before the
PyPI launch.

### What's new

**Test coverage closure**

An independent testing assessment identified three gaps in v0.8.0. All three are
now resolved:

- `lint_service.py` — 0% → 100% (shipped in v0.8.0, assessment ran against older state)
- `cli/main.py` — 43% → 96% — 25 new targeted tests covering every previously-uncovered
  branch: empty list, export FileNotFoundError, uninstall invalid target/not-found, init
  config creation + tool detection hints (single/multi/none), info registry fallback /
  depends_on / requires_forge / up-to-date / deprecated, doctor registry fallback, update
  no-registry error + confirm abort, diff no-registry actionable error, test command eval
  display (pass / fail / error / no-evals skip)
- `cli/factory.py` — 71% → 99% — `build_fetcher` per-registry token resolution tested

Overall: **665 tests at 97% coverage** (up from 640 tests / 95% in v0.8.0).

**Skills bumped to v1.0.0**

- `release-preflight@1.0.0` — published to registry
- `user-story-test-cases@1.0.0` — published to registry
- `ai-eng-evaluator` already at v1.1.0 — no change needed

**Registry verified**

All 17 packs in the skill registry pass the full consistency check:
SHA256, size, manifest version, export formats, and platform coverage.

**PyPI metadata**

- `Development Status :: 4 - Beta` → `Development Status :: 5 - Production/Stable`
- `version = "0.8.0"` → `version = "1.0.0"`

### Upgrade

```bash
pip install --upgrade skills-forge
# or from source:
pip install -e ".[dev]"
```

---

## v0.8.0 — 2026-04-11

This release is the **production readiness** milestone: 95%+ test coverage, an
end-to-end integration test suite, actionable error messages, a MkDocs
documentation site, and a hardened GitHub Actions CI pipeline.

### BKL-023 — 95%+ test coverage

The test suite grew from ~257 tests at 83% coverage to **640 tests at 95.42%**
coverage. Systematic gap-filling targeted previously untested modules:

- `subprocess_claude_runner.py` — 39% → 100%
- `lint_service.py` — 0% → 100%
- `cli/main.py` — 43% → 88%
- `cli/factory.py` — 71% → 97%

New test files: `test_subprocess_claude_runner.py`, `test_lint_service.py`,
`test_cli_extended.py`, `test_coverage_gaps.py`.

### BKL-024 — End-to-end integration test suite

Five full-workflow E2E scenarios in `tests/e2e/test_e2e_scenarios.py`:

1. **Full lifecycle** — create → lint → pack → unpack → install → export (all formats)
2. **SHA256 verification** — correct hash installs; wrong hash aborts
3. **Dependency graph** — provider + consumer: info shows deps, pack bundles both
4. **Update / diff** — v0.1.0 installed, v0.2.0 in registry; update detects it, diff shows change
5. **Yank** — yank a version; update skips it and targets the next non-yanked latest

### BKL-025 — Error message quality audit

All key error paths now include:
- **What** failed (with the specific value that caused it)
- **Why** it failed (the constraint violated)
- **How** to fix it (specific CLI command or flag to use)

Improved messages in: `diff_skill`, `update_skill`, `publish_skill`,
`git_registry_publisher`, `symlink_installer`, `zip_skill_packer`.

### BKL-026 — MkDocs documentation site

Complete documentation at `docs/`:

- **Home** — overview, quick start, feature list, architecture diagram
- **Getting started** — install, create, lint, install, export
- **Command reference** — all 16 commands documented
- **Skill anatomy** — frontmatter, body structure, description guidelines, token budgets
- **Export formats** — all 8 formats with platform-specific setup instructions
- **Registry & publishing** — Git-backed registry layout, publish workflow, yank/deprecate
- **Install targets** — all 5 targets, scope semantics, doctor health check
- **Clean architecture** — layer diagram, dependency rule, use case anatomy, testing pyramid
- **Universal export** — platform categories, export pipeline, MCP server export
- **Contributing** — setup, conventions, adding exporters/validators, PR checklist
- **Changelog** — full history from v0.1.0 to v0.8.0

### BKL-028 — GitHub Actions CI hardening

`.github/workflows/ci.yml` now has four jobs:

| Job | What it does |
|-----|-------------|
| `test` | Runs pytest with 95% coverage gate on Python 3.10, 3.11, 3.12 |
| `lint` | Ruff lint + format check + mypy type check |
| `e2e` | Runs all 5 E2E scenarios |
| `docs` | Builds MkDocs with `--strict` |
| `publish-docs` | Deploys to GitHub Pages on `main` push |

Concurrency cancellation prevents queue pile-ups on rapid pushes.

### Other changes

- `pyproject.toml` version bumped to `0.8.0`
- Development status classifier updated from Alpha → Beta
- `mkdocs-material` and `mkdocstrings[python]` added to dev dependencies

---

## v0.7.0 — 2026-04-11

This release ships the Registry Governance milestone: version yanking, skill
deprecation, and a new doctor check that warns when an installed version has been
yanked in the upstream registry.

### New features

**BKL-011 — `skills-forge yank` — version yanking**

Registry maintainers can now retract a specific version of a skill without
removing it entirely. A yanked version remains visible in the index but is
excluded from fresh installs and `update` suggestions.

```
skills-forge yank python-tdd@1.0.0 -r ./registry-clone --reason "security: injection vector"
skills-forge yank python-tdd@1.0.0 -r ./registry-clone --push
```

Yanked entries carry an optional `yank_reason` field in `index.json`. When the
latest published version is yanked, `latest` automatically falls back to the
newest non-yanked version. If every version is yanked the field retains the last
known version (safe fallback).

**BKL-012 — `skills-forge deprecate` — skill-level deprecation**

Whole skills can be marked deprecated with an optional replacement pointer and
human-readable message:

```
skills-forge deprecate old-skill -r ./registry-clone \
    --replaced-by new-skill \
    --message "Superseded by new-skill v2, which supports tool calls"
```

The `deprecated`, `replaced_by`, and `deprecation_message` fields are stored in
`index.json` and surfaced by `skills-forge info` as a highlighted deprecation
notice.

**Doctor check #5 — yanked-version warning**

`skills-forge doctor` now reports a `yanked-version` warning (severity: WARNING)
when the installed version of a skill has been marked yanked in the upstream
registry, including the yank reason when present:

```
⚠  python-tdd: Installed v1.0.0 has been yanked — security: injection vector
   (run: skills-forge update python-tdd)
```

### Domain model changes

`IndexedVersion` gains `yanked: bool` and `yank_reason: str` fields.
`IndexedSkill` gains `deprecated: bool`, `replaced_by: str`, and
`deprecation_message: str` fields. All new fields have safe defaults and the
codec handles older `index.json` files that omit them without error.

Two new immutable operations on `RegistryIndex`:

- `yank_version(name, version, reason="") -> RegistryIndex`
- `set_skill_metadata(name, *, deprecated, replaced_by, deprecation_message) -> RegistryIndex`

`PackPublisher` port gains the abstract method
`update_index(index, message, push) -> bool`, implemented by
`GitRegistryPublisher`.

### Tests

36 new tests across three new test modules:

- `tests/application/test_yank_skill.py` — `RegistryIndex.yank_version()` + `YankSkill` use case
- `tests/application/test_deprecate_skill.py` — `RegistryIndex.set_skill_metadata()` + `DeprecateSkill` use case
- `tests/application/test_governance.py` — codec roundtrip for all new fields + doctor yanked-version integration

Total test count: **504**.

---

## v0.6.0 — 2026-04-11

This release ships three new export formats targeting API platforms, `allowed-tools`
frontmatter support (agentskills.io spec), and the `diff` command for comparing
installed skills against the registry.

### New features

**BKL-018 — `allowed-tools` frontmatter support**

Skills can now declare which agent tools they need using the agentskills.io
`allowed-tools` field:

```yaml
---
name: my-skill
allowed-tools: [Bash, Read, Write]
---
```

The field survives parse → model → render roundtrips and is reflected in all
export formats that carry tool-restriction metadata (Mistral, Gemini API,
OpenAI Assistants).

**BKL-015 — `--format mistral-json` export**

Exports a skill as a Mistral Agents API configuration JSON (`<slug>.mistral.json`).
The `system` field holds the full skill body; when `allowed-tools` is set, a
`tools` array of stub function definitions is included.

```
skills-forge export ./path/to/skill --format mistral-json
```

**BKL-016 — `--format gemini-api` export**

Exports a skill as a Vertex AI / Gemini API `GenerateContentRequest`-compatible
JSON (`<slug>.gemini-api.json`) with a `system_instruction` block.

```
skills-forge export ./path/to/skill --format gemini-api
```

**BKL-017 — `--format openai-assistants` export**

Exports a skill as an OpenAI Assistants API `CreateAssistant`-compatible JSON
(`<slug>.assistants.json`) with `instructions`, `model`, and `tools`.

```
skills-forge export ./path/to/skill --format openai-assistants
```

**NEW-004 — `skills-forge diff <skill-name>`**

Compare the locally installed SKILL.md against the latest version in the
registry. Shows a unified diff and exits 1 when differences are found:

```
skills-forge diff python-tdd \
    --registry https://raw.githubusercontent.com/org/skill-registry/main

# Narrower context
skills-forge diff python-tdd --context 1 -r https://…/main
```

### Internal changes

- `ExportFormat` enum gains `MISTRAL_JSON`, `GEMINI_API`, `OPENAI_ASSISTANTS` values.
- `Skill` domain model gains `allowed_tools: list[str]` field and `has_allowed_tools` property.
- `MarkdownSkillParser` parses `allowed-tools: [Tool1, Tool2]` inline YAML list syntax.
- `MarkdownSkillRenderer` writes `allowed-tools: [...]` when the list is non-empty.
- New `DiffSkill` use case with `DiffRequest`/`DiffResponse`; registered in `factory.py`.
- 3 new exporter classes in `infrastructure/adapters/exporters/`.
- **468 tests** — 52 new tests added for exporters, parser/renderer roundtrip, and diff use case.

---

## v0.5.0 — 2026-04-11

This release ships the discovery and maintenance layer: `info`, `doctor`, and
`update` commands, improved `list` filtering, and smarter `init` tool detection.

### New features

**NEW-001 — `skills-forge info <skill-name>`**

Display detailed information about an installed skill:

```
skills-forge info my-skill
skills-forge info my-skill --registry https://raw.githubusercontent.com/…/main
```

Reports version, category, token budget, eval count, dependency list,
`requires-forge` constraint, and the paths where the skill is installed (with
a `broken` flag when a symlink points to a missing target). When `--registry`
is provided (or a default registry is configured), the command fetches the
registry index and prints whether the installed version is up to date.

**BKL-021 — `skills-forge doctor`**

Health-sweep all installed skills:

```
skills-forge doctor
skills-forge doctor --no-registry   # offline-safe
```

Four checks are performed in order: (1) broken symlinks (ERROR), (2) missing
SKILL.md (ERROR), (3) unresolved `depends_on` entries (WARNING), (4) stale
versions against the registry (WARNING, skipped with `--no-registry`). Exits
non-zero when any ERROR-severity issue is found.

**BKL-019 — `skills-forge update [name]`**

Compare installed versions against the registry and install newer packs:

```
skills-forge update             # update all installed skills
skills-forge update my-skill   # update a specific skill
skills-forge update --dry-run  # preview available updates without installing
skills-forge update --yes      # skip per-skill confirmation
skills-forge update --pin 1.2.0
```

Downloads and installs each newer version using `InstallFromUrl` (same
fetch + sha256-verify + unpack + install pipeline as `install`). Respects
`--scope`, `--target`, and `--registry` flags.

**BKL-008 — `skills-forge list` filtering**

Three new optional flags for `list` (and `list-skills`):

```
skills-forge list --category productivity
skills-forge list --tag email
skills-forge list --filter grooming
```

`--category` matches the skill's category exactly (case-insensitive).
`--tag` and `--filter` do substring matches against name and description.

The list output now includes the skill version, eval count, and dependency
list for each skill.

**BKL-022 — `skills-forge init` tool detection**

`skills-forge init` now detects which agent-CLI tools are available on PATH
(`claude`, `gemini`, `codex`, `code`) and records them in the generated
`CLAUDE.md`. When multiple tools are found it hints at `--target all`.

### New port method

`SkillInstaller.scan_all_targets(scope) → dict[InstallTarget, list[Path]]`
is now part of the abstract port. `SymlinkSkillInstaller` scans every
applicable target directory for the given scope (VSCODE excluded at global).

### Test coverage

416 tests · 0 failures (up from 383 in v0.4.0)

---

## v0.4.0 — 2026-04-10

This release delivers five milestone items: evals as a first-class skill component,
compatibility constraints via `requires-forge`, a multi-registry configuration system,
per-registry auth tokens with env-var expansion, and secure remote install verification.

### New features

**NEW-005 — Evals as a first-class skill component**

Skills can now ship their own test suite inside an `evals/` subdirectory.

`evals/evals.json` is a JSON array of eval case objects, each with `id`, `prompt`,
`expected_output`, `assertions[]`, and `files[]`. Supported assertion types: `contains`,
`not-contains`, `regex`, `llm-judge` (programmatic for the first three; second Claude
call for `llm-judge`).

New command:

```bash
skills-forge test <skill-path> [-t <timeout>]
```

Runs every eval case and prints a per-assertion pass/fail table.

`skills-forge create` now generates an `evals/` directory with a starter `evals.json`
and an empty `evals/fixtures/` folder. `skills-forge list` shows an `[evals]` tag for
skills that have at least one eval case. The `evals/` directory is intentionally excluded
from all export formats.

New lint rules: `validate_evals_schema` (ERROR on malformed JSON or unknown assertion
types), `validate_eval_fixture_files` (WARNING on missing fixture files),
`validate_has_evals` (INFO when no evals are defined), `validate_requires_forge`
(WARNING when a skill uses `depends_on` or evals without `requires-forge`).

**NEW-003 — `requires-forge` frontmatter field**

Skills can now declare a version constraint:

```yaml
requires-forge: ">=0.4.0"
```

Supported operators: `>=`, `>`, `==`, `<=`, `<`, `!=`. Multiple comma-separated
specifiers are AND-ed (PEP 440 style). `skills-forge install` enforces the constraint
before writing any files.

**BKL-007 — Multi-registry configuration**

A persistent config lives at `~/.skills-forge/config.toml`, created automatically on
`skills-forge init`:

```toml
[defaults]
registry = "public"
target   = "claude"

[registries.public]
url = "https://raw.githubusercontent.com/ficiverson/skill-registry/main"

[registries.internal]
url   = "https://registry.example.com"
token = "${INTERNAL_REGISTRY_TOKEN}"
```

New subcommands: `skills-forge registry list`, `registry add`, `registry remove`,
`registry set-default`.

**BKL-010 — Per-registry auth tokens with env-var expansion**

Each registry entry accepts an optional `token` field with `${VAR}` / `$VAR` expansion
at call time. Token priority: config file → `GITHUB_TOKEN` env var → unauthenticated.

**BKL-013 — SHA256 warning on remote installs**

Installing from a URL without `--sha256` prints a warning to stderr. Providing a wrong
digest exits non-zero before any files are written.

### Bug fixes

- `LintReport.is_clean` no longer returns `False` for INFO-level issues — only ERROR
  and WARNING block clean status.
- `_parse_frontmatter` regex now matches hyphenated keys (e.g. `requires-forge`) and
  strips surrounding YAML quotes from values.

### Upgrade notes

- `skills-forge init` now creates `~/.skills-forge/config.toml` with the public registry
  pre-populated.
- No breaking changes to `.skillpack` archives or `index.json` registries.

### Test coverage

383 tests · 0 failures (up from 272 in v0.3.0)

---

## v0.3.0 — 2026-04-10

### New features

**BKL-001 — Dependency enforcement on install**

`skills-forge install` resolves `depends_on` entries in `SKILL.md` frontmatter and warns
about missing dependencies before completing. Install always proceeds; `--no-deps` skips
the check.

```
⚠ Missing dependencies (install these first):
  · some-skill  →  skills-forge install <path-to-some-skill>
```

**BKL-002 — Full uninstall with `--target` flag**

`skills-forge uninstall` accepts `--target` / `-t` to limit removal to a specific
platform directory. Reports each symlink removed. Idempotent — re-running on an
already-removed skill exits `0`.

**BKL-003 — `skills-forge list` alias**

`list` is now an alias for `list-skills`:

```bash
skills-forge list                     # new alias
skills-forge list output_skills/      # optional directory argument
```

**release-preflight skill (new)**

Published to the registry as `release-preflight@0.1.0`. Runs the five-phase pipeline
(code quality, pack consistency, schema alignment, CLI UAT, release hygiene) before any
release. Ships with `scripts/check_packs.py` and `scripts/uat_sandbox.py`.

### Improvements (from v0.2.0, shipped on this branch)

**Multi-platform install with `--target`**

`skills-forge install` supports `claude`, `gemini`, `codex`, `vscode`, `agents`, and
`all` targets.

**Export command — 5 platform formats**

```bash
skills-forge export my-skill.skillpack                  # system-prompt (default)
skills-forge export my-skill.skillpack -f gpt-json
skills-forge export my-skill.skillpack -f gem-txt
skills-forge export my-skill.skillpack -f bedrock-xml
skills-forge export my-skill.skillpack -f mcp-server
```

**`platforms` and `export_formats` in pack manifests**

Every `.skillpack` manifest now embeds supported platforms and export formats, written
automatically by `skills-forge publish`.

**`install-from-url` — remote skillpack install**

```bash
skills-forge install https://…/my-skill-1.0.0.skillpack --sha256 <digest>
```

### Bug fixes

- `UninstallSkill` now returns `list[Path]` (was `bool`) — enables per-path removal
  confirmations.
- `InstallFromUrl` correctly threads `InstallTarget` through to the installer adapter.
- `registry_index_codec`: renamed internal `_SUPPORTED` constant to `_supported` to
  satisfy ruff N806.
- All 35 source files pass mypy strict mode with zero errors.

### Test coverage

272 tests · 0 failures · 0 skipped
