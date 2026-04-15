"""Use case: yank a published skill version from the registry.

A yanked version is hidden from ``update`` resolution and ``install latest``
but remains downloadable by pinning the exact version, preserving
reproducible installs for anyone who already has it.  The pack file is
never deleted — only the index entry is updated.

``YankSkill`` reads the current index from the publisher, applies the yank
mutation via ``RegistryIndex.yank_version()``, and writes the result back
via ``PackPublisher.update_index()``.  The publisher handles git commit/push.
"""

from __future__ import annotations

from dataclasses import dataclass

from skill_forge.domain.ports import PackPublisher


@dataclass(frozen=True)
class YankRequest:
    """Parameters for the ``yank`` use case."""

    skill_name: str
    version: str
    reason: str = ""
    push: bool = False
    commit_message: str = ""  # defaults to "Yank <name>@<version>" when empty


@dataclass(frozen=True)
class YankResponse:
    """Result of the ``yank`` use case."""

    skill_name: str
    version: str
    yank_reason: str
    was_already_yanked: bool
    committed: bool


class YankSkill:
    """Mark a published skill version as yanked in the registry.

    Accepts any ``PackPublisher`` so tests can inject a stub without needing
    a real git repo on disk.
    """

    def __init__(self, publisher: PackPublisher) -> None:
        self._publisher = publisher

    def execute(self, request: YankRequest) -> YankResponse:
        index = self._publisher.read_index()

        # Check if already yanked before applying mutation
        was_already_yanked = False
        indexed_skill = None
        for s in index.skills:
            if s.name == request.skill_name:
                indexed_skill = s
                break

        if indexed_skill is None:
            raise ValueError(f"Skill '{request.skill_name}' not found in registry index")

        indexed_version = indexed_skill.find(request.version)
        if indexed_version is None:
            raise ValueError(
                f"Version '{request.version}' not found for skill '{request.skill_name}'"
            )

        was_already_yanked = indexed_version.yanked

        # Apply yank mutation (raises if not found — but we already validated above)
        updated_index = index.yank_version(
            request.skill_name,
            request.version,
            reason=request.reason,
        )

        message = request.commit_message or (f"Yank {request.skill_name}@{request.version}")
        committed = self._publisher.update_index(updated_index, message, request.push)

        return YankResponse(
            skill_name=request.skill_name,
            version=request.version,
            yank_reason=request.reason,
            was_already_yanked=was_already_yanked,
            committed=committed,
        )


__all__ = ["YankRequest", "YankResponse", "YankSkill"]
