"""Use case: mark a skill as deprecated in the registry.

A deprecated skill is superseded by a newer skill or version.  It still
appears in listings (with a notice) so existing users can see the migration
path, but ``update`` and ``install latest`` will surface the warning.

``DeprecateSkill`` reads the current index, applies the deprecation mutation
via ``RegistryIndex.set_skill_metadata()``, and writes the result back via
``PackPublisher.update_index()``.
"""

from __future__ import annotations

from dataclasses import dataclass

from skill_forge.domain.ports import PackPublisher


@dataclass(frozen=True)
class DeprecateRequest:
    """Parameters for the ``deprecate`` use case."""

    skill_name: str
    replaced_by: str = ""           # name of the skill that supersedes this one
    message: str = ""               # human-readable migration note
    push: bool = False
    commit_message: str = ""        # defaults to "Deprecate <name>" when empty


@dataclass(frozen=True)
class DeprecateResponse:
    """Result of the ``deprecate`` use case."""

    skill_name: str
    deprecated: bool
    replaced_by: str
    deprecation_message: str
    was_already_deprecated: bool
    committed: bool


class DeprecateSkill:
    """Mark a skill as deprecated in the registry.

    Accepts any ``PackPublisher`` so tests can inject a stub without needing
    a real git repo on disk.
    """

    def __init__(self, publisher: PackPublisher) -> None:
        self._publisher = publisher

    def execute(self, request: DeprecateRequest) -> DeprecateResponse:
        index = self._publisher.read_index()

        # Validate skill exists
        indexed_skill = None
        for s in index.skills:
            if s.name == request.skill_name:
                indexed_skill = s
                break

        if indexed_skill is None:
            raise ValueError(
                f"Skill '{request.skill_name}' not found in registry index"
            )

        was_already_deprecated = indexed_skill.deprecated

        updated_index = index.set_skill_metadata(
            request.skill_name,
            deprecated=True,
            replaced_by=request.replaced_by or None,
            deprecation_message=request.message or None,
        )

        message = request.commit_message or f"Deprecate {request.skill_name}"
        committed = self._publisher.update_index(updated_index, message, request.push)

        # Read back the final state for the response
        final_skill = None
        for s in updated_index.skills:
            if s.name == request.skill_name:
                final_skill = s
                break

        replaced_by = final_skill.replaced_by if final_skill else request.replaced_by
        dep_message = (
            final_skill.deprecation_message if final_skill else request.message
        )

        return DeprecateResponse(
            skill_name=request.skill_name,
            deprecated=True,
            replaced_by=replaced_by,
            deprecation_message=dep_message,
            was_already_deprecated=was_already_deprecated,
            committed=committed,
        )


__all__ = ["DeprecateRequest", "DeprecateResponse", "DeprecateSkill"]
