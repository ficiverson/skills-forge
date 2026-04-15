"""Mutation-killing tests for CreateSkill use case.

These tests assert every field of the Skill returned by _build_skill,
which is the primary cause of surviving mutants in create_skill.py.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from unittest.mock import MagicMock

from skill_forge.application.use_cases.create_skill import CreateSkill, CreateSkillRequest
from skill_forge.domain.model import DEFAULT_SKILL_VERSION


def _make_use_case(*, exists: bool = False, save_path: Path = Path("/skills/my-skill")):
    repo = MagicMock()
    repo.exists.return_value = exists
    repo.save.return_value = save_path
    renderer = MagicMock()
    return CreateSkill(repository=repo, renderer=renderer), repo


class TestCreateSkillFullSkillFields:
    """Every field set by _build_skill must be present in the response.skill."""

    def test_identity_name_is_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(name="my-skill", category="dev", description="Build .py files")
        resp = uc.execute(req)
        assert resp.skill.identity.name == "my-skill"

    def test_identity_category_is_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(name="my-skill", category="ops", description="Build .py files")
        resp = uc.execute(req)
        assert resp.skill.identity.category == "ops"

    def test_description_text_is_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Exact description text here",
        )
        resp = uc.execute(req)
        assert resp.skill.description.text == "Exact description text here"

    def test_version_is_set_from_request(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="A skill for .py files",
            version="2.5.0",
        )
        resp = uc.execute(req)
        assert resp.skill.version == "2.5.0"

    def test_version_defaults_to_default_skill_version(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(name="s", category="c", description="Build .py files")
        resp = uc.execute(req)
        assert resp.skill.version == DEFAULT_SKILL_VERSION

    def test_starter_character_is_set_when_provided(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            starter_emoji="🦊",
        )
        resp = uc.execute(req)
        assert resp.skill.starter_character is not None
        assert resp.skill.starter_character.emoji == "🦊"

    def test_starter_character_is_none_when_not_provided(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        resp = uc.execute(req)
        assert resp.skill.starter_character is None

    def test_principles_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            principles=["Be correct", "Be concise"],
        )
        resp = uc.execute(req)
        assert resp.skill.content.principles == ["Be correct", "Be concise"]

    def test_principles_empty_when_not_provided(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        resp = uc.execute(req)
        assert resp.skill.content.principles == []

    def test_instructions_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            instructions="Step one. Step two.",
        )
        resp = uc.execute(req)
        assert resp.skill.content.instructions == "Step one. Step two."

    def test_constraints_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            constraints=["No global state", "Max 200 lines"],
        )
        resp = uc.execute(req)
        assert resp.skill.content.constraints == ["No global state", "Max 200 lines"]

    def test_hints_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            hints="Check types first",
        )
        resp = uc.execute(req)
        assert resp.skill.content.hints == "Check types first"

    def test_references_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            references=[{"path": "references/guide.md", "purpose": "Style Guide"}],
        )
        resp = uc.execute(req)
        assert len(resp.skill.references) == 1
        assert resp.skill.references[0].path == PurePosixPath("references/guide.md")
        assert resp.skill.references[0].purpose == "Style Guide"

    def test_scripts_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            scripts=[{"path": "scripts/run.py", "description": "Runs the skill"}],
        )
        resp = uc.execute(req)
        assert len(resp.skill.scripts) == 1
        assert resp.skill.scripts[0].path == PurePosixPath("scripts/run.py")
        assert resp.skill.scripts[0].description == "Runs the skill"

    def test_assets_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            assets=[{"path": "assets/data.csv", "description": "Training data"}],
        )
        resp = uc.execute(req)
        assert len(resp.skill.assets) == 1
        assert resp.skill.assets[0].path == PurePosixPath("assets/data.csv")
        assert resp.skill.assets[0].description == "Training data"

    def test_examples_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            examples=[{"path": "examples/out.json", "description": "Sample output"}],
        )
        resp = uc.execute(req)
        assert len(resp.skill.examples) == 1
        assert resp.skill.examples[0].path == PurePosixPath("examples/out.json")
        assert resp.skill.examples[0].description == "Sample output"

    def test_depends_on_are_set(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(
            name="s",
            category="c",
            description="Write .py files",
            depends_on=[{"skill_name": "pdf-export", "reason": "PDF generation"}],
        )
        resp = uc.execute(req)
        assert len(resp.skill.depends_on) == 1
        assert resp.skill.depends_on[0].skill_name == "pdf-export"
        assert resp.skill.depends_on[0].reason == "PDF generation"

    def test_empty_collections_when_not_provided(self) -> None:
        uc, _ = _make_use_case()
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        resp = uc.execute(req)
        assert resp.skill.references == []
        assert resp.skill.scripts == []
        assert resp.skill.assets == []
        assert resp.skill.examples == []
        assert resp.skill.depends_on == []


class TestCreateSkillExecuteFlow:
    def test_already_existed_flag_set_when_skill_exists(self) -> None:
        uc, _ = _make_use_case(exists=True)
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        resp = uc.execute(req)
        assert resp.already_existed is True

    def test_already_existed_false_when_skill_is_new(self) -> None:
        uc, _ = _make_use_case(exists=False)
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        resp = uc.execute(req)
        assert resp.already_existed is False

    def test_path_returned_from_repository_save(self) -> None:
        expected_path = Path("/registry/dev/my-skill")
        uc, _ = _make_use_case(save_path=expected_path)
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        resp = uc.execute(req)
        assert resp.path == expected_path

    def test_save_not_called_when_skill_exists(self) -> None:
        uc, repo = _make_use_case(exists=True)
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        uc.execute(req)
        repo.save.assert_not_called()

    def test_path_is_dot_when_already_existed(self) -> None:
        uc, _ = _make_use_case(exists=True)
        req = CreateSkillRequest(name="s", category="c", description="Write .py files")
        resp = uc.execute(req)
        assert resp.path == Path(".")

    def test_repository_init_stored(self) -> None:
        uc, repo = _make_use_case()
        assert uc._repository is repo
