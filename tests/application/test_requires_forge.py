"""Tests for requires-forge version constraint checking."""

from __future__ import annotations

import pytest

from skill_forge.application.use_cases.install_skill import (
    _parse_version,
    _satisfies,
)


class TestParseVersion:
    def test_simple(self) -> None:
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_two_part(self) -> None:
        assert _parse_version("0.4") == (0, 4)

    def test_with_prerelease(self) -> None:
        assert _parse_version("1.0.0-beta.1") == (1, 0, 0)

    def test_with_build_meta(self) -> None:
        assert _parse_version("1.0.0+build.1") == (1, 0, 0)

    def test_empty_returns_zero_tuple(self) -> None:
        assert _parse_version("") == (0,)


class TestSatisfies:
    def test_ge_passes(self) -> None:
        assert _satisfies(">=0.4.0", "0.4.0")
        assert _satisfies(">=0.4.0", "1.0.0")
        assert _satisfies(">=0.4.0", "0.5.0")

    def test_ge_fails(self) -> None:
        assert not _satisfies(">=0.4.0", "0.3.9")
        assert not _satisfies(">=0.4.0", "0.3.0")

    def test_gt_passes(self) -> None:
        assert _satisfies(">0.4.0", "0.4.1")
        assert _satisfies(">0.4.0", "1.0.0")

    def test_gt_fails_equal(self) -> None:
        assert not _satisfies(">0.4.0", "0.4.0")

    def test_eq_passes(self) -> None:
        assert _satisfies("==0.4.0", "0.4.0")

    def test_eq_fails(self) -> None:
        assert not _satisfies("==0.4.0", "0.4.1")

    def test_lt_passes(self) -> None:
        assert _satisfies("<1.0.0", "0.9.0")

    def test_lt_fails(self) -> None:
        assert not _satisfies("<1.0.0", "1.0.0")
        assert not _satisfies("<1.0.0", "1.1.0")

    def test_ne_passes(self) -> None:
        assert _satisfies("!=0.3.0", "0.4.0")

    def test_ne_fails(self) -> None:
        assert not _satisfies("!=0.3.0", "0.3.0")

    def test_multiple_specifiers(self) -> None:
        assert _satisfies(">=0.4.0, <1.0.0", "0.5.0")
        assert not _satisfies(">=0.4.0, <1.0.0", "1.0.0")
        assert not _satisfies(">=0.4.0, <1.0.0", "0.3.0")

    def test_unknown_operator_ignored(self) -> None:
        # Unrecognised spec is skipped, so always passes
        assert _satisfies("~=0.4.0", "0.3.0")


class TestInstallSkillRequiresForge:
    """Integration test: InstallSkill raises when constraint not met."""

    def test_constraint_not_met_raises(self, tmp_path: Path) -> None:
        from unittest.mock import MagicMock

        from skill_forge.application.use_cases.install_skill import (
            InstallSkill,
            InstallSkillRequest,
        )
        from skill_forge.domain.model import (
            Description,
            InstallTarget,
            Skill,
            SkillContent,
            SkillIdentity,
            SkillScope,
        )

        skill = Skill(
            identity=SkillIdentity(name="test-skill", category="test"),
            description=Description(text="desc"),
            content=SkillContent(principles=["p"]),
            requires_forge=">=99.0.0",  # impossibly high requirement
        )
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            '---\nname: test-skill\nrequires-forge: ">=99.0.0"\ndescription: |\n  desc\n---\n',
            encoding="utf-8",
        )

        mock_parser = MagicMock()
        mock_parser.parse.return_value = skill
        mock_installer = MagicMock()

        use_case = InstallSkill(installer=mock_installer, parser=mock_parser)
        request = InstallSkillRequest(
            skill_path=tmp_path,
            scope=SkillScope.GLOBAL,
            target=InstallTarget.CLAUDE,
        )
        with pytest.raises(ValueError, match=r"requires skills-forge >=99\.0\.0"):
            use_case.execute(request)


# Import Path for the integration test
from pathlib import Path  # noqa: E402
