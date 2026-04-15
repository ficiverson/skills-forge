# Release Notes — skills-forge 0.4.0

Release date: 2026-04-10

This release delivers the complete v0.4.0 milestone: evals as a first-class skill component, compatibility constraints, a multi-registry configuration system, per-registry auth tokens, and secure remote install verification.

---

## New features

### NEW-005 — Evals as a first-class skill component

Skills can now ship their own test suite inside an `evals/` subdirectory.

**Schema** (`evals/evals.json`): a JSON array of eval case objects, each with:

- `id` — unique string identifier for the case
- `prompt` — the user input to test against
- `expected_output` — the expected model response (used for programmatic assertions)
- `assertions` — array of assertion objects (`id`, `text`, `type`, `expected`)
- `files` — optional list of fixture file paths relative to `evals/fixtures/`

Supported assertion types: `contains`, `not-contains`, `regex`, `llm-judge`.

**New command**:

```
skills-forge test <skill-path> [-t <timeout>]
```

Runs every eval case and prints a per-assertion pass/fail table. `contains`, `not-contains`, and `regex` assertions are graded programmatically; `llm-judge` assertions invoke a second Claude call.

**Scaffolding**: `skills-forge create` now generates an `evals/` directory with a starter `evals.json` and an empty `evals/fixtures/` folder.

**Linting**: new lint rules — `validate_evals_schema` (ERROR on malformed JSON or unknown assertion types), `validate_eval_fixture_files` (WARNING when referenced fixture files are missing), `validate_has_evals` (INFO when no evals are defined), `validate_requires_forge` (WARNING when a skill uses `depends_on` or evals but omits `requires-forge`).

**List view**: `skills-forge list` now shows an `[evals]` tag for skills that have at least one eval case.

**Export safety**: the `evals/` directory is intentionally excluded from all export formats — eval fixtures are developer tooling, not user-facing prompt content.

---

### NEW-003 — `requires-forge` frontmatter field

Skills can now declare a minimum (or exact) skills-forge version required to install them:

```yaml
---
name: my-skill
requires-forge: ">=0.4.0"
---
```

Supported operators: `>=`, `>`, `==`, `<=`, `<`, `!=`. Multiple comma-separated specifiers are supported (AND logic, consistent with PEP 440).

`skills-forge install` checks this constraint before writing any files and raises a clear error if the running version does not satisfy it. The constraint is also preserved in `skills-forge pack` archives and honoured on `skills-forge install <url>`.

---

### BKL-007 — Multi-registry configuration

A persistent configuration file is now supported at `~/.skills-forge/config.toml` (created automatically on `skills-forge init`).

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

New subcommands:

```
skills-forge registry list
skills-forge registry add <name> <url> [--token <tok>]
skills-forge registry remove <name>
skills-forge registry set-default <name>
```

---

### BKL-010 — Per-registry auth tokens with env-var expansion

Each registry entry can carry an optional `token` field. The value is resolved at call time using `${VAR}` / `$VAR` substitution from the process environment. Unresolved variables are left as-is and never logged.

Token resolution priority for remote fetches:

1. Token configured for the matching registry in `config.toml`
2. `GITHUB_TOKEN` environment variable (legacy fallback)
3. Unauthenticated request

Tokens support a `Bearer ` prefix — if the stored value already starts with `Bearer `, it is used verbatim; otherwise `Bearer <token>` is constructed automatically.

---

### BKL-013 — SHA256 warning on remote installs + mismatch error

When installing a `.skillpack` from a URL, a visible warning is now printed to stderr if no `--sha256` digest is supplied:

```
⚠  Installing without SHA256 verification — supply the digest with --sha256 <hex> for secure installs
```

If `--sha256` is provided and the downloaded archive does not match, the command exits non-zero with a clear error message before any files are written.

Four E2E tests cover: warning present when digest omitted, warning absent when digest provided, non-zero exit on digest mismatch, zero exit on correct digest.

---

## Bug fixes

- `LintReport.is_clean` no longer returns `False` for INFO-level issues. Only ERROR and WARNING severities mark a report as unclean.

---

## Upgrade notes

- `skills-forge init` now also creates `~/.skills-forge/config.toml` with the default public registry pre-populated.
- Existing `.skillpack` archives continue to work without modification.
- No breaking changes to the public CLI interface.

---

## Test coverage

379 tests passing (up from 257 in v0.3.0), 0 failures.
