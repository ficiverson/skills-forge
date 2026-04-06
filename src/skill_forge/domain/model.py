"""Domain models for skill-forge.

These are pure data structures with no dependencies on infrastructure.
They represent the core concepts of a Claude Code skill.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SkillScope(Enum):
    GLOBAL = "global"
    PROJECT = "project"


@dataclass(frozen=True)
class SkillIdentity:
    """Value object: uniquely identifies a skill."""

    name: str
    category: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Skill name cannot be empty")
        if not self.category or not self.category.strip():
            raise ValueError("Skill category cannot be empty")

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-")

    def __str__(self) -> str:
        return f"{self.category}/{self.slug}"


@dataclass(frozen=True)
class Description:
    """Value object: the trigger description shown to Claude.

    This is the single most important piece of a skill — it determines
    when Claude activates it. Keep it lean, precise, and third-person.
    """

    text: str

    @property
    def token_estimate(self) -> int:
        return len(self.text.split()) * 2

    @property
    def is_within_budget(self) -> bool:
        return self.token_estimate <= 150


@dataclass(frozen=True)
class StarterCharacter:
    """Value object: visual emoji confirming skill activation."""

    emoji: str

    def __str__(self) -> str:
        return self.emoji


@dataclass(frozen=True)
class Reference:
    """A supporting document loaded on-demand to save context."""

    path: PurePosixPath
    purpose: str

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class Script:
    """An executable script bundled with the skill."""

    path: PurePosixPath
    description: str


@dataclass(frozen=True)
class Asset:
    """A static asset bundled with the skill (data files, images, templates)."""

    path: PurePosixPath
    description: str


@dataclass(frozen=True)
class Example:
    """An example output demonstrating the expected result format."""

    path: PurePosixPath
    description: str


@dataclass(frozen=True)
class Dependency:
    """A skill that this skill depends on for composed workflows."""

    skill_name: str
    reason: str

    def __post_init__(self) -> None:
        if not self.skill_name or not self.skill_name.strip():
            raise ValueError("Dependency skill_name cannot be empty")
        if " " in self.skill_name.strip():
            raise ValueError(
                f"Dependency skill_name '{self.skill_name}' must be "
                f"kebab-case (no spaces)"
            )


@dataclass
class SkillContent:
    """The body of a SKILL.md — instructions that Claude follows."""

    principles: list[str] = field(default_factory=list)
    instructions: str = ""
    constraints: list[str] = field(default_factory=list)

    hints: str = ""

    @property
    def estimated_tokens(self) -> int:
        total_words = len(self.instructions.split())
        total_words += sum(len(p.split()) for p in self.principles)
        total_words += sum(len(c.split()) for c in self.constraints)
        if self.hints:
            total_words += len(self.hints.split())
        return total_words * 2


@dataclass
class Skill:
    """Aggregate root: a complete Claude Code skill."""

    identity: SkillIdentity
    description: Description
    starter_character: StarterCharacter | None = None
    content: SkillContent = field(default_factory=SkillContent)
    references: list[Reference] = field(default_factory=list)
    scripts: list[Script] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    examples: list[Example] = field(default_factory=list)
    depends_on: list[Dependency] = field(default_factory=list)

    @property
    def total_estimated_tokens(self) -> int:
        return self.description.token_estimate + self.content.estimated_tokens

    @property
    def has_references(self) -> bool:
        return len(self.references) > 0

    @property
    def has_scripts(self) -> bool:
        return len(self.scripts) > 0

    @property
    def has_assets(self) -> bool:
        return len(self.assets) > 0

    @property
    def has_examples(self) -> bool:
        return len(self.examples) > 0

    @property
    def has_dependencies(self) -> bool:
        return len(self.depends_on) > 0


@dataclass(frozen=True)
class LintIssue:
    """A single issue found during skill validation."""

    rule: str
    message: str
    severity: Severity
    location: str | None = None

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        loc = f" ({self.location})" if self.location else ""
        return f"{prefix} {self.rule}{loc}: {self.message}"


@dataclass
class LintReport:
    """The result of validating a skill."""

    skill_name: str
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0

    def add(self, issue: LintIssue) -> None:
        self.issues.append(issue)
