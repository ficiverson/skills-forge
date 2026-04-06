"""Tests for the lint skill use case."""

from skill_forge.application.use_cases.lint_skill import LintSkill, LintSkillRequest
from skill_forge.domain.model import Skill


class TestLintSkillUseCase:
    def test_clean_skill_produces_clean_report(self, minimal_skill: Skill):
        use_case = LintSkill()
        request = LintSkillRequest(skill=minimal_skill)
        response = use_case.execute(request)

        assert response.report.skill_name == "development/python-tdd"
        assert not response.report.has_errors

    def test_bloated_skill_produces_errors(self, bloated_skill: Skill):
        use_case = LintSkill()
        request = LintSkillRequest(skill=bloated_skill)
        response = use_case.execute(request)

        assert response.report.has_errors
        assert response.report.error_count > 0

    def test_raises_without_skill_or_path(self):
        use_case = LintSkill()
        request = LintSkillRequest()

        try:
            use_case.execute(request)
            raise AssertionError("Should have raised ValueError")
        except ValueError:
            pass
