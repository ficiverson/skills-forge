"""Use case: run evals for a skill and grade each assertion.

Assertion types
---------------
contains     — output must include ``expected`` as a literal substring
not-contains — output must NOT include ``expected`` as a literal substring
regex        — output must match the ``expected`` regular expression
llm-judge    — a secondary LLM call decides whether the output satisfies
               the criterion in ``text``; ``expected`` is ignored

The use case is pure Python and decoupled from any CLI.  Callers inject a
``SkillParser`` and a ``ClaudeRunner`` port so the runner can be stubbed in
tests without spawning real subprocess calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from skill_forge.domain.model import EvalAssertion, EvalCase, Skill
from skill_forge.domain.ports import ClaudeRunner, SkillParser

# ── result types ─────────────────────────────────────────────────────────────


@dataclass
class AssertionResult:
    assertion: EvalAssertion
    passed: bool
    reason: str = ""


@dataclass
class EvalCaseResult:
    case: EvalCase
    response: str
    assertion_results: list[AssertionResult] = field(default_factory=list)
    error: str = ""

    @property
    def passed(self) -> bool:
        if self.error:
            return False
        return all(r.passed for r in self.assertion_results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.assertion_results if r.passed)

    @property
    def total_count(self) -> int:
        return len(self.assertion_results)


@dataclass
class AssessSkillResponse:
    skill_name: str
    case_results: list[EvalCaseResult] = field(default_factory=list)

    @property
    def total_assertions(self) -> int:
        return sum(r.total_count for r in self.case_results)

    @property
    def passed_assertions(self) -> int:
        return sum(r.pass_count for r in self.case_results)

    @property
    def failed_assertions(self) -> int:
        return self.total_assertions - self.passed_assertions

    @property
    def pass_rate(self) -> float:
        if self.total_assertions == 0:
            return 1.0
        return self.passed_assertions / self.total_assertions

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.case_results)


# ── request ───────────────────────────────────────────────────────────────────


@dataclass
class AssessSkillRequest:
    skill_path: str  # path to skill directory
    filter_ids: list[int] = field(default_factory=list)  # run only these case IDs
    timeout: int = 120  # seconds per eval call


# ── use case ──────────────────────────────────────────────────────────────────


class AssessSkill:
    """Run evals for a skill and grade every assertion."""

    def __init__(self, parser: SkillParser, runner: ClaudeRunner) -> None:
        self._parser = parser
        self._runner = runner

    def execute(self, request: AssessSkillRequest, skill: Skill) -> AssessSkillResponse:
        cases = skill.evals
        if request.filter_ids:
            cases = [c for c in cases if c.id in request.filter_ids]

        response = AssessSkillResponse(skill_name=skill.identity.name)

        for case in cases:
            case_result = self._run_case(case, skill, request.timeout)
            response.case_results.append(case_result)

        return response

    # ── internal ─────────────────────────────────────────────────────────────

    def _run_case(
        self, case: EvalCase, skill: Skill, timeout: int
    ) -> EvalCaseResult:
        try:
            output = self._runner.run(case.prompt, timeout=timeout)
        except Exception as exc:
            return EvalCaseResult(case=case, response="", error=str(exc))

        results: list[AssertionResult] = []
        for assertion in case.assertions:
            result = self._grade(assertion, output, timeout)
            results.append(result)

        return EvalCaseResult(case=case, response=output, assertion_results=results)

    def _grade(
        self, assertion: EvalAssertion, output: str, timeout: int
    ) -> AssertionResult:
        atype = assertion.type

        if atype == "contains":
            passed = assertion.expected in output
            reason = (
                "" if passed
                else f"Expected substring not found: {assertion.expected!r}"
            )
            return AssertionResult(assertion=assertion, passed=passed, reason=reason)

        if atype == "not-contains":
            passed = assertion.expected not in output
            reason = (
                "" if passed
                else f"Unexpected substring found: {assertion.expected!r}"
            )
            return AssertionResult(assertion=assertion, passed=passed, reason=reason)

        if atype == "regex":
            try:
                passed = bool(re.search(assertion.expected, output))
                reason = (
                    "" if passed
                    else f"Regex did not match: {assertion.expected!r}"
                )
            except re.error as exc:
                passed = False
                reason = f"Invalid regex {assertion.expected!r}: {exc}"
            return AssertionResult(assertion=assertion, passed=passed, reason=reason)

        if atype == "llm-judge":
            return self._grade_llm_judge(assertion, output, timeout)

        # Unknown type — shouldn't reach here if linter ran
        return AssertionResult(
            assertion=assertion,
            passed=False,
            reason=f"Unknown assertion type: {atype!r}",
        )

    def _grade_llm_judge(
        self, assertion: EvalAssertion, output: str, timeout: int
    ) -> AssertionResult:
        judge_prompt = (
            "You are a precise evaluator. I will give you an AI output and a "
            "quality criterion. Reply with EXACTLY one word: PASS or FAIL.\n\n"
            f"CRITERION: {assertion.text}\n\n"
            f"OUTPUT:\n{output}\n\n"
            "Your verdict (PASS or FAIL):"
        )
        try:
            verdict = self._runner.run(judge_prompt, timeout=timeout).strip().upper()
            passed = verdict.startswith("PASS")
            reason = "" if passed else f"LLM judge returned: {verdict!r}"
        except Exception as exc:
            passed = False
            reason = f"LLM judge error: {exc}"
        return AssertionResult(assertion=assertion, passed=passed, reason=reason)
