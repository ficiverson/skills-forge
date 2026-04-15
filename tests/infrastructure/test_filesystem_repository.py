"""Tests for the filesystem repository adapter."""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import Skill
from skill_forge.infrastructure.adapters.filesystem_repository import (
    FilesystemSkillRepository,
)
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer


class TestFilesystemSkillRepository:
    def _build_repo(self, tmp_path: Path) -> FilesystemSkillRepository:
        return FilesystemSkillRepository(
            base_path=tmp_path,
            renderer=MarkdownSkillRenderer(),
            parser=MarkdownSkillParser(),
        )

    def test_save_creates_directory_and_file(self, tmp_path: Path, minimal_skill: Skill):
        repo = self._build_repo(tmp_path)
        path = repo.save(minimal_skill)

        assert path.exists()
        assert (path / "SKILL.md").exists()

    def test_exists_returns_false_for_new_skill(self, tmp_path: Path, minimal_skill: Skill):
        repo = self._build_repo(tmp_path)
        assert not repo.exists(minimal_skill)

    def test_exists_returns_true_after_save(self, tmp_path: Path, minimal_skill: Skill):
        repo = self._build_repo(tmp_path)
        repo.save(minimal_skill)
        assert repo.exists(minimal_skill)

    def test_load_roundtrips_name(self, tmp_path: Path, minimal_skill: Skill):
        repo = self._build_repo(tmp_path)
        path = repo.save(minimal_skill)
        loaded = repo.load(path)

        assert loaded.identity.name == minimal_skill.identity.name

    def test_list_all_finds_saved_skills(
        self, tmp_path: Path, minimal_skill: Skill, skill_with_references: Skill
    ):
        repo = self._build_repo(tmp_path)
        repo.save(minimal_skill)
        repo.save(skill_with_references)

        all_skills = repo.list_all()
        assert len(all_skills) == 2

    def test_save_creates_references_dir_when_needed(
        self, tmp_path: Path, skill_with_references: Skill
    ):
        repo = self._build_repo(tmp_path)
        path = repo.save(skill_with_references)

        assert (path / "references").exists()
