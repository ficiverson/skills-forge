"""Tests for new validators: reference links, examples, assets, dependencies."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from skill_forge.domain.model import (
    Asset,
    Dependency,
    Description,
    Example,
    Reference,
    Script,
    Severity,
    Skill,
    SkillIdentity,
)
from skill_forge.domain.validators import (
    validate_asset_files,
    validate_dependency_exists,
    validate_example_files,
    validate_has_examples,
    validate_reference_links,
    validate_script_files,
)


@pytest.fixture
def skill_with_refs() -> Skill:
    return Skill(
        identity=SkillIdentity(name="test-skill", category="testing"),
        description=Description(text="A test skill for validating references"),
        references=[
            Reference(path=PurePosixPath("references/guide.md"), purpose="Guide"),
            Reference(path=PurePosixPath("references/missing.md"), purpose="Missing"),
        ],
    )


@pytest.fixture
def skill_with_examples() -> Skill:
    return Skill(
        identity=SkillIdentity(name="test-skill", category="testing"),
        description=Description(text="A test skill with examples"),
        scripts=[Script(path=PurePosixPath("scripts/run.py"), description="Runner")],
        examples=[
            Example(path=PurePosixPath("examples/output.json"), description="Sample"),
            Example(path=PurePosixPath("examples/missing.json"), description="Missing"),
        ],
    )


@pytest.fixture
def skill_with_assets() -> Skill:
    return Skill(
        identity=SkillIdentity(name="test-skill", category="testing"),
        description=Description(text="A test skill with assets"),
        assets=[
            Asset(path=PurePosixPath("assets/data.csv"), description="Data"),
        ],
    )


@pytest.fixture
def skill_with_deps() -> Skill:
    return Skill(
        identity=SkillIdentity(name="test-skill", category="testing"),
        description=Description(text="A test skill with dependencies"),
        depends_on=[
            Dependency(skill_name="pdf", reason="PDF generation"),
        ],
    )


class TestReferenceLinksValidator:
    def test_no_skill_dir_skips_validation(self, skill_with_refs: Skill):
        issues = validate_reference_links(skill_with_refs, skill_dir=None)
        assert len(issues) == 0

    def test_valid_reference_passes(self, skill_with_refs: Skill, tmp_path: Path):
        # Create only the first reference file
        (tmp_path / "references").mkdir()
        (tmp_path / "references" / "guide.md").write_text("# Guide")

        issues = validate_reference_links(skill_with_refs, skill_dir=tmp_path)
        broken = [i for i in issues if i.rule == "broken-reference-link"]
        # Only missing.md should fail
        assert len(broken) == 1
        assert "missing.md" in broken[0].message

    def test_all_references_exist_passes(self, skill_with_refs: Skill, tmp_path: Path):
        (tmp_path / "references").mkdir()
        (tmp_path / "references" / "guide.md").write_text("# Guide")
        (tmp_path / "references" / "missing.md").write_text("# Found")

        issues = validate_reference_links(skill_with_refs, skill_dir=tmp_path)
        assert len(issues) == 0

    def test_broken_reference_is_error(self, skill_with_refs: Skill, tmp_path: Path):
        issues = validate_reference_links(skill_with_refs, skill_dir=tmp_path)
        assert all(i.severity == Severity.ERROR for i in issues)


class TestExampleFilesValidator:
    def test_no_skill_dir_skips(self, skill_with_examples: Skill):
        issues = validate_example_files(skill_with_examples, skill_dir=None)
        assert len(issues) == 0

    def test_missing_example_is_error(self, skill_with_examples: Skill, tmp_path: Path):
        (tmp_path / "examples").mkdir()
        (tmp_path / "examples" / "output.json").write_text("{}")

        issues = validate_example_files(skill_with_examples, skill_dir=tmp_path)
        assert len(issues) == 1
        assert "missing.json" in issues[0].message

    def test_all_examples_exist_passes(self, skill_with_examples: Skill, tmp_path: Path):
        (tmp_path / "examples").mkdir()
        (tmp_path / "examples" / "output.json").write_text("{}")
        (tmp_path / "examples" / "missing.json").write_text("{}")

        issues = validate_example_files(skill_with_examples, skill_dir=tmp_path)
        assert len(issues) == 0


class TestAssetFilesValidator:
    def test_missing_asset_is_error(self, skill_with_assets: Skill, tmp_path: Path):
        issues = validate_asset_files(skill_with_assets, skill_dir=tmp_path)
        assert len(issues) == 1
        assert issues[0].rule == "broken-asset-link"

    def test_existing_asset_passes(self, skill_with_assets: Skill, tmp_path: Path):
        (tmp_path / "assets").mkdir()
        (tmp_path / "assets" / "data.csv").write_text("a,b,c")

        issues = validate_asset_files(skill_with_assets, skill_dir=tmp_path)
        assert len(issues) == 0


class TestHasExamplesValidator:
    def test_skill_with_scripts_but_no_examples_gets_info(
        self, skill_with_examples: Skill,
    ):
        # Remove examples to test the warning
        skill = Skill(
            identity=skill_with_examples.identity,
            description=skill_with_examples.description,
            scripts=skill_with_examples.scripts,
            examples=[],  # No examples
        )
        issues = validate_has_examples(skill)
        assert len(issues) == 1
        assert issues[0].rule == "missing-examples"

    def test_skill_with_scripts_and_examples_passes(
        self, skill_with_examples: Skill,
    ):
        issues = validate_has_examples(skill_with_examples)
        assert len(issues) == 0

    def test_skill_without_scripts_skips(self):
        skill = Skill(
            identity=SkillIdentity(name="simple", category="test"),
            description=Description(text="Simple skill"),
        )
        issues = validate_has_examples(skill)
        assert len(issues) == 0


class TestDependencyValidator:
    def test_valid_dependency_passes(self):
        skill = Skill(
            identity=SkillIdentity(name="test", category="test"),
            description=Description(text="Test skill"),
            depends_on=[Dependency(skill_name="pdf", reason="PDF gen")],
        )
        issues = validate_dependency_exists(skill)
        assert len(issues) == 0

    def test_empty_dependency_name_raises(self):
        """__post_init__ now rejects empty dependency names at construction."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Dependency(skill_name="", reason="empty name")

    def test_spaces_in_dependency_name_raises(self):
        """__post_init__ now rejects spaces in dependency names at construction."""
        with pytest.raises(ValueError, match="kebab-case"):
            Dependency(skill_name="bad name", reason="")


class TestScriptFilesValidator:
    def test_missing_script_is_error(self, tmp_path: Path):
        skill = Skill(
            identity=SkillIdentity(name="test", category="test"),
            description=Description(text="Test skill"),
            scripts=[Script(path=PurePosixPath("scripts/run.py"), description="Run")],
        )
        issues = validate_script_files(skill, skill_dir=tmp_path)
        assert len(issues) == 1
        assert issues[0].rule == "broken-script-link"

    def test_existing_script_passes(self, tmp_path: Path):
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "run.py").write_text("print('hello')")

        skill = Skill(
            identity=SkillIdentity(name="test", category="test"),
            description=Description(text="Test skill"),
            scripts=[Script(path=PurePosixPath("scripts/run.py"), description="Run")],
        )
        issues = validate_script_files(skill, skill_dir=tmp_path)
        assert len(issues) == 0
