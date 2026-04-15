# Changelog

All notable changes to skills-forge are documented here.

---

## [0.8.0] — 2026-04-11

### Added
- **95%+ test coverage** (640 tests, up from ~257 in v0.7.0)
- **End-to-end integration test suite** — 5 full workflow scenarios covering create→lint→pack→install→export, SHA256 verification, dependency graphs, update/diff, and yank
- **MkDocs documentation site** — complete docs covering all commands, skill anatomy, export formats, registry publishing, install targets, and clean architecture design
- **GitHub Actions CI** — automated pipeline with Python 3.10/3.11/3.12 matrix, 95% coverage gate, ruff linting, and mypy type checking
- **Improved error messages** — all key error paths now include actionable guidance ("run 'skills-forge pack' first", "use '--scope project'", "valid targets: ...")

### Changed
- `diff` error: "registry_url is required" now includes how to pass or configure it
- `update` error: "not installed" message now suggests the `install` command
- `publish` error: "pack does not exist" now suggests running `pack` first
- `GitRegistryPublisher` errors: paths now quoted, multi-skill error explains workaround
- `SymlinkInstaller` errors: invalid target messages now list valid options
- `ZipSkillPacker` errors: pack corruption messages now suggest re-packing

### Infrastructure
- New test files: `tests/infrastructure/test_subprocess_claude_runner.py`, `tests/infrastructure/test_coverage_gaps.py`, `tests/application/test_lint_service.py`, `tests/cli/test_cli_extended.py`, `tests/e2e/test_e2e_scenarios.py`
- Coverage climbed from 83% → 95.42% through systematic gap-filling

---

## [0.7.0] — 2026-04-09

### Added
- `skills-forge test` command — run skill evals against Claude or OpenAI
- `skills-forge diff` command — unified diff between installed version and registry latest
- `skills-forge update` command — auto-update installed skills from a registry
- `skills-forge doctor` command — diagnose installation health (broken symlinks, missing deps, outdated versions)
- MCP server export format (`-f mcp-server`)
- Mistral JSON export format (`-f mistral-json`)
- Gemini Developer API export format (`-f gemini-api`)
- OpenAI Assistants API export format (`-f openai-assistants`)
- `depends_on` frontmatter field for skill dependency declarations
- `hints` frontmatter field for model-specific guidance
- Dependency resolution in `install` (warns about missing dependencies)
- `--no-deps` flag on `install` to skip dependency checks

---

## [0.6.0] — 2026-03-28

### Added
- `skills-forge publish` command — publish `.skillpack` to a Git-backed registry
- `skills-forge yank` command — mark a version as yanked
- `skills-forge deprecate` command — mark a version as deprecated
- `skills-forge registry` subcommands (list, add, remove, set-default)
- Registry index codec — `RegistryIndex` JSON serialisation/deserialisation
- HTTP pack fetcher with SHA256 verification and size cap
- Git registry publisher adapter

---

## [0.5.0] — 2026-03-15

### Added
- `skills-forge export` command with system-prompt, gpt-json, gem-txt, bedrock-xml formats
- `skills-forge pack` / `skills-forge unpack` commands
- `.skillpack` archive format with `manifest.json`
- `skills-forge info` command
- `--target all` to install into every supported tool directory

---

## [0.4.0] — 2026-02-20

### Added
- Multi-target install: `--target gemini`, `--target codex`, `--target vscode`, `--target agents`
- `scripts`, `examples`, `assets` frontmatter sections
- `skills-forge list` command with token estimates
- Install-from-URL support for `.skillpack` archives

---

## [0.3.0] — 2026-01-15

### Added
- `skills-forge install` with global/project scope
- Symlink-based installation model
- `skills-forge create` scaffold command
- 20+ lint validators
- Clean architecture refactor: domain / application / infrastructure / cli layers

---

## [0.1.0] — 2025-12-01

Initial release with basic `lint` functionality.
