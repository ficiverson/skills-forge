# Contributing

Thank you for your interest in contributing to skills-forge!

---

## Development setup

```bash
git clone https://github.com/ficiverson/skills-forge.git
cd skills-forge
pip install -e ".[dev]"
```

This installs the package in editable mode with all development dependencies (pytest, ruff, mypy, coverage, mkdocs-material).

---

## Running tests

```bash
# Run all tests
pytest

# Run with coverage (requires 95%)
pytest --cov=skill_forge --cov-fail-under=95

# Run a specific test file
pytest tests/domain/test_validators.py

# Run E2E scenarios
pytest tests/e2e/
```

---

## Code quality

```bash
# Lint with ruff
ruff check src/ tests/

# Type check with mypy
mypy src/

# Format
ruff format src/ tests/
```

The CI pipeline runs all of these automatically.

---

## Architecture

Before adding a feature, read [Clean Architecture Principles](design/clean-principles.md). The key rules:

1. New business logic goes in `application/use_cases/` (no I/O)
2. New I/O adapters go in `infrastructure/adapters/`
3. New ports go in `domain/ports.py`
4. `cli/factory.py` is the **only** file that wires concrete types
5. `domain/` must have zero external imports

---

## Adding a new export format

1. Create `src/skill_forge/infrastructure/adapters/exporters/<name>_exporter.py`
2. Implement `SkillExporter` with `format = ExportFormat.<NAME>`
3. Add `ExportFormat.<NAME>` to `domain/model.py`
4. Register the exporter in `cli/factory.py`
5. Add tests in `tests/infrastructure/`

---

## Adding a new validator

1. Add your function to `domain/validators.py`
2. Follow the signature: `def validate_xyz(skill: Skill, skill_dir: Path | None = None) -> list[LintIssue]`
3. Add the function to `_ALL_VALIDATORS` at the bottom of the file
4. Add tests in `tests/domain/test_validators.py`

---

## Commit messages

We use the Conventional Commits format:

```
feat: add gemini-api export format
fix: correct token count for multi-byte characters
test: add e2e scenario for dependency resolution
docs: update install targets table
```

---

## Pull request checklist

- [ ] Tests pass: `pytest --cov=skill_forge --cov-fail-under=95`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Type checking passes: `mypy src/`
- [ ] New code has tests
- [ ] Docs updated if behaviour changed
- [ ] RELEASE_NOTES.md updated for user-visible changes

---

## Reporting issues

Open an issue on [GitHub](https://github.com/ficiverson/skills-forge/issues) with:

- skills-forge version (`skills-forge --version`)
- Python version
- Operating system
- Minimal reproduction steps
- Expected vs. actual behaviour
