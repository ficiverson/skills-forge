"""Tests for the YankSkill use case and RegistryIndex.yank_version()."""

from __future__ import annotations

from skill_forge.application.use_cases.yank_skill import (
    YankRequest,
    YankSkill,
)
from skill_forge.domain.model import (
    IndexedSkill,
    IndexedVersion,
    RegistryIndex,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_index(
    skill_name: str = "python-tdd",
    versions: tuple[str, ...] = ("1.0.0", "1.1.0"),
    yanked: dict[str, bool] | None = None,
) -> RegistryIndex:
    yanked = yanked or {}
    indexed_versions = tuple(
        IndexedVersion(
            version=v,
            path=f"packs/dev/{skill_name}-{v}.skillpack",
            sha256="a" * 64,
            yanked=yanked.get(v, False),
        )
        for v in versions
    )
    return RegistryIndex(
        registry_name="test",
        base_url="https://reg.example.com",
        updated_at="2026-04-11T00:00:00Z",
        skills=(
            IndexedSkill(
                category="dev",
                name=skill_name,
                latest=versions[-1],
                versions=indexed_versions,
            ),
        ),
    )


class _StubPublisher:
    """Minimal PackPublisher stub for yank tests."""

    def __init__(self, index: RegistryIndex) -> None:
        self._index = index
        self.written_index: RegistryIndex | None = None
        self.committed = True  # pretend commits always succeed

    def publish(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def read_index(self) -> RegistryIndex:
        return self._index

    def update_index(self, index: RegistryIndex, message: str, push: bool) -> bool:
        self.written_index = index
        return self.committed


# ── RegistryIndex.yank_version() ──────────────────────────────────────────────


class TestYankVersion:
    def test_marks_version_yanked(self) -> None:
        index = _make_index(versions=("1.0.0", "1.1.0"))
        updated = index.yank_version("python-tdd", "1.0.0", reason="bug")
        skill = updated.find("dev", "python-tdd")
        assert skill is not None
        v = skill.find("1.0.0")
        assert v is not None
        assert v.yanked is True
        assert v.yank_reason == "bug"

    def test_other_versions_unchanged(self) -> None:
        index = _make_index(versions=("1.0.0", "1.1.0"))
        updated = index.yank_version("python-tdd", "1.0.0")
        skill = updated.find("dev", "python-tdd")
        assert skill is not None
        v11 = skill.find("1.1.0")
        assert v11 is not None
        assert v11.yanked is False

    def test_latest_recalculated_to_skip_yanked(self) -> None:
        index = _make_index(versions=("1.0.0", "1.1.0"))
        updated = index.yank_version("python-tdd", "1.1.0")
        skill = updated.find("dev", "python-tdd")
        assert skill is not None
        assert skill.latest == "1.0.0"  # falls back to non-yanked

    def test_all_yanked_latest_falls_back_to_last(self) -> None:
        index = _make_index(versions=("1.0.0",))
        updated = index.yank_version("python-tdd", "1.0.0")
        skill = updated.find("dev", "python-tdd")
        assert skill is not None
        assert skill.latest == "1.0.0"  # no non-yanked, so keeps last

    def test_raises_when_skill_not_found(self) -> None:
        import pytest

        index = _make_index()
        with pytest.raises(ValueError, match="not found in registry"):
            index.yank_version("nonexistent", "1.0.0")

    def test_raises_when_version_not_found(self) -> None:
        import pytest

        index = _make_index(versions=("1.0.0",))
        with pytest.raises(ValueError, match="not found for skill"):
            index.yank_version("python-tdd", "9.9.9")

    def test_yank_reason_defaults_empty(self) -> None:
        index = _make_index(versions=("1.0.0",))
        updated = index.yank_version("python-tdd", "1.0.0")
        v = updated.find("dev", "python-tdd").find("1.0.0")  # type: ignore[union-attr]
        assert v.yank_reason == ""


# ── YankSkill use case ────────────────────────────────────────────────────────


class TestYankSkill:
    def test_yanks_version_in_index(self) -> None:
        index = _make_index(versions=("1.0.0", "1.1.0"))
        publisher = _StubPublisher(index)
        use_case = YankSkill(publisher=publisher)

        response = use_case.execute(
            YankRequest(skill_name="python-tdd", version="1.0.0", reason="security")
        )

        assert response.skill_name == "python-tdd"
        assert response.version == "1.0.0"
        assert response.yank_reason == "security"
        assert response.was_already_yanked is False
        assert response.committed is True

        written = publisher.written_index
        assert written is not None
        skill = written.find("dev", "python-tdd")
        assert skill is not None
        v = skill.find("1.0.0")
        assert v is not None
        assert v.yanked is True

    def test_detects_already_yanked(self) -> None:
        index = _make_index(versions=("1.0.0",), yanked={"1.0.0": True})
        publisher = _StubPublisher(index)
        use_case = YankSkill(publisher=publisher)

        response = use_case.execute(YankRequest(skill_name="python-tdd", version="1.0.0"))

        assert response.was_already_yanked is True

    def test_raises_when_skill_not_found(self) -> None:
        import pytest

        index = _make_index()
        publisher = _StubPublisher(index)
        use_case = YankSkill(publisher=publisher)

        with pytest.raises(ValueError, match="not found"):
            use_case.execute(YankRequest(skill_name="nonexistent", version="1.0.0"))

    def test_raises_when_version_not_found(self) -> None:
        import pytest

        index = _make_index(versions=("1.0.0",))
        publisher = _StubPublisher(index)
        use_case = YankSkill(publisher=publisher)

        with pytest.raises(ValueError, match="not found for skill"):
            use_case.execute(YankRequest(skill_name="python-tdd", version="9.9.9"))

    def test_default_commit_message(self) -> None:
        """update_index is called with auto-generated message."""
        index = _make_index(versions=("1.0.0",))
        publisher = _StubPublisher(index)
        messages: list[str] = []
        _orig = publisher.update_index

        def _spy(idx, msg, push):  # type: ignore[no-untyped-def]
            messages.append(msg)
            return _orig(idx, msg, push)

        publisher.update_index = _spy  # type: ignore[method-assign]
        YankSkill(publisher=publisher).execute(
            YankRequest(skill_name="python-tdd", version="1.0.0")
        )
        assert messages == ["Yank python-tdd@1.0.0"]

    def test_custom_commit_message(self) -> None:
        index = _make_index(versions=("1.0.0",))
        publisher = _StubPublisher(index)
        messages: list[str] = []
        _orig = publisher.update_index

        def _spy(idx, msg, push):  # type: ignore[no-untyped-def]
            messages.append(msg)
            return _orig(idx, msg, push)

        publisher.update_index = _spy  # type: ignore[method-assign]
        YankSkill(publisher=publisher).execute(
            YankRequest(
                skill_name="python-tdd",
                version="1.0.0",
                commit_message="Custom yank message",
            )
        )
        assert messages == ["Custom yank message"]
