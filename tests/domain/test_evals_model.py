"""Tests for EvalAssertion, EvalCase, and Skill.evals domain model additions."""

from __future__ import annotations

import pytest

from skill_forge.domain.model import (
    VALID_ASSERTION_TYPES,
    Description,
    EvalAssertion,
    EvalCase,
    Skill,
    SkillContent,
    SkillIdentity,
)

# ── EvalAssertion ─────────────────────────────────────────────────────────────


class TestEvalAssertion:
    def test_valid_contains(self) -> None:
        a = EvalAssertion(id="a1", text="Has greeting", type="contains", expected="hello")
        assert a.id == "a1"
        assert a.type == "contains"
        assert a.expected == "hello"

    def test_valid_not_contains(self) -> None:
        a = EvalAssertion(id="a1", text="No error", type="not-contains", expected="ERROR")
        assert a.type == "not-contains"

    def test_valid_regex(self) -> None:
        a = EvalAssertion(id="a1", text="Has number", type="regex", expected=r"\d+")
        assert a.type == "regex"

    def test_valid_llm_judge(self) -> None:
        a = EvalAssertion(id="a1", text="Complete sentence", type="llm-judge")
        assert a.type == "llm-judge"
        assert a.expected == ""

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id cannot be empty"):
            EvalAssertion(id="", text="some text", type="contains")

    def test_whitespace_id_raises(self) -> None:
        with pytest.raises(ValueError, match="id cannot be empty"):
            EvalAssertion(id="   ", text="some text", type="contains")

    def test_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="text cannot be empty"):
            EvalAssertion(id="a1", text="", type="contains")

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError, match="type must be one of"):
            EvalAssertion(id="a1", text="some text", type="fuzzy-match")

    def test_valid_assertion_types_constant(self) -> None:
        assert {"contains", "not-contains", "regex", "llm-judge"} == VALID_ASSERTION_TYPES

    def test_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        a = EvalAssertion(id="a1", text="text", type="contains", expected="x")
        with pytest.raises(FrozenInstanceError):
            a.id = "changed"  # type: ignore[misc]


# ── EvalCase ──────────────────────────────────────────────────────────────────


class TestEvalCase:
    def test_minimal_case(self) -> None:
        case = EvalCase(id=1, prompt="What is 2+2?", expected_output="4")
        assert case.id == 1
        assert case.assertions == ()
        assert case.files == ()

    def test_with_assertions(self) -> None:
        a = EvalAssertion(id="a1", text="Contains 4", type="contains", expected="4")
        case = EvalCase(
            id=1,
            prompt="What is 2+2?",
            expected_output="4",
            assertions=(a,),
        )
        assert len(case.assertions) == 1
        assert case.assertions[0].expected == "4"

    def test_with_files(self) -> None:
        case = EvalCase(
            id=2, prompt="Analyse file", expected_output="...",
            files=("fixtures/sample.py",),
        )
        assert case.files == ("fixtures/sample.py",)

    def test_empty_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="prompt cannot be empty"):
            EvalCase(id=1, prompt="", expected_output="something")

    def test_whitespace_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="prompt cannot be empty"):
            EvalCase(id=1, prompt="   ", expected_output="something")

    def test_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        case = EvalCase(id=1, prompt="p", expected_output="o")
        with pytest.raises(FrozenInstanceError):
            case.id = 99  # type: ignore[misc]


# ── Skill.evals ───────────────────────────────────────────────────────────────


def _make_skill(**kwargs) -> Skill:
    return Skill(
        identity=SkillIdentity(name="test-skill", category="test"),
        description=Description(text="Test skill description for testing purposes."),
        content=SkillContent(principles=["Do the right thing"]),
        **kwargs,
    )


class TestSkillEvals:
    def test_default_empty(self) -> None:
        skill = _make_skill()
        assert skill.evals == []
        assert skill.has_evals is False

    def test_with_evals(self) -> None:
        case = EvalCase(id=1, prompt="p", expected_output="o")
        skill = _make_skill(evals=[case])
        assert len(skill.evals) == 1
        assert skill.has_evals is True

    def test_total_estimated_tokens_unchanged(self) -> None:
        """Evals don't affect the token estimate (they're not exported)."""
        skill_no_evals = _make_skill()
        case = EvalCase(id=1, prompt="p " * 100, expected_output="o " * 100)
        skill_with_evals = _make_skill(evals=[case])
        assert skill_no_evals.total_estimated_tokens == skill_with_evals.total_estimated_tokens
