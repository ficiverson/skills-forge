"""Application service: orchestrates linting across multiple skills."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_forge.application.use_cases.lint_skill import LintSkill, LintSkillRequest
from skill_forge.domain.model import LintReport
from skill_forge.domain.ports import SkillParser, SkillRepository


@dataclass
class BulkLintResponse:
    reports: list[LintReport]

    @property
    def total_errors(self) -> int:
        return sum(r.error_count for r in self.reports)

    @property
    def total_warnings(self) -> int:
        return sum(r.warning_count for r in self.reports)

    @property
    def all_clean(self) -> bool:
        return all(r.is_clean for r in self.reports)


class LintService:
    """Lint all skills in a repository or a list of paths."""

    def __init__(
        self,
        repository: SkillRepository,
        parser: SkillParser,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._lint_use_case = LintSkill(parser=parser)

    def lint_all(self) -> BulkLintResponse:
        skills = self._repository.list_all()
        reports = []
        for skill in skills:
            request = LintSkillRequest(skill=skill)
            response = self._lint_use_case.execute(request)
            reports.append(response.report)
        return BulkLintResponse(reports=reports)

    def lint_paths(self, paths: list[Path]) -> BulkLintResponse:
        reports = []
        for path in paths:
            request = LintSkillRequest(path=path)
            response = self._lint_use_case.execute(request)
            reports.append(response.report)
        return BulkLintResponse(reports=reports)
