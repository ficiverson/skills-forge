"""Tests for LintService — bulk lint orchestration across a skill repository."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from skill_forge.application.services.lint_service import BulkLintResponse, LintService
from skill_forge.domain.model import LintIssue, LintReport, Severity, Skill


def _make_skill(name: str = "test-skill", category: str = "dev") -> Skill:
    from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
    md = (
        f"---\nname: {name}\n"
        f"description: |\n  Use when testing {name}. Triggers on: test.\n"
        f"---\n\n## Instructions\n\nDo stuff.\n"
    )
    return MarkdownSkillParser().parse(md)


def _clean_report(name: str = "test-skill") -> LintReport:
    return LintReport(skill_name=name, issues=())


def _warning_report(name: str = "warn-skill") -> LintReport:
    return LintReport(
        skill_name=name,
        issues=(LintIssue(rule="W001", severity=Severity.WARNING, message="weak description"),),
    )


def _error_report(name: str = "bad-skill") -> LintReport:
    return LintReport(
        skill_name=name,
        issues=(LintIssue(rule="E001", severity=Severity.ERROR, message="name mismatch"),),
    )


class TestBulkLintResponse:
    def test_total_errors_sums_across_reports(self) -> None:
        resp = BulkLintResponse(
            reports=[_clean_report(), _error_report(), _error_report("x")]
        )
        assert resp.total_errors == 2

    def test_total_warnings_sums_across_reports(self) -> None:
        resp = BulkLintResponse(
            reports=[_warning_report(), _warning_report("y"), _clean_report()]
        )
        assert resp.total_warnings == 2

    def test_all_clean_true_when_no_issues(self) -> None:
        resp = BulkLintResponse(reports=[_clean_report(), _clean_report("b")])
        assert resp.all_clean is True

    def test_all_clean_false_when_any_has_issues(self) -> None:
        resp = BulkLintResponse(reports=[_clean_report(), _warning_report()])
        assert resp.all_clean is False


class TestLintServiceLintAll:
    def test_lint_all_returns_one_report_per_skill(self) -> None:
        skill_a = _make_skill("skill-a")
        skill_b = _make_skill("skill-b")

        mock_repo = MagicMock()
        mock_repo.list_all.return_value = [skill_a, skill_b]

        mock_parser = MagicMock()
        mock_parser.parse.return_value = skill_a  # same skill returned for any path

        service = LintService(repository=mock_repo, parser=mock_parser)
        response = service.lint_all()

        assert len(response.reports) == 2

    def test_lint_all_empty_repo_returns_empty(self) -> None:
        mock_repo = MagicMock()
        mock_repo.list_all.return_value = []
        mock_parser = MagicMock()

        service = LintService(repository=mock_repo, parser=mock_parser)
        response = service.lint_all()

        assert response.reports == []
        assert response.all_clean is True
        assert response.total_errors == 0
        assert response.total_warnings == 0


class TestLintServiceLintPaths:
    def test_lint_paths_with_real_skill_md(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "dev" / "my-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: my-skill\n"
            "description: |\n"
            "  Use this when running integration tests. Triggers on: test, "
            "validate, quality.\n"
            "---\n\n"
            "## Instructions\n\nDo stuff.\n",
            encoding="utf-8",
        )

        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        parser = MarkdownSkillParser()
        mock_repo = MagicMock()

        service = LintService(repository=mock_repo, parser=parser)
        response = service.lint_paths([skill_dir / "SKILL.md"])

        assert len(response.reports) == 1

    def test_lint_paths_collects_all_reports(self, tmp_path: Path) -> None:
        paths = []
        for n in range(3):
            d = tmp_path / f"skill-{n}"
            d.mkdir()
            md = d / "SKILL.md"
            md.write_text(
                f"---\nname: skill-{n}\ndescription: |\n"
                f"  Use this for testing skill {n}. Triggers on: test.\n"
                f"---\n\n## Instructions\n\nDo {n}.\n",
                encoding="utf-8",
            )
            paths.append(md)

        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        parser = MarkdownSkillParser()
        service = LintService(repository=MagicMock(), parser=parser)
        response = service.lint_paths(paths)

        assert len(response.reports) == 3
