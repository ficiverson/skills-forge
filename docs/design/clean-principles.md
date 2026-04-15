# Clean Architecture Principles

skills-forge is built on clean architecture. This page explains why and what it means for contributors and embedders.

---

## Layer diagram

```
┌─────────────────────────────────────────────────┐
│  cli/                                            │
│  (Typer commands + factory.py composition root) │
└───────────────────┬─────────────────────────────┘
                    │ depends on
┌───────────────────▼─────────────────────────────┐
│  application/                                    │
│  (use cases: create, lint, install, pack, …)    │
└───────────────────┬─────────────────────────────┘
                    │ depends on
┌───────────────────▼─────────────────────────────┐
│  domain/                                         │
│  (Skill, LintIssue, ports, validators)           │
│  Zero external dependencies                      │
└────────────────────────────▲────────────────────┘
                             │ depends on
┌────────────────────────────┴────────────────────┐
│  infrastructure/                                 │
│  (adapters: filesystem, git, HTTP, exporters)   │
└─────────────────────────────────────────────────┘
```

Dependencies point **inward only**. The domain layer has zero external dependencies.

---

## The dependency rule

> "Source code dependencies must point only inward, toward higher-level policies."
> — Robert C. Martin, *Clean Architecture*

In practice:

- `domain/` imports nothing outside the standard library
- `application/` imports only `domain/`
- `infrastructure/` imports `domain/` (to implement ports)
- `cli/` imports `application/` and `infrastructure/` — but only through `factory.py`

---

## factory.py: the composition root

`cli/factory.py` is the **only** place that knows about concrete implementations. It wires:

- Which `SkillInstaller` implementation to use (`SymlinkSkillInstaller`)
- Which `SkillParser` to use (`MarkdownSkillParser`)
- Which exporters are registered
- Which `PackFetcher` to use for URL installs

This means you can swap any adapter without touching business logic.

---

## Ports and adapters

Every infrastructure concern is hidden behind a **port** (interface) defined in `domain/ports.py`:

| Port | Description |
|------|-------------|
| `SkillRepository` | List and load skills from storage |
| `SkillInstaller` | Install, uninstall, list installed skills |
| `SkillParser` | Parse SKILL.md text → Skill domain object |
| `SkillExporter` | Export a skill to a specific format |
| `PackPublisher` | Publish, yank, deprecate in a registry |
| `PackFetcher` | Fetch a remote pack and its registry index |
| `ClaudeRunner` | Run Claude CLI subprocess |

Adapters implement these ports. Tests use mock adapters.

---

## Use cases

Each use case is a single-responsibility class with an `execute(request) → response` method:

```python
class LintSkill:
    def execute(self, request: LintSkillRequest) -> LintReport:
        skill = request.skill or self._parser.parse(
            request.path.read_text(), base_path=request.path.parent
        )
        return LintReport(
            skill_name=skill.identity.name,
            issues=tuple(run_all_validators(skill, request.path)),
        )
```

Use cases are pure. They do not touch the filesystem, network, or git directly — they call ports.

---

## Validators

All validators are **pure functions**:

```python
def validate_description_triggers(skill: Skill) -> list[LintIssue]:
    ...
```

Input: `Skill`. Output: `list[LintIssue]`. No side effects. Easy to unit test.

Path-aware validators additionally receive a `skill_dir: Path` when they need to check file presence.

---

## Testing strategy

The clean architecture enables a fast, reliable test pyramid:

| Layer | Test type | Tools |
|-------|-----------|-------|
| Domain | Unit | `pytest` with constructed domain objects |
| Application | Unit | `pytest` with `MagicMock` adapters |
| Infrastructure | Integration | `pytest` with `tmp_path` |
| CLI | Integration | `typer.testing.CliRunner` |
| Full stack | E2E | `CliRunner` with real temp directories |

The result: **826 tests in ~4 seconds**, 97% coverage.
