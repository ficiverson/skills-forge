"""Tests for eval linter rules."""

from __future__ import annotations

import json
from pathlib import Path

from skill_forge.domain.model import (
    Description,
    EvalCase,
    Severity,
    Skill,
    SkillContent,
    SkillIdentity,
)
from skill_forge.domain.validators import (
    validate_eval_fixture_files,
    validate_evals_schema,
    validate_has_evals,
)


def _skill(evals: list[EvalCase] | None = None) -> Skill:
    return Skill(
        identity=SkillIdentity(name="test-skill", category="test"),
        description=Description(text="Test skill for validator tests."),
        content=SkillContent(principles=["Be correct"]),
        evals=evals or [],
    )


def _write_evals(skill_dir: Path, data: object) -> None:
    evals_dir = skill_dir / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    (evals_dir / "evals.json").write_text(json.dumps(data), encoding="utf-8")


# ── validate_has_evals ────────────────────────────────────────────────────────


class TestValidateHasEvals:
    def test_no_evals_produces_info(self) -> None:
        issues = validate_has_evals(_skill())
        assert len(issues) == 1
        assert issues[0].rule == "missing-evals"
        assert issues[0].severity == Severity.INFO

    def test_has_evals_clean(self) -> None:
        case = EvalCase(id=1, prompt="p", expected_output="o")
        issues = validate_has_evals(_skill(evals=[case]))
        assert issues == []


# ── validate_evals_schema ─────────────────────────────────────────────────────


class TestValidateEvalsSchema:
    def test_no_skill_dir_skipped(self) -> None:
        issues = validate_evals_schema(_skill(), skill_dir=None)
        assert issues == []

    def test_no_evals_json_skipped(self, tmp_path: Path) -> None:
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert issues == []

    def test_invalid_json_error(self, tmp_path: Path) -> None:
        evals_dir = tmp_path / "evals"
        evals_dir.mkdir()
        (evals_dir / "evals.json").write_text("{bad", encoding="utf-8")
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert any(i.rule == "evals-invalid-json" for i in issues)
        assert all(i.severity == Severity.ERROR for i in issues)

    def test_not_array_error(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, {"key": "value"})
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert any(i.rule == "evals-not-array" for i in issues)

    def test_empty_array_clean(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, [])
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert issues == []

    def test_missing_prompt_error(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, [{"id": 1, "expected_output": "o"}])
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert any(i.rule == "evals-missing-prompt" for i in issues)

    def test_non_object_case_error(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, ["not-an-object"])
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert any(i.rule == "evals-invalid-case" for i in issues)

    def test_invalid_assertion_type_error(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, [{
            "id": 1, "prompt": "p", "expected_output": "o",
            "assertions": [{"id": "a", "text": "t", "type": "fuzzy-match"}],
        }])
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert any(i.rule == "evals-unknown-assertion-type" for i in issues)

    def test_assertion_missing_id_warning(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, [{
            "id": 1, "prompt": "p", "expected_output": "o",
            "assertions": [{"text": "t", "type": "contains", "expected": "x"}],
        }])
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert any(i.rule == "evals-assertion-missing-id" for i in issues)

    def test_assertion_missing_text_warning(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, [{
            "id": 1, "prompt": "p", "expected_output": "o",
            "assertions": [{"id": "a", "type": "contains", "expected": "x"}],
        }])
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert any(i.rule == "evals-assertion-missing-text" for i in issues)

    def test_valid_schema_clean(self, tmp_path: Path) -> None:
        _write_evals(tmp_path, [{
            "id": 1,
            "prompt": "What is 2+2?",
            "expected_output": "4",
            "assertions": [
                {"id": "a1", "text": "Has answer", "type": "contains", "expected": "4"},
                {"id": "a2", "text": "Is complete", "type": "llm-judge"},
            ],
        }])
        issues = validate_evals_schema(_skill(), skill_dir=tmp_path)
        assert issues == []


# ── validate_eval_fixture_files ───────────────────────────────────────────────


class TestValidateEvalFixtureFiles:
    def _make_skill_with_fixture(self, fixture: str) -> Skill:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            files=(fixture,),
        )
        return _skill(evals=[case])

    def test_no_skill_dir_skipped(self) -> None:
        issues = validate_eval_fixture_files(
            self._make_skill_with_fixture("sample.py"), skill_dir=None
        )
        assert issues == []

    def test_no_evals_skipped(self, tmp_path: Path) -> None:
        issues = validate_eval_fixture_files(_skill(), skill_dir=tmp_path)
        assert issues == []

    def test_missing_fixture_error(self, tmp_path: Path) -> None:
        issues = validate_eval_fixture_files(
            self._make_skill_with_fixture("missing.py"), skill_dir=tmp_path
        )
        assert len(issues) == 1
        assert issues[0].rule == "evals-missing-fixture"
        assert issues[0].severity == Severity.ERROR

    def test_existing_fixture_clean(self, tmp_path: Path) -> None:
        fixtures = tmp_path / "evals" / "fixtures"
        fixtures.mkdir(parents=True)
        (fixtures / "sample.py").write_text("x = 1")
        issues = validate_eval_fixture_files(
            self._make_skill_with_fixture("sample.py"), skill_dir=tmp_path
        )
        assert issues == []
