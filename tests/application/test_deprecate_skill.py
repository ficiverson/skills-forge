"""Tests for the DeprecateSkill use case and RegistryIndex.set_skill_metadata()."""

from __future__ import annotations

import pytest

from skill_forge.application.use_cases.deprecate_skill import (
    DeprecateRequest,
    DeprecateSkill,
)
from skill_forge.domain.model import (
    IndexedSkill,
    IndexedVersion,
    RegistryIndex,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_index(
    skill_name: str = "old-skill",
    deprecated: bool = False,
    replaced_by: str = "",
    deprecation_message: str = "",
) -> RegistryIndex:
    return RegistryIndex(
        registry_name="test",
        base_url="https://reg.example.com",
        updated_at="2026-04-11T00:00:00Z",
        skills=(
            IndexedSkill(
                category="dev",
                name=skill_name,
                latest="1.0.0",
                versions=(
                    IndexedVersion(
                        version="1.0.0",
                        path=f"packs/dev/{skill_name}-1.0.0.skillpack",
                        sha256="a" * 64,
                    ),
                ),
                deprecated=deprecated,
                replaced_by=replaced_by,
                deprecation_message=deprecation_message,
            ),
        ),
    )


class _StubPublisher:
    def __init__(self, index: RegistryIndex) -> None:
        self._index = index
        self.written_index: RegistryIndex | None = None

    def publish(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def read_index(self) -> RegistryIndex:
        return self._index

    def update_index(self, index: RegistryIndex, message: str, push: bool) -> bool:
        self.written_index = index
        return True


# ── RegistryIndex.set_skill_metadata() ───────────────────────────────────────


class TestSetSkillMetadata:
    def test_sets_deprecated_flag(self) -> None:
        index = _make_index()
        updated = index.set_skill_metadata("old-skill", deprecated=True)
        skill = updated.find("dev", "old-skill")
        assert skill is not None
        assert skill.deprecated is True

    def test_sets_replaced_by(self) -> None:
        index = _make_index()
        updated = index.set_skill_metadata("old-skill", replaced_by="new-skill")
        skill = updated.find("dev", "old-skill")
        assert skill is not None
        assert skill.replaced_by == "new-skill"

    def test_sets_deprecation_message(self) -> None:
        index = _make_index()
        updated = index.set_skill_metadata(
            "old-skill", deprecation_message="Use new-skill instead"
        )
        skill = updated.find("dev", "old-skill")
        assert skill is not None
        assert skill.deprecation_message == "Use new-skill instead"

    def test_none_fields_preserve_existing_values(self) -> None:
        index = _make_index(replaced_by="other", deprecation_message="legacy")
        updated = index.set_skill_metadata("old-skill", deprecated=True)
        skill = updated.find("dev", "old-skill")
        assert skill is not None
        # deprecated changed, the rest kept
        assert skill.deprecated is True
        assert skill.replaced_by == "other"
        assert skill.deprecation_message == "legacy"

    def test_versions_unchanged(self) -> None:
        index = _make_index()
        updated = index.set_skill_metadata("old-skill", deprecated=True)
        skill = updated.find("dev", "old-skill")
        orig_skill = index.find("dev", "old-skill")
        assert skill is not None and orig_skill is not None
        assert skill.versions == orig_skill.versions

    def test_raises_when_skill_not_found(self) -> None:
        index = _make_index()
        with pytest.raises(ValueError, match="not found in registry"):
            index.set_skill_metadata("nonexistent", deprecated=True)


# ── DeprecateSkill use case ───────────────────────────────────────────────────


class TestDeprecateSkill:
    def test_marks_skill_deprecated(self) -> None:
        index = _make_index()
        publisher = _StubPublisher(index)
        use_case = DeprecateSkill(publisher=publisher)

        response = use_case.execute(
            DeprecateRequest(
                skill_name="old-skill",
                replaced_by="new-skill",
                message="Superseded by new-skill",
            )
        )

        assert response.skill_name == "old-skill"
        assert response.deprecated is True
        assert response.replaced_by == "new-skill"
        assert response.deprecation_message == "Superseded by new-skill"
        assert response.was_already_deprecated is False
        assert response.committed is True

    def test_index_written_with_deprecated_true(self) -> None:
        index = _make_index()
        publisher = _StubPublisher(index)
        DeprecateSkill(publisher=publisher).execute(DeprecateRequest(skill_name="old-skill"))
        written = publisher.written_index
        assert written is not None
        skill = written.find("dev", "old-skill")
        assert skill is not None
        assert skill.deprecated is True

    def test_detects_already_deprecated(self) -> None:
        index = _make_index(deprecated=True)
        publisher = _StubPublisher(index)
        response = DeprecateSkill(publisher=publisher).execute(
            DeprecateRequest(skill_name="old-skill")
        )
        assert response.was_already_deprecated is True

    def test_raises_when_skill_not_found(self) -> None:
        index = _make_index()
        publisher = _StubPublisher(index)
        with pytest.raises(ValueError, match="not found"):
            DeprecateSkill(publisher=publisher).execute(DeprecateRequest(skill_name="nonexistent"))

    def test_default_commit_message(self) -> None:
        index = _make_index()
        publisher = _StubPublisher(index)
        messages: list[str] = []
        _orig = publisher.update_index

        def _spy(idx, msg, push):  # type: ignore[no-untyped-def]
            messages.append(msg)
            return _orig(idx, msg, push)

        publisher.update_index = _spy  # type: ignore[method-assign]
        DeprecateSkill(publisher=publisher).execute(DeprecateRequest(skill_name="old-skill"))
        assert messages == ["Deprecate old-skill"]

    def test_custom_commit_message(self) -> None:
        index = _make_index()
        publisher = _StubPublisher(index)
        messages: list[str] = []
        _orig = publisher.update_index

        def _spy(idx, msg, push):  # type: ignore[no-untyped-def]
            messages.append(msg)
            return _orig(idx, msg, push)

        publisher.update_index = _spy  # type: ignore[method-assign]
        DeprecateSkill(publisher=publisher).execute(
            DeprecateRequest(
                skill_name="old-skill",
                commit_message="chore: deprecate old-skill",
            )
        )
        assert messages == ["chore: deprecate old-skill"]

    def test_empty_replaced_by_and_message(self) -> None:
        index = _make_index()
        publisher = _StubPublisher(index)
        response = DeprecateSkill(publisher=publisher).execute(
            DeprecateRequest(skill_name="old-skill")
        )
        assert response.replaced_by == ""
        assert response.deprecation_message == ""
