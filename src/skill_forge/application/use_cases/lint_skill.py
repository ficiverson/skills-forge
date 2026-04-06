"""Use case: lint an existing skill and report issues."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_forge.domain.model import LintReport, Skill
from skill_forge.domain.ports import SkillParser
from skill_forge.domain.validators import ALL_VALIDATORS, PATH_AWARE_VALIDATORS


@dataclass
class LintSkillRequest:
    """Input: either a Skill object or a path to parse."""

    skill: Skill | None = None
    path: Path | None = None


@dataclass
class LintSkillResponse:
    """Output: the lint report."""

    report: LintReport


class LintSkill:
    """Runs all domain validators against a skill.

    Two kinds of validators run:
    - Pure validators: receive only the Skill object
    - Path-aware validators: also receive the skill directory, enabling
      filesystem checks like broken reference links
    """

    def __init__(self, parser: SkillParser | None = None) -> None:
        self._parser = parser

    def execute(self, request: LintSkillRequest) -> LintSkillResponse:
        skill = self._resolve_skill(request)
        skill_dir = self._resolve_skill_dir(request)
        report = LintReport(skill_name=str(skill.identity))

        for pure_v in ALL_VALIDATORS:
            for issue in pure_v(skill):
                report.add(issue)

        for path_v in PATH_AWARE_VALIDATORS:
            for issue in path_v(skill, skill_dir):
                report.add(issue)

        return LintSkillResponse(report=report)

    def _resolve_skill(self, request: LintSkillRequest) -> Skill:
        if request.skill is not None:
            return request.skill

        if request.path is not None and self._parser is not None:
            content = request.path.read_text(encoding="utf-8")
            return self._parser.parse(content, base_path=request.path.parent)

        raise ValueError(
            "LintSkillRequest requires either a Skill object or a path "
            "with a configured parser."
        )

    def _resolve_skill_dir(self, request: LintSkillRequest) -> Path | None:
        if request.path is not None:
            return request.path.parent if request.path.is_file() else request.path
        return None
