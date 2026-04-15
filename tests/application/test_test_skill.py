"""Tests for the TestSkill use case with a stub ClaudeRunner."""

from __future__ import annotations

from skill_forge.application.use_cases.test_skill import (
    TestSkill,
    TestSkillRequest,
)
from skill_forge.domain.model import (
    Description,
    EvalAssertion,
    EvalCase,
    Skill,
    SkillContent,
    SkillIdentity,
)
from skill_forge.domain.ports import ClaudeRunner, SkillParser

# ── stubs ─────────────────────────────────────────────────────────────────────


class StubRunner(ClaudeRunner):
    """Returns a fixed response string for all prompts."""

    def __init__(self, response: str = "Hello World") -> None:
        self._response = response

    def run(self, prompt: str, timeout: int = 120) -> str:
        return self._response


class ErrorRunner(ClaudeRunner):
    """Always raises RuntimeError."""

    def run(self, prompt: str, timeout: int = 120) -> str:
        raise RuntimeError("Claude CLI not available")


class JudgeRunner(ClaudeRunner):
    """Returns PASS for the first call; the stub eval output for the second."""

    def __init__(self, eval_output: str, verdict: str = "PASS") -> None:
        self._eval_output = eval_output
        self._verdict = verdict
        self._calls = 0

    def run(self, prompt: str, timeout: int = 120) -> str:
        self._calls += 1
        if "Your verdict" in prompt:
            return self._verdict
        return self._eval_output


class StubParser(SkillParser):
    def parse(self, content, base_path=None):  # type: ignore[override]
        raise NotImplementedError


# ── helpers ───────────────────────────────────────────────────────────────────


def _skill(evals: list[EvalCase]) -> Skill:
    return Skill(
        identity=SkillIdentity(name="my-skill", category="test"),
        description=Description(text="Test skill"),
        content=SkillContent(principles=["Be correct"]),
        evals=evals,
    )


def _request(**kwargs) -> TestSkillRequest:
    return TestSkillRequest(skill_path=".", **kwargs)


# ── basic grading ─────────────────────────────────────────────────────────────


class TestContainsAssertion:
    def test_passes_when_substring_present(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="has hello", type="contains", expected="Hello"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("Hello World"))
        resp = use_case.execute(_request(), _skill([case]))
        assert resp.all_passed
        assert resp.passed_assertions == 1

    def test_fails_when_substring_absent(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="has foo", type="contains", expected="foo"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("Hello World"))
        resp = use_case.execute(_request(), _skill([case]))
        assert not resp.all_passed
        assert resp.failed_assertions == 1
        assert "Expected substring not found" in resp.case_results[0].assertion_results[0].reason


class TestNotContainsAssertion:
    def test_passes_when_substring_absent(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="no error", type="not-contains", expected="ERROR"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("Everything is fine"))
        resp = use_case.execute(_request(), _skill([case]))
        assert resp.all_passed

    def test_fails_when_substring_present(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="no error", type="not-contains", expected="ERROR"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("ERROR: something failed"))
        resp = use_case.execute(_request(), _skill([case]))
        assert not resp.all_passed


class TestRegexAssertion:
    def test_passes_on_match(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="has digits", type="regex", expected=r"\d+"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("The answer is 42"))
        resp = use_case.execute(_request(), _skill([case]))
        assert resp.all_passed

    def test_fails_on_no_match(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="has digits", type="regex", expected=r"\d+"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("No numbers here"))
        resp = use_case.execute(_request(), _skill([case]))
        assert not resp.all_passed

    def test_invalid_regex_fails_gracefully(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="bad regex", type="regex", expected="[invalid"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("anything"))
        resp = use_case.execute(_request(), _skill([case]))
        assert not resp.all_passed
        assert "Invalid regex" in resp.case_results[0].assertion_results[0].reason


class TestLlmJudgeAssertion:
    def test_pass_verdict(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="quality check", type="llm-judge"),
            ),
        )
        use_case = TestSkill(
            parser=StubParser(),
            runner=JudgeRunner(eval_output="Good response", verdict="PASS"),
        )
        resp = use_case.execute(_request(), _skill([case]))
        assert resp.all_passed

    def test_fail_verdict(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a", text="quality check", type="llm-judge"),
            ),
        )
        use_case = TestSkill(
            parser=StubParser(),
            runner=JudgeRunner(eval_output="Bad response", verdict="FAIL"),
        )
        resp = use_case.execute(_request(), _skill([case]))
        assert not resp.all_passed


# ── runner error handling ─────────────────────────────────────────────────────


class TestRunnerErrors:
    def test_runner_error_marks_case_failed(self) -> None:
        case = EvalCase(id=1, prompt="p", expected_output="o")
        use_case = TestSkill(parser=StubParser(), runner=ErrorRunner())
        resp = use_case.execute(_request(), _skill([case]))
        assert not resp.all_passed
        assert resp.case_results[0].error == "Claude CLI not available"


# ── aggregates ────────────────────────────────────────────────────────────────


class TestAggregates:
    def _two_assertion_case(self, pass_first: bool) -> EvalCase:
        expected = "Hello" if pass_first else "NEVER_THERE"
        return EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a1", text="t1", type="contains", expected=expected),
                EvalAssertion(id="a2", text="t2", type="contains", expected="World"),
            ),
        )

    def test_pass_rate_both_pass(self) -> None:
        case = EvalCase(
            id=1, prompt="p", expected_output="o",
            assertions=(
                EvalAssertion(id="a1", text="t1", type="contains", expected="Hello"),
                EvalAssertion(id="a2", text="t2", type="contains", expected="World"),
            ),
        )
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("Hello World"))
        resp = use_case.execute(_request(), _skill([case]))
        assert resp.pass_rate == 1.0
        assert resp.passed_assertions == 2

    def test_pass_rate_partial(self) -> None:
        case = self._two_assertion_case(pass_first=False)
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("Hello World"))
        resp = use_case.execute(_request(), _skill([case]))
        assert resp.passed_assertions == 1
        assert resp.failed_assertions == 1
        assert resp.pass_rate == 0.5

    def test_filter_ids(self) -> None:
        cases = [
            EvalCase(id=1, prompt="p1", expected_output="o"),
            EvalCase(id=2, prompt="p2", expected_output="o"),
        ]
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("x"))
        resp = use_case.execute(_request(filter_ids=[2]), _skill(cases))
        assert len(resp.case_results) == 1
        assert resp.case_results[0].case.id == 2

    def test_no_evals_perfect_pass_rate(self) -> None:
        use_case = TestSkill(parser=StubParser(), runner=StubRunner("x"))
        resp = use_case.execute(_request(), _skill([]))
        assert resp.pass_rate == 1.0
        assert resp.all_passed
