---
name: release-preflight
version: 0.1.0
description: >
  Five-phase pre-release verification for skills-forge projects: pytest, ruff, mypy,
  pack consistency (sha256/size/manifest vs index.json), schema alignment
  (FORMAT_VERSION constants), CLI sandbox UAT (every command), and release hygiene
  (branch, version, notes, changelog, clean git status).
  Trigger on: "ready to release", "run all checks", "pre-release checklist",
  "verify before tagging", "UAT", "preflight", "PyPI publish check",
  "pack consistency", "schema aligned", "registry up-to-date", "run lint and tests".
  Always run all phases unless the user explicitly requests a single one.
emoji: 🚀
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

```bash
# All three commands must exit 0; run in the project root
export PATH="$PATH:$HOME/.local/bin"   # skills-forge install location

pytest --tb=short -q                   # full test suite
ruff check src/ tests/                 # E/F/W/I/N/UP/B/SIM/RUF rules
mypy src/                              # strict mode, zero issues
```

**What to report:**
- Number of tests collected and the pass/fail count
- Any ruff rule violations with file + line
- Any mypy errors with file + line

Stop the preflight and report failure if any of these exit non-zero — the remaining
phases still require clean code to be meaningful.

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

All 5 export formats: `system-prompt`, `gpt-json`, `gem-txt`, `bedrock-xml`, `mcp-server`
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
| `skills-forge init` | Workspace initialisation |
| `skills-forge create` | Skill scaffolding |
| `skills-forge lint` | SKILL.md validation |
| `skills-forge install` (project, claude) | Symlink into `.claude/skills/` |
| `skills-forge install` (project, agents) | Symlink into `.agents/skills/` |
| `skills-forge list` | List installed skills |
| `skills-forge pack` | Bundle into `.skillpack` |
| `skills-forge unpack` | Extract `.skillpack` |
| `skills-forge export` (system-prompt) | Plain-text export |
| `skills-forge export` (gpt-json) | OpenAI JSON export |
| `skills-forge uninstall` | Remove symlinks |
| `skills-forge uninstall` (idempotent) | Re-run on already-removed exits 0 |

For each command, capture stdout/stderr and exit code. Print `✅ <command>` or
`❌ <command>: exit <N> — <stderr snippet>`. Clean up the temp directory at the end.

---

## Phase 5 — Release Hygiene

Work through this checklist (automate what you can with git):

- [ ] **Correct branch** — are we on the intended release branch (e.g. `1.0.0`, `release/x.y.z`)?
- [ ] **Version bump** — does `pyproject.toml` `[project].version` match the intended release?
- [ ] **RELEASE_NOTES** — does `RELEASE_NOTES_<version>.md` exist and cover all changes since last tag?
- [ ] **ROADMAP** — is `ROADMAP_1.0.0.md` updated with completed items reflected?
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
  Phase 1 · Code Quality        ✅  272 tests, ruff OK, mypy OK
  Phase 2 · Pack Consistency    ✅  10/10 packs
  Phase 3 · Schema Alignment    ✅  format_version "3"/"1" aligned
  Phase 4 · CLI Sandbox UAT     ✅  12/12 commands
  Phase 5 · Release Hygiene     ⚠️  RELEASE_NOTES missing for v0.3.1
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
