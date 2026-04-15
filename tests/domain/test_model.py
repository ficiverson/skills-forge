"""Tests for domain models."""

from skill_forge.domain.model import (
    Description,
    LintIssue,
    LintReport,
    Severity,
    SkillIdentity,
    StarterCharacter,
)


class TestSkillIdentity:
    def test_slug_lowercases_and_hyphenates(self):
        identity = SkillIdentity(name="Python TDD", category="development")
        assert identity.slug == "python-tdd"

    def test_str_includes_category(self):
        identity = SkillIdentity(name="api-reviewer", category="development")
        assert str(identity) == "development/api-reviewer"


class TestDescription:
    def test_token_estimate_is_roughly_double_word_count(self):
        desc = Description(text="Use this for Python TDD testing")
        assert desc.token_estimate == 12  # 6 words * 2

    def test_short_description_is_within_budget(self):
        desc = Description(text="Short description for testing triggers")
        assert desc.is_within_budget

    def test_long_description_exceeds_budget(self):
        desc = Description(text="word " * 100)
        assert not desc.is_within_budget


class TestStarterCharacter:
    def test_str_returns_emoji(self):
        sc = StarterCharacter(emoji="🔴")
        assert str(sc) == "🔴"


class TestLintReport:
    def test_empty_report_is_clean(self):
        report = LintReport(skill_name="test")
        assert report.is_clean
        assert not report.has_errors

    def test_report_with_error_is_not_clean(self):
        report = LintReport(skill_name="test")
        report.add(
            LintIssue(
                rule="test-rule",
                message="something wrong",
                severity=Severity.ERROR,
            )
        )
        assert not report.is_clean
        assert report.has_errors
        assert report.error_count == 1

    def test_report_counts_by_severity(self):
        report = LintReport(skill_name="test")
        report.add(LintIssue(rule="r1", message="e1", severity=Severity.ERROR))
        report.add(LintIssue(rule="r2", message="w1", severity=Severity.WARNING))
        report.add(LintIssue(rule="r3", message="w2", severity=Severity.WARNING))
        report.add(LintIssue(rule="r4", message="i1", severity=Severity.INFO))

        assert report.error_count == 1
        assert report.warning_count == 2

    def test_lint_issue_str_format(self):
        issue = LintIssue(
            rule="test-rule",
            message="fix this",
            severity=Severity.ERROR,
            location="SKILL.md",
        )
        assert "[ERROR]" in str(issue)
        assert "test-rule" in str(issue)
        assert "(SKILL.md)" in str(issue)
