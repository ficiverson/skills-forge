"""Domain validators: pure business rules for skill quality.

Each validator is a small, focused function following SRP.
They receive a Skill and return LintIssues — no side effects.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from skill_forge.domain.model import (
    LintIssue,
    Severity,
    Skill,
)

# Type aliases for the two validator signatures
SkillValidator = Callable[[Skill], list[LintIssue]]
PathAwareValidator = Callable[[Skill, Path | None], list[LintIssue]]

# --- Description validators ---

VAGUE_WORDS = frozenset({
    "stuff", "things", "various", "misc", "general", "generic",
    "help", "assist", "handle", "manage", "deal with", "work with",
    "etc", "and so on", "similar", "other", "whatever",
})

OVERLY_BROAD_PHRASES = frozenset({
    "any task", "all tasks", "everything", "anything",
    "any situation", "all situations", "whenever needed",
    "all purposes", "any purpose", "any kind",
})


def validate_description_length(skill: Skill) -> list[LintIssue]:
    """Description should be concise but informative (30-150 tokens)."""
    issues = []
    tokens = skill.description.token_estimate

    if tokens < 30:
        issues.append(LintIssue(
            rule="description-too-short",
            message=f"Description is ~{tokens} tokens. Aim for 30-150 to give "
                    f"Claude enough context to trigger correctly.",
            severity=Severity.WARNING,
            location="frontmatter.description",
        ))
    elif tokens > 150:
        issues.append(LintIssue(
            rule="description-too-long",
            message=f"Description is ~{tokens} tokens. Over 150 tokens wastes "
                    f"context at startup. Be more concise.",
            severity=Severity.ERROR,
            location="frontmatter.description",
        ))
    return issues


def validate_description_precision(skill: Skill) -> list[LintIssue]:
    """Description should avoid vague or overly broad language."""
    issues = []
    text_lower = skill.description.text.lower()

    for word in VAGUE_WORDS:
        if word in text_lower:
            issues.append(LintIssue(
                rule="description-vague-language",
                message=f'Avoid vague word "{word}". Use specific trigger '
                        f"terms that match real user intents.",
                severity=Severity.WARNING,
                location="frontmatter.description",
            ))

    for phrase in OVERLY_BROAD_PHRASES:
        if phrase in text_lower:
            issues.append(LintIssue(
                rule="description-overly-broad",
                message=f'Phrase "{phrase}" is too broad and will cause false '
                        f"positives. Narrow the scope.",
                severity=Severity.ERROR,
                location="frontmatter.description",
            ))

    return issues


def validate_description_trigger_words(skill: Skill) -> list[LintIssue]:
    """Description should contain concrete trigger words or file extensions."""
    issues = []
    text = skill.description.text

    has_extension = any(
        ext in text for ext in [".py", ".ts", ".js", ".md", ".yaml", ".json",
                                ".toml", ".rs", ".go", ".java", ".rb", ".sh",
                                ".docx", ".xlsx", ".pptx", ".pdf", ".csv"]
    )
    has_action_verb = any(
        verb in text.lower()
        for verb in ["create", "generate", "write", "build", "test", "lint",
                     "validate", "format", "convert", "analyze", "review",
                     "deploy", "refactor", "debug", "extract", "parse"]
    )

    if not has_extension and not has_action_verb:
        issues.append(LintIssue(
            rule="description-missing-triggers",
            message="Description lacks concrete triggers (file extensions or "
                    "action verbs). Add specific terms so Claude knows when "
                    "to activate this skill.",
            severity=Severity.WARNING,
            location="frontmatter.description",
        ))

    return issues


# --- Structure validators ---


def validate_has_principles(skill: Skill) -> list[LintIssue]:
    """Skills should define guiding principles, not just instructions."""
    if not skill.content.principles:
        return [LintIssue(
            rule="missing-principles",
            message="No principles defined. Principles guide Claude's "
                    "decision-making better than step-by-step instructions.",
            severity=Severity.WARNING,
            location="SKILL.md body",
        )]
    return []


def validate_context_budget(skill: Skill) -> list[LintIssue]:
    """Total token cost should stay reasonable."""
    issues = []
    total = skill.total_estimated_tokens

    if total > 2000:
        issues.append(LintIssue(
            rule="context-budget-exceeded",
            message=f"Skill uses ~{total} tokens. Over 2000 tokens risks "
                    f"context rot. Move details to references/.",
            severity=Severity.ERROR,
            location="SKILL.md",
        ))
    elif total > 1200:
        issues.append(LintIssue(
            rule="context-budget-high",
            message=f"Skill uses ~{total} tokens. Consider moving some "
                    f"content to references/ for on-demand loading.",
            severity=Severity.WARNING,
            location="SKILL.md",
        ))

    return issues


def validate_references_depth(skill: Skill) -> list[LintIssue]:
    """References should be one level deep — no index chains."""
    issues = []
    for ref in skill.references:
        parts = ref.path.parts
        # references/subdir/file = 3 levels = too deep
        if len(parts) > 2:
            issues.append(LintIssue(
                rule="reference-too-deep",
                message=f'Reference "{ref.path}" is nested too deeply. '
                        f"Keep references one level deep for direct access.",
                severity=Severity.WARNING,
                location=str(ref.path),
            ))
    return issues


def validate_single_responsibility(skill: Skill) -> list[LintIssue]:
    """A skill should focus on one cohesive concern."""
    issues = []
    word_count = len(skill.content.instructions.split())

    if word_count > 800:
        issues.append(LintIssue(
            rule="possible-srp-violation",
            message=f"Instructions are ~{word_count} words. If the skill "
                    f"covers multiple concerns, consider splitting it.",
            severity=Severity.INFO,
            location="SKILL.md body",
        ))

    return issues


def validate_starter_character(skill: Skill) -> list[LintIssue]:
    """Starter character helps confirm activation visually."""
    if skill.starter_character is None:
        return [LintIssue(
            rule="missing-starter-character",
            message="No STARTER_CHARACTER defined. Adding one helps you "
                    "confirm the skill activated correctly.",
            severity=Severity.INFO,
            location="SKILL.md body",
        )]
    return []


# --- Filesystem-aware validators (require skill directory path) ---


def validate_reference_links(skill: Skill, skill_dir: Path | None = None) -> list[LintIssue]:
    """Every reference path in SKILL.md must resolve to a real file."""
    if skill_dir is None or not skill.references:
        return []

    issues = []
    for ref in skill.references:
        resolved = skill_dir / str(ref.path)
        if not resolved.exists():
            issues.append(LintIssue(
                rule="broken-reference-link",
                message=f'Reference "{ref.path}" does not exist at '
                        f"{resolved}. Fix the path or create the file.",
                severity=Severity.ERROR,
                location=str(ref.path),
            ))
    return issues


def validate_example_files(skill: Skill, skill_dir: Path | None = None) -> list[LintIssue]:
    """Example output files referenced in SKILL.md must exist on disk."""
    if skill_dir is None or not skill.examples:
        return []

    issues = []
    for example in skill.examples:
        resolved = skill_dir / str(example.path)
        if not resolved.exists():
            issues.append(LintIssue(
                rule="broken-example-link",
                message=f'Example "{example.path}" does not exist at '
                        f"{resolved}. Add the example file.",
                severity=Severity.ERROR,
                location=str(example.path),
            ))
    return issues


def validate_asset_files(skill: Skill, skill_dir: Path | None = None) -> list[LintIssue]:
    """Asset files referenced in SKILL.md must exist on disk."""
    if skill_dir is None or not skill.assets:
        return []

    issues = []
    for asset in skill.assets:
        resolved = skill_dir / str(asset.path)
        if not resolved.exists():
            issues.append(LintIssue(
                rule="broken-asset-link",
                message=f'Asset "{asset.path}" does not exist at '
                        f"{resolved}. Add the asset file.",
                severity=Severity.ERROR,
                location=str(asset.path),
            ))
    return issues


def validate_script_files(skill: Skill, skill_dir: Path | None = None) -> list[LintIssue]:
    """Script files referenced in SKILL.md must exist on disk."""
    if skill_dir is None or not skill.scripts:
        return []

    issues = []
    for script in skill.scripts:
        resolved = skill_dir / str(script.path)
        if not resolved.exists():
            issues.append(LintIssue(
                rule="broken-script-link",
                message=f'Script "{script.path}" does not exist at '
                        f"{resolved}. Add the script file.",
                severity=Severity.ERROR,
                location=str(script.path),
            ))
    return issues


def validate_skill_name_format(skill: Skill) -> list[LintIssue]:
    """Skill name should follow kebab-case or slug-friendly format."""
    import re as _re

    name = skill.identity.name
    if not _re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
        return [LintIssue(
            rule="invalid-skill-name",
            message=f'Skill name "{name}" should be lowercase kebab-case '
                    f"(e.g., 'python-tdd', 'api-reviewer').",
            severity=Severity.WARNING,
            location="frontmatter.name",
        )]
    return []


def validate_has_examples(skill: Skill) -> list[LintIssue]:
    """Skills with scripts should have example outputs to calibrate Claude."""
    if skill.has_scripts and not skill.has_examples:
        return [LintIssue(
            rule="missing-examples",
            message="Skill has scripts but no example outputs. Add an "
                    "examples/ directory with sample outputs so Claude can "
                    "calibrate format and quality.",
            severity=Severity.INFO,
            location="SKILL.md",
        )]
    return []


def validate_dependency_exists(skill: Skill) -> list[LintIssue]:
    """Dependencies should reference well-formed skill names."""
    issues = []
    for dep in skill.depends_on:
        if not dep.skill_name or " " in dep.skill_name:
            issues.append(LintIssue(
                rule="invalid-dependency-name",
                message=f'Dependency "{dep.skill_name}" is not a valid skill '
                        f"slug. Use kebab-case names.",
                severity=Severity.ERROR,
                location="frontmatter.depends_on",
            ))
    return issues


# --- Registry of all validators ---

ALL_VALIDATORS: list[SkillValidator] = [
    validate_skill_name_format,
    validate_description_length,
    validate_description_precision,
    validate_description_trigger_words,
    validate_has_principles,
    validate_context_budget,
    validate_references_depth,
    validate_single_responsibility,
    validate_starter_character,
    validate_has_examples,
    validate_dependency_exists,
]

PATH_AWARE_VALIDATORS: list[PathAwareValidator] = [
    validate_reference_links,
    validate_example_files,
    validate_asset_files,
    validate_script_files,
]
