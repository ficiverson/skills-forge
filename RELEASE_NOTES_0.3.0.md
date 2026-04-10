# Release Notes — skills-forge v0.3.0

**Release date:** 2026-04-10  
**Branch:** `1.0.0`  
**Requires:** Python ≥ 3.10, typer ≥ 0.12

---

## What's new

### Dependency enforcement on install (BKL-001)

`skills-forge install` now resolves the `depends_on` field in `SKILL.md` frontmatter
and warns about any missing dependencies before completing the install. The install
still proceeds — warnings never block — but each missing dependency is listed with the
exact command needed to resolve it:

```
⚠ Missing dependencies (install these first):
  · some-skill  →  skills-forge install <path-to-some-skill>
```

A `--no-deps` flag is available to skip the check entirely (useful in CI or offline
scenarios).

### Full uninstall with `--target` flag (BKL-002)

`skills-forge uninstall` now:

- Accepts `--target` / `-t` to limit removal to a specific platform directory
  (`claude`, `gemini`, `codex`, `vscode`, `agents`, or `all`).
- Reports each symlink path it removed: `✔ Removed ~/.claude/skills/my-skill`
- Is **idempotent** — re-running on an already-removed skill exits `0` with a
  warning instead of failing. This makes it safe to call from scripts and CI.

### `skills-forge list` alias (BKL-003)

The existing `list-skills` command is now also available as plain `list`,
matching the short-form used throughout the documentation:

```bash
skills-forge list                     # new alias
skills-forge list-skills              # still works
skills-forge list output_skills/      # accepts an optional directory argument
```

### `release-preflight` skill (new)

A new bundled skill lives at `output_skills/distribution/release-preflight/` and is
published to the registry as `release-preflight@0.1.0`. It runs the five-phase
verification pipeline before any release:

| Phase | What it checks |
|-------|---------------|
| 1 · Code Quality | pytest, ruff, mypy |
| 2 · Pack Consistency | sha256, size, manifest vs index.json for every pack |
| 3 · Schema Alignment | FORMAT_VERSION constants vs wire formats |
| 4 · CLI Sandbox UAT | All 12 CLI commands in an isolated temp directory |
| 5 · Release Hygiene | Branch, version, release notes, changelog, git status |

Ships with two reusable scripts: `scripts/check_packs.py` and `scripts/uat_sandbox.py`.

---

## Improvements in v0.2.0 (shipped on this branch)

### Multi-platform install with `--target`

`skills-forge install` gained a `--target` / `-t` flag supporting all five
agent skill platforms:

| Target | Path |
|--------|------|
| `claude` (default) | `~/.claude/skills/` |
| `gemini` | `~/.gemini/skills/` |
| `codex` | `~/.codex/skills/` |
| `vscode` | `.github/skills/` (project only) |
| `agents` | `~/.agents/skills/` |
| `all` | Every applicable path at once |

### Export command — 5 platform formats

`skills-forge export <pack>` converts a `.skillpack` into a platform-specific
prompt format:

```bash
skills-forge export my-skill.skillpack                  # system-prompt (default)
skills-forge export my-skill.skillpack -f gpt-json      # OpenAI Custom GPT JSON
skills-forge export my-skill.skillpack -f gem-txt       # Google Gemini Gem
skills-forge export my-skill.skillpack -f bedrock-xml   # AWS Bedrock agent XML
skills-forge export my-skill.skillpack -f mcp-server    # Self-contained Python MCP server
```

### `platforms` and `export_formats` in pack manifests

Every `.skillpack` manifest now embeds the supported platforms and export formats.
The `skills-forge publish` command writes these fields into both the manifest and
`index.json` automatically. All 11 packs in the registry were rebuilt to include
this metadata.

### `install-from-url` — remote skillpack install

```bash
skills-forge install https://raw.githubusercontent.com/…/my-skill-1.0.0.skillpack \
  --sha256 <digest>
```

Fetches a remote `.skillpack`, verifies its sha256 digest, and installs it in one
step.

---

## Bug fixes

- `UninstallSkill` now returns `list[Path]` (was `bool`) — enables the CLI to print
  per-path removal confirmations.
- `InstallFromUrl` correctly threads `InstallTarget` through to the installer adapter.
- `registry_index_codec`: renamed internal `_SUPPORTED` constant to `_supported` to
  satisfy ruff N806.
- All 35 source files pass mypy strict mode with zero errors.

---

## Test coverage

272 tests · 0 failures · 0 skipped

Key new test files:

- `tests/application/test_install_skill.py` — 11 tests covering dependency
  enforcement, `--no-deps` flag, multiple missing deps, idempotent uninstall,
  and uninstall with explicit target.

---

## Upgrade notes

No breaking changes. All existing `SKILL.md` files, `.skillpack` archives, and
`index.json` registries from v0.2.0 remain fully compatible.

If you have skills with `depends_on` entries, they will now produce install-time
warnings when dependencies are absent. Pass `--no-deps` to suppress.
