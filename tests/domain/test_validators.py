"""Tests for domain validators."""

from __future__ import annotations

from skill_forge.domain.model import Severity, Skill
from skill_forge.domain.validators import (
    validate_context_budget,
    validate_description_length,
    validate_description_precision,
    validate_description_trigger_words,
    validate_has_principles,
    validate_references_depth,
    validate_single_responsibility,
    validate_starter_character,
)


class TestDescriptionLengthValidator:
    def test_good_description_has_no_issues(self, minimal_skill: Skill):
        issues = validate_description_length(minimal_skill)
        assert len(issues) == 0

    def test_too_short_description_warns(self, minimal_skill: Skill):
        from skill_forge.domain.model import Description

        skill = Skill(
            identity=minimal_skill.identity,
            description=Description(text="short"),
        )
        issues = validate_description_length(skill)
        assert len(issues) == 1
        assert issues[0].severity == Severity.WARNING
        assert issues[0].rule == "description-too-short"

    def test_too_long_description_errors(self, bloated_skill: Skill):
        issues = validate_description_length(bloated_skill)
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR


class TestDescriptionPrecisionValidator:
    def test_clean_description_passes(self, minimal_skill: Skill):
        issues = validate_description_precision(minimal_skill)
        assert len(issues) == 0

    def test_vague_words_produce_warnings(self, bloated_skill: Skill):
        issues = validate_description_precision(bloated_skill)
        vague_issues = [i for i in issues if i.rule == "description-vague-language"]
        assert len(vague_issues) > 0

    def test_overly_broad_phrases_produce_errors(self, bloated_skill: Skill):
        issues = validate_description_precision(bloated_skill)
        broad_issues = [i for i in issues if i.rule == "description-overly-broad"]
        assert len(broad_issues) > 0


class TestDescriptionTriggerWordsValidator:
    def test_description_with_triggers_passes(self, minimal_skill: Skill):
        issues = validate_description_trigger_words(minimal_skill)
        assert len(issues) == 0

    def test_description_without_triggers_warns(self):
        from skill_forge.domain.model import Description, SkillContent, SkillIdentity

        skill = Skill(
            identity=SkillIdentity(name="vague", category="misc"),
            description=Description(text="A skill for doing some things nicely"),
            content=SkillContent(),
        )
        issues = validate_description_trigger_words(skill)
        assert len(issues) == 1
        assert issues[0].rule == "description-missing-triggers"


class TestHasPrinciplesValidator:
    def test_skill_with_principles_passes(self, minimal_skill: Skill):
        issues = validate_has_principles(minimal_skill)
        assert len(issues) == 0

    def test_skill_without_principles_warns(self, bloated_skill: Skill):
        issues = validate_has_principles(bloated_skill)
        assert len(issues) == 1
        assert issues[0].rule == "missing-principles"


class TestContextBudgetValidator:
    def test_lean_skill_passes(self, minimal_skill: Skill):
        issues = validate_context_budget(minimal_skill)
        assert len(issues) == 0

    def test_bloated_skill_errors(self, bloated_skill: Skill):
        issues = validate_context_budget(bloated_skill)
        assert len(issues) == 1
        assert issues[0].severity == Severity.ERROR


class TestReferencesDepthValidator:
    def test_flat_references_pass(self, skill_with_references: Skill):
        issues = validate_references_depth(skill_with_references)
        assert len(issues) == 0

    def test_deeply_nested_references_warn(self, bloated_skill: Skill):
        issues = validate_references_depth(bloated_skill)
        assert len(issues) == 1
        assert issues[0].rule == "reference-too-deep"


class TestSingleResponsibilityValidator:
    def test_focused_skill_passes(self, minimal_skill: Skill):
        issues = validate_single_responsibility(minimal_skill)
        assert len(issues) == 0

    def test_verbose_skill_gets_info(self, bloated_skill: Skill):
        issues = validate_single_responsibility(bloated_skill)
        assert len(issues) == 1
        assert issues[0].severity == Severity.INFO


class TestStarterCharacterValidator:
    def test_skill_with_starter_passes(self, minimal_skill: Skill):
        issues = validate_starter_character(minimal_skill)
        assert len(issues) == 0

    def test_skill_without_starter_gets_info(self, bloated_skill: Skill):
        issues = validate_starter_character(bloated_skill)
        assert len(issues) == 1
        assert issues[0].rule == "missing-starter-character"
