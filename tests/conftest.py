"""Shared test fixtures."""

from __future__ import annotations

from pathlib import PurePosixPath

import pytest

from skill_forge.domain.model import (
    Asset,
    Dependency,
    Description,
    Example,
    Reference,
    Script,
    Skill,
    SkillContent,
    SkillIdentity,
    StarterCharacter,
)


@pytest.fixture
def minimal_skill() -> Skill:
    """A well-formed minimal skill for testing."""
    return Skill(
        identity=SkillIdentity(name="python-tdd", category="development"),
        description=Description(
            text="Use this skill when writing Python code with TDD. "
            "Triggers on: test-first, red-green-refactor, pytest, "
            "unit testing .py files."
        ),
        starter_character=StarterCharacter(emoji="🔴"),
        content=SkillContent(
            principles=[
                "Write the failing test first",
                "Make it pass with minimal code",
                "Refactor only when green",
            ],
            instructions="Follow the red-green-refactor cycle strictly.",
            constraints=["Never skip the red phase"],
        ),
    )


@pytest.fixture
def bloated_skill() -> Skill:
    """A skill that violates several clean principles."""
    return Skill(
        identity=SkillIdentity(name="do-everything", category="misc"),
        description=Description(
            text="This skill helps with any task and handles everything "
            "related to various things in any situation. It manages "
            "stuff and assists with all tasks whenever needed. " * 5
        ),
        content=SkillContent(
            principles=[],
            instructions="Do whatever the user asks. " * 200,
            constraints=[],
        ),
        references=[
            Reference(
                path=PurePosixPath("references/deep/nested/file.md"),
                purpose="some doc",
            ),
        ],
    )


@pytest.fixture
def skill_with_references() -> Skill:
    """A skill with properly structured references."""
    return Skill(
        identity=SkillIdentity(name="api-reviewer", category="development"),
        description=Description(
            text="Review REST API designs for consistency, naming conventions, "
            "and HTTP semantics. Triggers on: API review, endpoint design, "
            "REST conventions, OpenAPI .yaml .json."
        ),
        starter_character=StarterCharacter(emoji="🔍"),
        content=SkillContent(
            principles=[
                "Consistent naming over clever naming",
                "HTTP methods carry semantics",
                "Errors should be informative",
            ],
            instructions="Analyze the API surface and report issues.",
            constraints=["Don't rewrite the entire API, focus on actionable feedback"],
        ),
        references=[
            Reference(
                path=PurePosixPath("references/rest-conventions.md"),
                purpose="REST naming conventions",
            ),
            Reference(
                path=PurePosixPath("references/http-status-codes.md"),
                purpose="HTTP status code guide",
            ),
        ],
    )


@pytest.fixture
def full_featured_skill() -> Skill:
    """A skill using all new features: scripts, examples, assets, depends_on, hints."""
    return Skill(
        identity=SkillIdentity(name="eval-runner", category="evaluation"),
        description=Description(
            text="Evaluate code challenge submissions and generate PDF reports. "
            "Triggers on: evaluate, score candidate, grade challenge, "
            "review submission, competency matrix."
        ),
        starter_character=StarterCharacter(emoji="⚖️"),
        content=SkillContent(
            principles=[
                "Evidence over impression",
                "Read actual code, not just structure",
            ],
            instructions="Score competencies, audit practices, generate report.",
            constraints=["Do not hallucinate evidence"],
            hints="If the repo has no tests, score code_quality <= 4.\n"
            "If AI workflow tooling is detected, apply inflation rules.",
        ),
        references=[
            Reference(
                path=PurePosixPath("references/scoring-guide.md"),
                purpose="Scoring anchors",
            ),
        ],
        scripts=[
            Script(
                path=PurePosixPath("scripts/generate_report.py"),
                description="Generate PDF report",
            ),
            Script(
                path=PurePosixPath("scripts/validate_output.py"),
                description="Validate output JSON",
            ),
        ],
        examples=[
            Example(
                path=PurePosixPath("examples/sample-eval.json"),
                description="Example evaluation output",
            ),
        ],
        assets=[
            Asset(
                path=PurePosixPath("assets/thresholds.csv"),
                description="Level threshold data",
            ),
        ],
        depends_on=[
            Dependency(skill_name="pdf", reason="PDF generation"),
        ],
    )
