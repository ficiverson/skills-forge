# skills-forge

**A clean-architecture toolkit for crafting, linting, packing, and sharing Claude Code skills.**

skills-forge gives you a complete workflow for building high-quality, reusable Claude Code skill files — from scaffolding and validation through packaging, publishing, and cross-tool export.

---

## Quick start

```bash
pip install skills-forge
skills-forge create -n python-tdd -c development -d "Use when writing Python with TDD. Triggers on: pytest, test-first, red-green-refactor." -e 🔴
skills-forge lint output_skills/development/python-tdd
skills-forge install output_skills/development/python-tdd
```

That's it — your skill is live in `~/.claude/skills/`.

---

## Key features

- **Scaffolding** — `create` generates a well-structured SKILL.md with frontmatter, instructions, and optional references
- **Lint** — 20+ validators catch name mismatches, description problems, oversized instructions, and more
- **Pack / Unpack** — bundle one or more skills into a portable `.skillpack` archive
- **Install** — symlink into Claude Code, Gemini CLI, Codex, VS Code Copilot, or all at once
- **Export** — emit prompts optimised for OpenAI Custom GPTs, Google Gemini Gems, AWS Bedrock Agents, or a self-contained MCP server
- **Registry** — publish, discover, update, and yank skills via a Git-backed registry
- **Doctor** — diagnose broken symlinks, outdated skills, and missing dependencies

---

## Why skills-forge?

Claude Code skills are just Markdown files — but writing *good* ones takes discipline. skills-forge enforces the patterns that make skills effective: concise descriptions with trigger phrases, focused bodies under ~1 000 tokens, progressive disclosure via references, and clean frontmatter metadata.

The clean-architecture design means every use case is independently testable and every adapter is swappable. Use the CLI today and embed the Python API tomorrow.

---

## Architecture at a glance

```
cli/                  # Typer commands + composition root (factory.py)
  └─ main.py
application/          # Use cases (zero I/O)
  └─ use_cases/
infrastructure/       # Adapters (filesystem, git, HTTP, exporters)
  └─ adapters/
domain/               # Models, validators, ports (zero dependencies)
  └─ model.py, validators.py, ports.py
```

Dependencies flow strictly inward: **cli → application → domain ← infrastructure**.

---

## Status

skills-forge is in active development. The v0.8.0 release focuses on production readiness:

- ✅ 95%+ test coverage (640 tests)
- ✅ End-to-end integration test suite
- ✅ Error messages with actionable guidance
- ✅ GitHub Actions CI with multi-Python matrix
- ✅ MkDocs documentation site (this site)

See the [changelog](changelog.md) for the full history.
