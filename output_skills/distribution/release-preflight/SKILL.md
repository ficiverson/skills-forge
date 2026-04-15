---
name: release-preflight
version: 1.1.0
description: >
  Five-phase pre-release check for skills-forge: (1) pytest + ruff + mypy via
  check_pipeline.py, (2) pack consistency sha256/size/manifest, (3) schema alignment
  FORMAT_VERSION, (4) CLI sandbox UAT all commands + E2E scenarios, (5) release hygiene
  branch/version/notes/registry. Triggers on: "ready to release", "run preflight",
  "pre-release checklist", "verify before tagging", "UAT", "pack consistency",
  "run lint and tests", "pipeline check", "PyPI publish".
emoji: 🚀
requires-forge: ">=0.8.0"
---

# Release Preflight

STARTER_CHARACTER = 🚀

## Principles

- **Run every phase even if one fails** — surface all issues in a single pass so the
  developer can fix multiple problems without re-running the pipeline repeatedly.
- **Be specific about failures** — name the exact file, pack, command, or line number so
  the developer can act immediately without re-reading raw output.
- **Automate what you can, prompt for the rest** — Phase 1–4 are fully scriptable; Phase 5
  requires judgment. Use the provided scripts and commands; only ask the developer for
  information the scripts cannot infer.
- **Gate on Phase 1** — if tests/lint/types fail, report Phase 1 failure in the summary
  and mark the overall result ❌. Still run and report Phases 2–5 so the developer sees
  the full picture.
- **A yellow board (⚠️) is still shippable** — warn about hygiene issues (missing notes,
  stale README) but do not block the release on them unless the developer asks you to.

This skill runs the five-phase verification pipeline used before every skills-forge
release. The goal is to reach a **green board** — every gate passes — before tagging
or publishing.

## The Five Phases

| Phase | What it checks | Gate |
|-------|---------------|------|
| 1 · Code Quality | pytest, ruff, mypy | Zero failures / errors / warnings |
| 2 · Pack Consistency | sha256, size, manifest.version vs index.json | Every pack ✅ |
| 3 · Schema Alignment | FORMAT_VERSION constants vs actual wire formats | No drift |
| 4 · CLI Sandbox UAT | Every CLI command exercised end-to-end | All commands run without error |
| 5 · Release Hygiene | Branch, notes, roadmap, changelog | All items checked |

Run all five phases in order and report a summary at the end.

---

## Phase 1 — Code Quality

Run the two checks in order. Both must exit 0 before the release can proceed.

### 1a — Test suite + coverage gate

```bash
# Run from the project root
export PATH="$PATH:$HOME/.local/bin"

pytest --cov=skill_forge --cov-fail-under=95 --tb=short -q
```

**What to report:**
- Number of tests collected and the pass/fail count (target: 665+)
- Coverage percentage (must be ≥ 95%)
- Any failing tests with file + line

### 1b — CI pipeline check (lint & type check)

Run the dedicated script that mirrors the GitHub Actions **Lint & Type Check** job
exactly — same three commands, same order:

```bash
python output_skills/distribution/release-preflight/scripts/check_pipeline.py
```

The script runs:

| CI step | Command |
|---------|---------|
| Ruff lint | `ruff check src/ tests/` |
| Ruff format check | `ruff format --check src/ tests/` |
| Mypy type check | `mypy src/` |

It exits 0 when all three pass and prints a structured summary. On failure it
prints the full tool output so you can fix the issue without re-running manually.

**What to report:**
- `✅ CLEAR` if all three commands passed
- `❌ BLOCKED` with the specific failing command(s) and the tool output if any failed

Stop the preflight and report Phase 1 failure if either 1a or 1b exits non-zero —
the remaining phases still require clean code to be meaningful.

---

## Phase 2 — Pack Consistency

Run the consistency check script:

```bash
python output_skills/distribution/release-preflight/scripts/check_packs.py \
  <path-to-skill-registry>
```

The script checks every pack listed in `index.json` against the `.skillpack` file on disk:

| Check | What it verifies |
|-------|-----------------|
| File exists | Pack file is actually present in `packs/` |
| sha256 | Digest in index matches digest of file on disk |
| size_bytes | Size in index matches actual file size |
| manifest.version | Version inside the ZIP manifest matches index entry |
| export_formats | Both index and manifest list all 5 formats |
| platforms | Skill-level platforms in index list all 5 targets |

Core export formats (all new packs should include): `system-prompt`, `gpt-json`, `gem-txt`, `bedrock-xml`, `mcp-server`
Extended export formats (v0.6.0+): `mistral-json`, `gemini-api`, `openai-assistants`
All 5 platforms: `claude`, `gemini`, `codex`, `vscode`, `agents`

Print `✅ <name>@<version>` for each passing pack and `❌ <name>@<version>: <reason>` for
any failure. Print a summary line: `All N packs passed` or `X/N packs FAILED`.

If any packs fail, the fix is to rebuild them:
```bash
skills-forge pack output_skills/<category>/<skill-name>/ \
  -o <registry>/packs/<category>/<skill-name>-<version>.skillpack
skills-forge publish <pack> -r <registry-clone> -u <base-url>
```

---

## Phase 3 — Schema Alignment

Check that the in-code constants match what's actually in the files on disk. The things
that can drift are:

**`RegistryIndex.FORMAT_VERSION`** (currently `"3"`) — the codec should accept `"1"`, `"2"`, `"3"`.
Check:
```bash
grep -n "FORMAT_VERSION\|_SUPPORTED" \
  src/skill_forge/infrastructure/adapters/registry_index_codec.py
```

**`SkillPackManifest.FORMAT_VERSION`** (currently `"1"`) — manifests inside every `.skillpack`
must have `"format_version": "1"`.
Check a sample pack:
```bash
python - << 'EOF'
import zipfile, json, sys
pack = sys.argv[1]
with zipfile.ZipFile(pack) as z:
    m = json.loads(z.read("manifest.json"))
    print("format_version:", m.get("format_version"))
    print("platforms:", m.get("platforms"))
    print("export_formats:", m.get("export_formats"))
EOF path/to/any.skillpack
```

**Domain model vs wire format** — do a round-trip load to surface codec drift:
```bash
python - << 'EOF'
import sys
sys.path.insert(0, "src")
from skill_forge.infrastructure.adapters.registry_index_codec import RegistryIndexCodec
from pathlib import Path
codec = RegistryIndexCodec()
index = codec.load(Path(sys.argv[1] + "/index.json"))
assert index.format_version == "3", f"unexpected: {index.format_version}"
print(f"✅ index round-trip OK — {len(index.skills)} skills loaded")
EOF path/to/skill-registry
```

Report any mismatches. Schema alignment issues are rare but severe — they silently corrupt
published data and break downstream consumers.

---

## Phase 4 — CLI Sandbox UAT

Run the UAT script to exercise every CLI command in an isolated temp directory:

```bash
python output_skills/distribution/release-preflight/scripts/uat_sandbox.py
```

The script creates a fresh temp workspace, then runs each command in sequence and records
pass/fail:

| Command | What it exercises |
|---------|------------------|
| `skills-forge init` | Workspace initialisation + config.toml creation + tool detection |
| `skills-forge create` | Skill scaffolding (incl. evals/ directory) |
| `skills-forge lint` | SKILL.md validation |
| `skills-forge install` (project, claude) | Symlink into `.claude/skills/` |
| `skills-forge install` (project, agents) | Symlink into `.agents/skills/` |
| `skills-forge list` | List installed skills (incl. version, evals, deps) |
| `skills-forge list --category` | Filter by category (v0.5.0) |
| `skills-forge list --filter` | Filter by substring (v0.5.0) |
| `skills-forge info` | Per-skill detail view (v0.5.0) |
| `skills-forge doctor` | Health sweep — broken links, deps, stale versions (v0.5.0) |
| `skills-forge pack` | Bundle into `.skillpack` |
| `skills-forge unpack` | Extract `.skillpack` |
| `skills-forge export` (system-prompt) | Plain-text export |
| `skills-forge export` (gpt-json) | OpenAI Custom GPT JSON export |
| `skills-forge export` (mistral-json) | Mistral Agents API JSON export (NEW in v0.6.0) |
| `skills-forge export` (gemini-api) | Vertex AI / Gemini API JSON export (NEW in v0.6.0) |
| `skills-forge export` (openai-assistants) | OpenAI Assistants API JSON export (NEW in v0.6.0) |
| `skills-forge test` | Run skill evals |
| `skills-forge registry list` | Show configured registries |
| `skills-forge registry add` | Add a registry entry |
| `skills-forge registry remove` | Remove a registry entry |
| `skills-forge registry set-default` | Change default registry |
| `skills-forge install <url>` (no sha256) | Remote install — must print SHA256 warning |
| `skills-forge update --dry-run` | Preview available updates (v0.5.0) |
| `skills-forge diff` (no registry) | Actionable error: "Pass '--registry <url>'" (NEW in v0.8.0) |
| `skills-forge yank` | Yank a version in a registry clone (NEW in v0.7.0) |
| `skills-forge deprecate` | Mark a skill deprecated in a registry clone (NEW in v0.7.0) |
| `skills-forge uninstall` | Remove symlinks |
| `skills-forge uninstall` (idempotent) | Re-run on already-removed exits 0 |

Also verify the E2E suite passes as a block:

```bash
pytest tests/e2e/ -v --tb=short   # 19 E2E scenarios — all must pass
```

For each command, capture stdout/stderr and exit code. Print `✅ <command>` or
`❌ <command>: exit <N> — <stderr snippet>`. Clean up the temp directory at the end.

---

## Phase 5 — Release Hygiene

Work through this checklist (automate what you can with git):

- [ ] **Correct branch** — are we on the intended release branch (e.g. `1.0.0`, `release/x.y.z`)?
- [ ] **Version bump** — does `pyproject.toml` `[project].version` match the intended release?
- [ ] **RELEASE_NOTES** — does `RELEASE_NOTES.md` have an entry for the new version covering all changes since the last tag?
- [ ] **Changelog / commit log** — do git log messages since the last tag tell a coherent story?
- [ ] **Registry `updated_at`** — has `index.json` `updated_at` been refreshed?
- [ ] **README + index.html regenerated** — run `python regenerate-readme.py` in the registry repo.
- [ ] **Clean working tree** — `git status` shows nothing uncommitted on both repos.

Quick commands:
```bash
git branch --show-current
grep '^version' pyproject.toml
git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)..HEAD | head -20
git status --short
```

---

## Summary Report

After all five phases, produce this summary table:

```
═══════════════════════════════════════════════════
 🚀  Release Preflight  ·  skills-forge vX.Y.Z
═══════════════════════════════════════════════════
  Phase 1 · Code Quality        ✅  665 tests (97% cov) · ruff ✅ · fmt ✅ · mypy ✅
  Phase 2 · Pack Consistency    ✅  10/10 packs
  Phase 3 · Schema Alignment    ✅  format_version "3"/"1" aligned
  Phase 4 · CLI Sandbox UAT     ✅  31/31 commands + 19/19 E2E scenarios
  Phase 5 · Release Hygiene     ⚠️  RELEASE_NOTES missing for v0.6.1
───────────────────────────────────────────────────
  Overall                       ⚠️  1 item needs attention
═══════════════════════════════════════════════════
```

Use ✅ when a phase passes completely, ⚠️ for non-blocking issues, and ❌ for hard failures
that block the release. Be specific — name the exact file, pack, or command that failed.

---

## Common Fixes

| Symptom | Fix |
|---------|-----|
| Pack sha256/size mismatch | Rebuild pack with `skills-forge pack`, republish to update index |
| Missing `platforms`/`export_formats` in manifest | Rebuild the pack (pre-v0.2.0 packs lack the fields) |
| ruff N806 | Rename `_CONST = …` inside function body to `_const` |
| mypy forward-reference error | Move import to module level, remove string quotes from return type |
| `pytest: command not found` | `PATH="$PATH:$HOME/.local/bin" pytest …` |
| `skills-forge: command not found` | `pip install -e ".[dev]" --break-system-packages` |
| Uninstall exits 1 for missing skill | Upgrade to v0.3.0+ — idempotent uninstall fixed in BKL-002 |
| `SkillRef category cannot be empty` | Use `category/name/` directory layout when packing |
