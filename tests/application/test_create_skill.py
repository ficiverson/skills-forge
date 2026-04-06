"""Tests for the create skill use case."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from skill_forge.application.use_cases.create_skill import (
    CreateSkill,
    CreateSkillRequest,
)
from skill_forge.domain.ports import SkillRenderer, SkillRepository


class TestCreateSkillUseCase:
    def test_creates_new_skill(self, tmp_path: Path):
        repo = MagicMock(spec=SkillRepository)
        repo.exists.return_value = False
        repo.save.return_value = tmp_path / "development" / "my-skill"
        renderer = MagicMock(spec=SkillRenderer)

        use_case = CreateSkill(repository=repo, renderer=renderer)
        request = CreateSkillRequest(
            name="my-skill",
            category="development",
            description="Create Python tests with pytest .py files.",
            starter_emoji="🧪",
            principles=["Test first", "Keep it simple"],
        )

        response = use_case.execute(request)

        assert not response.already_existed
        repo.save.assert_called_once()
        assert response.skill.identity.name == "my-skill"
        assert response.skill.starter_character is not None

    def test_reports_existing_skill(self):
        repo = MagicMock(spec=SkillRepository)
        repo.exists.return_value = True
        renderer = MagicMock(spec=SkillRenderer)

        use_case = CreateSkill(repository=repo, renderer=renderer)
        request = CreateSkillRequest(
            name="existing",
            category="dev",
            description="Already exists.",
        )

        response = use_case.execute(request)
        assert response.already_existed
        repo.save.assert_not_called()
