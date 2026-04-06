"""Use case: create a new skill from a specification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_forge.domain.model import (
    DEFAULT_SKILL_VERSION,
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
from skill_forge.domain.ports import SkillRenderer, SkillRepository


@dataclass
class CreateSkillRequest:
    """Input DTO for the create-skill use case."""

    name: str
    category: str
    description: str
    starter_emoji: str | None = None
    version: str = DEFAULT_SKILL_VERSION
    principles: list[str] | None = None
    instructions: str = ""
    constraints: list[str] | None = None
    hints: str = ""
    references: list[dict[str, str]] | None = None
    scripts: list[dict[str, str]] | None = None
    assets: list[dict[str, str]] | None = None
    examples: list[dict[str, str]] | None = None
    depends_on: list[dict[str, str]] | None = None


@dataclass
class CreateSkillResponse:
    """Output DTO for the create-skill use case."""

    path: Path
    skill: Skill
    already_existed: bool = False


class CreateSkill:
    """Creates a new skill and persists it via the repository."""

    def __init__(
        self,
        repository: SkillRepository,
        renderer: SkillRenderer,
    ) -> None:
        self._repository = repository
        self._renderer = renderer

    def execute(self, request: CreateSkillRequest) -> CreateSkillResponse:
        skill = self._build_skill(request)

        if self._repository.exists(skill):
            return CreateSkillResponse(
                path=Path("."),
                skill=skill,
                already_existed=True,
            )

        path = self._repository.save(skill)
        return CreateSkillResponse(path=path, skill=skill)

    def _build_skill(self, request: CreateSkillRequest) -> Skill:
        from pathlib import PurePosixPath

        identity = SkillIdentity(
            name=request.name,
            category=request.category,
        )
        description = Description(text=request.description)
        starter = (
            StarterCharacter(emoji=request.starter_emoji)
            if request.starter_emoji
            else None
        )
        content = SkillContent(
            principles=request.principles or [],
            instructions=request.instructions,
            constraints=request.constraints or [],
            hints=request.hints,
        )
        references = [
            Reference(path=PurePosixPath(r["path"]), purpose=r["purpose"])
            for r in (request.references or [])
        ]
        scripts = [
            Script(path=PurePosixPath(s["path"]), description=s["description"])
            for s in (request.scripts or [])
        ]
        assets = [
            Asset(path=PurePosixPath(a["path"]), description=a["description"])
            for a in (request.assets or [])
        ]
        examples = [
            Example(path=PurePosixPath(e["path"]), description=e["description"])
            for e in (request.examples or [])
        ]
        depends_on = [
            Dependency(skill_name=d["skill_name"], reason=d.get("reason", ""))
            for d in (request.depends_on or [])
        ]

        return Skill(
            identity=identity,
            description=description,
            starter_character=starter,
            content=content,
            references=references,
            scripts=scripts,
            assets=assets,
            examples=examples,
            depends_on=depends_on,
            version=request.version,
        )
