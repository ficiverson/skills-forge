# skills-forge — Roadmap to v1.0.0

> Current stable: **v0.2.0**  
> Target GA: **v1.0.0**  
> Approach: six milestone releases (v0.3 → v0.8) converging on a production-grade, fully documented, 95%-covered toolkit.

---

## Backlog Sources

This roadmap was compiled from:
- Known issues and technical debt discovered during v0.2.0 assessment sessions
- Features mentioned in the blog post as "upcoming" (OpenAPI exporter, Actions)
- Gaps identified in the universal export research document (`docs/universal-export-research.md`)
- Domain model fields that are parsed but not yet enforced (`depends_on`)
- CLI commands that exist as stubs but lack full use-case implementations (`uninstall`)
- Architecture patterns the clean-architecture design enables but hasn't yet surfaced

---

## Milestones Overview

| Version | Theme | Target |
|---------|-------|--------|
| v0.3.0 | **Dependency & lifecycle completeness** | Core install/uninstall/depends_on loop closes |
| v0.4.0 | **Registry discovery** | Search, multi-registry config, list improvements |
| v0.5.0 | **Registry governance** | Private auth, yank, deprecation, signing |
| v0.6.0 | **Platform expansion** | OpenAPI exporter, Actions, 3 new export formats |
| v0.7.0 | **Operational tooling** | Update command, registry management CLI, hooks |
| v0.8.0 | **Production hardening** | 95% coverage, integration suite, docs site, error quality |
| **v1.0.0** | **GA** | Changelog, migration guide, stable API contract |

---

## v0.3.0 — Dependency & Lifecycle Completeness

### BKL-001 · Enforce `depends_on` during install
**Priority:** High · **Effort:** M

The `depends_on` field is parsed from `SKILL.md` frontmatter and stored in the domain model, but is never consulted during `install`. If Skill A declares `depends_on: python-tdd`, installing A should either auto-install `python-tdd` or warn the user it is missing.

Acceptance criteria:
- `install` resolves direct dependencies from the same registry the pack was installed from
- `--no-deps` flag skips resolution for offline/CI scenarios
- Circular dependency detection raises a clean error before any installation occurs
- `lint` warns when a declared dependency is not found in any configured registry

### BKL-002 · Complete `uninstall` use case
**Priority:** High · **Effort:** S

The `uninstall` command is registered in the CLI but the application-layer use case (`uninstall_skill.py`) does not exist. The command currently has no implementation behind it.

Acceptance criteria:
- Removes symlink(s) created by `install` for the specified skill and target
- `--target all` removes from every path it was installed to
- Warns if the skill is listed as a dependency of another installed skill
- Idempotent: running twice on the same skill is not an error

### BKL-003 · `list` alias for `list-skills`
**Priority:** Low · **Effort:** XS

The `CLAUDE.md` documentation and the blog post both refer to `skills-forge list`. The actual command is `skills-forge list-skills`. Add `list` as an alias. No behavioral change.

### BKL-004 · Fix `full-featured-tester` version mismatch in public registry
**Priority:** High · **Effort:** XS

Pack filename and index say `1.0.0`; the manifest inside the `.skillpack` says `1.1.0` (introduced in commit `ffbb49a`). Re-pack with `--version 1.0.0` to restore consistency, or publish as a proper `1.1.0` entry.

### BKL-005 · Commit skill-registry README and index.html
**Priority:** Medium · **Effort:** XS

`regenerate-readme.py` was run during the v0.2.0 assessment and produced correct changes (skills_count 8→9, new tester row, updated owners) that were not committed to the repository.

---

## v0.4.0 — Registry Discovery

### BKL-006 · `skills-forge search` command
**Priority:** High · **Effort:** L

Users cannot discover skills without manually browsing the registry website or cloning the index. A CLI search command closes this gap.

```bash
skills-forge search "api testing"
skills-forge search --category evaluation
skills-forge search --author "Fernando Souto"
skills-forge search --tag agile
```

Acceptance criteria:
- Searches the local index cache first; fetches remote if cache is stale (>24h)
- Displays name, category, version, description excerpt, supported platforms
- `--registry <url>` targets a specific registry; defaults to all configured registries
- Results sorted by relevance (trigram match on name + description + tags)

### BKL-007 · Multi-registry config file
**Priority:** High · **Effort:** M

Today there is no way to register multiple registries. Users must pass the full URL on every command. A config file at `~/.skills-forge/config.toml` should persist named registries.

```toml
[registries]
public   = "https://raw.githubusercontent.com/ficiverson/skill-registry/main"
internal = "https://raw.githubusercontent.com/yourorg/skills/main"
team-sre = "https://raw.githubusercontent.com/yourorg/sre-skills/main"

[defaults]
registry = "internal"
target   = "agents"
```

Commands:
```bash
skills-forge registry add internal https://raw.githubusercontent.com/yourorg/skills/main
skills-forge registry list
skills-forge registry remove internal
skills-forge registry set-default internal
```

### BKL-008 · Improve `list-skills` output
**Priority:** Low · **Effort:** S

Current output shows only name and token estimate. Extend to include version, category, installed targets (detected via symlink scan), and last-modified date.

```
  ✔ development/python-tdd @ 1.2.0  (~180 tokens)  [claude, gemini]  2026-04-07
  ✔ evaluation/ai-eng-evaluator @ 2.0.0  (~640 tokens)  [all]  2026-04-09
```

### BKL-009 · Registry index caching
**Priority:** Medium · **Effort:** M

Every `search` and `install-from-url` currently performs a live HTTP fetch. Add a local cache at `~/.skills-forge/cache/<registry-name>/index.json` with a configurable TTL (default 24h) and a `--refresh` flag to force a fetch.

---

## v0.5.0 — Registry Governance

### BKL-010 · Private registry authentication
**Priority:** High · **Effort:** L

Private GitHub repositories require a Personal Access Token. The `http_pack_fetcher.py` and registry publisher have no auth layer today.

```toml
[registries.internal]
url   = "https://raw.githubusercontent.com/yourorg/skills/main"
token = "${SKILLS_FORGE_INTERNAL_TOKEN}"   # env var expansion supported
```

Acceptance criteria:
- Token passed via config, environment variable, or `--token` flag
- Token stored securely in OS keychain via `keyring` (optional dependency)
- Auth failure produces a clear error distinguishing 401 from 404 from network error

### BKL-011 · Skill yank
**Priority:** Medium · **Effort:** M

A published version that contains a critical bug should be removable from discovery without destroying the binary (to preserve reproducible installs for existing users).

```bash
skills-forge yank my-skill@1.0.0 --registry internal --reason "Security: prompt injection vector"
```

Acceptance criteria:
- Yanked versions are hidden from `search` results but the `.skillpack` file is retained
- `install my-skill` skips yanked versions when resolving latest
- `install my-skill@1.0.0` installs a yanked version with a visible warning
- Registry index carries a `yanked: true` and `yank_reason` field per version entry

### BKL-012 · Skill deprecation
**Priority:** Low · **Effort:** S

Soft deprecation for skills that are superseded but not harmful. Different from yank: deprecated skills still appear in search with a deprecation notice and a `replaced_by` pointer.

```bash
skills-forge deprecate my-skill@1.0.0 --replaced-by my-skill@2.0.0
```

### BKL-013 · Verify SHA256 on install-from-url
**Priority:** High · **Effort:** S

The `--sha256` flag on `install <https-url>` exists in the CLI but the verification logic in `http_pack_fetcher.py` needs an end-to-end test and a user-visible warning when the flag is omitted for a remote install.

---

## v0.6.0 — Platform Expansion

### BKL-014 · OpenAPI / Actions exporter
**Priority:** High · **Effort:** XL

The most-requested missing feature, referenced in the blog post as "upcoming." Skills contain `scripts/` — Python files with typed function signatures. The Actions exporter should:

1. Inspect `scripts/*.py` and infer an OpenAPI 3.1 schema from type annotations
2. Produce a self-hosted FastAPI server wrapping those scripts
3. Emit the OpenAI Custom GPT `gpt-json` config with an `actions` block pointing to the server

```bash
skills-forge export ./evaluation-1.0.0.skillpack --format openapi -o ./exports/
# Produces: evaluation-openapi.yaml + evaluation-actions-server.py
```

This gives a Custom GPT or Bedrock Agent "hands" — it can physically call the skill's Python scripts without manual integration boilerplate.

### BKL-015 · Mistral Agents export format
**Priority:** Medium · **Effort:** M

Mistral Agents use a `system` prompt + `tools` JSON array. The research document (`docs/universal-export-research.md`) has the full spec. Adds `--format mistral-json` to the export command.

### BKL-016 · Vertex AI / Gemini API export format
**Priority:** Medium · **Effort:** S

Gemini API (Vertex AI) uses a `system_instruction` field. Straightforward adapter, adds `--format gemini-api`.

### BKL-017 · OpenAI Assistants API export format
**Priority:** Low · **Effort:** S

The Assistants API uses an `instructions` parameter + optional vector store file upload. Adds `--format openai-assistants`. Supplement files are bundled as knowledge-base attachments.

### BKL-018 · `allowed-tools` frontmatter support
**Priority:** Medium · **Effort:** S

The agentskills.io spec defines an `allowed-tools` frontmatter field that restricts which agent tools are active when a skill is loaded. The parser ignores it today. It should be stored in the domain model and written through to the installed `SKILL.md`.

---

## v0.7.0 — Operational Tooling

### BKL-019 · `skills-forge update` command
**Priority:** High · **Effort:** L

Users have no way to update installed skills to their latest version without manually re-running `install`.

```bash
skills-forge update                    # Update all installed skills
skills-forge update python-tdd         # Update a specific skill
skills-forge update --dry-run          # Show what would be updated
skills-forge update --registry internal # Update from a specific registry
```

Acceptance criteria:
- Compares installed version against registry latest
- Respects yanked and deprecated versions
- `--pin <version>` prevents a skill from being auto-updated
- Prints a diff of changed fields (description, version, platforms) before updating

### BKL-020 · Pre/post install hooks
**Priority:** Medium · **Effort:** M

Allow skill authors to ship shell scripts that run before/after installation. Hooks live in the `scripts/` directory with reserved names:

```
scripts/pre-install.sh
scripts/post-install.sh
scripts/pre-uninstall.sh
```

Acceptance criteria:
- Hooks are opt-in: skills without hook scripts are unaffected
- Hooks run in a sandboxed subprocess with no network access by default
- User is shown hook script content and prompted for confirmation before execution
- `--no-hooks` flag skips all hooks

### BKL-021 · `skills-forge doctor` command
**Priority:** Medium · **Effort:** M

Diagnoses the local skills environment: broken symlinks, version mismatches between installed skills and registry, dependency resolution issues, missing tool installations.

```bash
skills-forge doctor
# ✔ claude target: 4 skills installed, 0 broken symlinks
# ⚠ python-tdd@1.0.0 — registry has 1.2.0 available
# ✘ ai-eng-evaluator: dependency 'pdf-tools@1.0.0' not installed
```

### BKL-022 · `skills-forge init` improvements
**Priority:** Low · **Effort:** S

The current `init` command creates a bare workspace. Extend it to:
- Detect existing tool installations (Claude Code, Gemini CLI) and configure targets automatically
- Write a starter `~/.skills-forge/config.toml` with the public registry pre-configured
- Offer to install a starter skill from the public registry

---

## v0.8.0 — Production Hardening

### BKL-023 · Reach 95% test coverage
**Priority:** High · **Effort:** L

Current coverage: 92% (147 missed statements across 1906). Identify uncovered paths — primarily error branches, edge cases in the codec, and the `http_pack_fetcher.py` network layer. Write targeted tests to close the gap.

Key modules below 95% to audit:
- `export_skill.py` (95% — close)
- `install_skill.py`
- `http_pack_fetcher.py`
- `registry_index_codec.py` error paths

### BKL-024 · End-to-end integration test suite
**Priority:** High · **Effort:** L

The current suite is unit-only. Add an integration layer that exercises the full pipeline against a real filesystem and a local mock registry (no network):

1. `create` → `lint` → `pack` → `publish` to temp registry → `search` → `install` → `export` → `uninstall`
2. Install from URL (mock HTTP server)
3. Dependency resolution with a multi-skill dependency graph
4. Yank + update interactions

### BKL-025 · Error message quality audit
**Priority:** Medium · **Effort:** M

Conduct a systematic review of all `ValueError`, `FileNotFoundError`, and `typer.Exit` calls. Every user-facing error should:
- State what went wrong in plain English (no tracebacks for user errors)
- Say what the user should do next
- Include the relevant path/version/flag in the message
- Have a consistent format across the CLI

### BKL-026 · Documentation site
**Priority:** High · **Effort:** L

The `docs/` directory has three guides (`getting-started.md`, `clean-principles-for-skills.md`, `sharing-via-github.md`, `universal-export-research.md`) but no published site. Publish to GitHub Pages using MkDocs Material or Docusaurus.

Required pages:
- Getting started (quickstart in <5 minutes)
- CLI reference (all commands, flags, examples)
- SKILL.md format reference
- Registry setup guide (public + private)
- Export formats guide (all 5 + upcoming OpenAPI)
- Migration guide (v0.x → v1.0)
- Contributing guide

### BKL-027 · `lint_service.py` audit
**Priority:** Low · **Effort:** S

A `lint_service.py` file was noted during the v0.2.0 assessment as needing either proper test coverage or removal. Determine whether it is used, tested, and correct — or delete it.

### BKL-028 · GitHub Actions CI pipeline hardening
**Priority:** Medium · **Effort:** M

The CI pipeline exists (PyPI publishing was done in the v0.1.x history). Extend it to:
- Run ruff + mypy + pytest on every PR
- Enforce 95% coverage as a required check
- Build and test on Python 3.10, 3.11, and 3.12
- Run the integration test suite against a mock registry
- Auto-publish to PyPI on tagged releases via OIDC (revert the API token workaround from v0.1.x)

---

## v1.0.0 — General Availability

### BKL-029 · Stable public API contract
**Priority:** High · **Effort:** M

Define and document the public Python API surface (use cases, domain model, ports). Mark internal implementation details with `_` prefixes. Commit to semantic versioning from this point forward: no breaking changes without a major version bump.

### BKL-030 · CHANGELOG.md
**Priority:** Medium · **Effort:** S

Compile a full changelog covering all versions from v0.1.0 through v1.0.0, following the [Keep a Changelog](https://keepachangelog.com) format. Link from README and docs site.

### BKL-031 · v0.x → v1.0 migration guide
**Priority:** Medium · **Effort:** S

Document every breaking change introduced across v0.2 through v0.9 with before/after examples and automated migration hints where possible. Key breaking changes to document:
- `export` now requires `.skillpack` input (introduced v0.2.0)
- Multi-registry config replaces bare URL flags (v0.4.0)
- Hook execution model (v0.7.0)

### BKL-032 · PyPI release and announcement
**Priority:** High · **Effort:** S

Tag `v1.0.0`, publish to PyPI via OIDC, post release notes to GitHub Releases, and publish the LinkedIn + blog post campaign.

---

## Backlog Summary

| ID | Title | Milestone | Priority | Effort |
|----|-------|-----------|----------|--------|
| BKL-001 | Enforce `depends_on` during install | v0.3.0 | High | M |
| BKL-002 | Complete `uninstall` use case | v0.3.0 | High | S |
| BKL-003 | `list` alias for `list-skills` | v0.3.0 | Low | XS |
| BKL-004 | Fix full-featured-tester version mismatch | v0.3.0 | High | XS |
| BKL-005 | Commit skill-registry README and index.html | v0.3.0 | Medium | XS |
| BKL-006 | `skills-forge search` command | v0.4.0 | High | L |
| BKL-007 | Multi-registry config file | v0.4.0 | High | M |
| BKL-008 | Improve `list-skills` output | v0.4.0 | Low | S |
| BKL-009 | Registry index caching | v0.4.0 | Medium | M |
| BKL-010 | Private registry authentication | v0.5.0 | High | L |
| BKL-011 | Skill yank | v0.5.0 | Medium | M |
| BKL-012 | Skill deprecation | v0.5.0 | Low | S |
| BKL-013 | Verify SHA256 on install-from-url | v0.5.0 | High | S |
| BKL-014 | OpenAPI / Actions exporter | v0.6.0 | High | XL |
| BKL-015 | Mistral Agents export format | v0.6.0 | Medium | M |
| BKL-016 | Vertex AI / Gemini API export format | v0.6.0 | Medium | S |
| BKL-017 | OpenAI Assistants API export format | v0.6.0 | Low | S |
| BKL-018 | `allowed-tools` frontmatter support | v0.6.0 | Medium | S |
| BKL-019 | `skills-forge update` command | v0.7.0 | High | L |
| BKL-020 | Pre/post install hooks | v0.7.0 | Medium | M |
| BKL-021 | `skills-forge doctor` command | v0.7.0 | Medium | M |
| BKL-022 | `skills-forge init` improvements | v0.7.0 | Low | S |
| BKL-023 | Reach 95% test coverage | v0.8.0 | High | L |
| BKL-024 | End-to-end integration test suite | v0.8.0 | High | L |
| BKL-025 | Error message quality audit | v0.8.0 | Medium | M |
| BKL-026 | Documentation site | v0.8.0 | High | L |
| BKL-027 | `lint_service.py` audit | v0.8.0 | Low | S |
| BKL-028 | GitHub Actions CI pipeline hardening | v0.8.0 | Medium | M |
| BKL-029 | Stable public API contract | v1.0.0 | High | M |
| BKL-030 | CHANGELOG.md | v1.0.0 | Medium | S |
| BKL-031 | v0.x → v1.0 migration guide | v1.0.0 | Medium | S |
| BKL-032 | PyPI release and announcement | v1.0.0 | High | S |

**Effort key:** XS = hours · S = 1–2 days · M = 3–5 days · L = 1–2 weeks · XL = 2–4 weeks
