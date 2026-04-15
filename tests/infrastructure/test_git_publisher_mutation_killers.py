"""Mutation-killing tests for GitRegistryPublisher."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from skill_forge.domain.model import (
    Owner,
    PublishMetadata,
    SkillPackManifest,
    SkillRef,
)
from skill_forge.infrastructure.adapters.git_registry_publisher import (
    GitRegistryPublisher,
)


@pytest.fixture
def registry_root(tmp_path: Path) -> Path:
    root = tmp_path / "registry"
    root.mkdir()
    return root

@pytest.fixture
def publisher(registry_root: Path) -> GitRegistryPublisher:
    return GitRegistryPublisher(
        registry_root=registry_root,
        registry_name="test-registry",
        base_url="https://example.com",
    )

@pytest.fixture
def manifest() -> SkillPackManifest:
    return SkillPackManifest(
        name="test-pack",
        version="1.0.0",
        author="test-author",
        created_at="2026-04-15T00:00:00Z",
        skills=(
            SkillRef(name="my-skill", category="dev", version="1.0.0"),
        )
    )

class TestGitRegistryPublisherInitMutationKillers:
    def test_init_missing_root_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "not-there"
        with pytest.raises(FileNotFoundError) as exc:
            GitRegistryPublisher(missing, "name", "url")
        assert f"Registry directory does not exist: '{missing}'" in str(exc.value)

    def test_init_not_a_directory_error(self, tmp_path: Path) -> None:
        fake_file = tmp_path / "file.txt"
        fake_file.write_text("not a dir")
        with pytest.raises(NotADirectoryError) as exc:
            GitRegistryPublisher(fake_file, "name", "url")
        assert f"Registry path is not a directory: '{fake_file}'" in str(exc.value)

    def test_init_resolves_path(self, registry_root: Path) -> None:
        # Create a relative-ish path using ..
        rel_path = registry_root.parent / "registry" / ".." / "registry"
        publisher = GitRegistryPublisher(rel_path, "name", "url")
        # _root should be resolved
        assert publisher._root == registry_root.resolve()

    def test_init_custom_git_command_usage(
        self, registry_root: Path, tmp_path: Path, manifest: SkillPackManifest
    ) -> None:
        publisher = GitRegistryPublisher(registry_root, "name", "url", git_command="custom-git")
        assert publisher._git == "custom-git"

        # Verify it's used in subprocess.run
        pack_path = tmp_path / "test.skillpack"
        pack_path.write_bytes(b"")
        (registry_root / ".git").mkdir()

        with patch("subprocess.run") as mock_run, patch("shutil.copyfile"), \
             patch(
                 "skill_forge.infrastructure.adapters.git_registry_publisher._sha256",
                 return_value="a" * 64
             ):
            mock_run.return_value = MagicMock(stdout="")
            publisher._git_add("file")
            # First arg should be custom-git
            assert mock_run.call_args[0][0][0] == "custom-git"

class TestGitRegistryPublisherMutationKillers:
    def test_publish_exact_git_commands(
        self,
        publisher: GitRegistryPublisher,
        registry_root: Path,
        manifest: SkillPackManifest,
        tmp_path: Path
    ) -> None:
        # Create a dummy pack
        pack_path = tmp_path / "test.skillpack"
        pack_path.write_bytes(b"content")

        # Mock .git directory to trigger git commands
        (registry_root / ".git").mkdir()

        with patch("subprocess.run") as mock_run, \
             patch("shutil.copyfile") as mock_copy, \
             patch(
                 "skill_forge.infrastructure.adapters.git_registry_publisher._sha256",
                 return_value="a" * 64
             ), \
             patch(
                 "skill_forge.infrastructure.adapters.git_registry_publisher._now_iso",
                 return_value="2026-04-15T12:00:00Z"
             ):

            # Create a real file at expected_dest so stat() doesn't fail
            expected_dest = registry_root / "packs" / "dev" / "my-skill-1.0.0.skillpack"
            expected_dest.parent.mkdir(parents=True, exist_ok=True)
            expected_dest.write_bytes(b"dummy")

            # Mock has_staged_changes to return True
            mock_run.return_value = MagicMock(stdout="index.json\n")

            publisher.publish(
                pack_path=pack_path,
                manifest=manifest,
                message="Custom commit message",
                push=True
            )

            # Verify shutil.copyfile arguments
            # path: packs/dev/my-skill-1.0.0.skillpack
            expected_dest = registry_root / "packs" / "dev" / "my-skill-1.0.0.skillpack"
            mock_copy.assert_called_once_with(pack_path, expected_dest)

            # Verify git commands
            calls = [c.args[0] for c in mock_run.call_args_list]

            # Check git add
            git_add_args = [
                "git", "-C", str(registry_root), "add",
                "packs/dev/my-skill-1.0.0.skillpack", "index.json"
            ]
            assert git_add_args in calls

            # Check git diff (has_staged_changes)
            assert ["git", "-C", str(registry_root), "diff", "--cached", "--name-only"] in calls

            # Check git commit
            git_commit_args = [
                "git", "-C", str(registry_root), "commit", "-m", "Custom commit message"
            ]
            assert git_commit_args in calls

            # Check git push
            assert ["git", "-C", str(registry_root), "push"] in calls

    def test_publish_default_commit_message(
        self,
        publisher: GitRegistryPublisher,
        registry_root: Path,
        manifest: SkillPackManifest,
        tmp_path: Path
    ) -> None:
        pack_path = tmp_path / "test.skillpack"
        pack_path.write_bytes(b"content")
        (registry_root / ".git").mkdir()

        with patch("subprocess.run") as mock_run, \
             patch("shutil.copyfile"), \
             patch(
                 "skill_forge.infrastructure.adapters.git_registry_publisher._sha256",
                 return_value="a" * 64
             ), \
             patch(
                 "skill_forge.infrastructure.adapters.git_registry_publisher._now_iso",
                 return_value="2026-04-15T12:00:00Z"
             ):

            # Create a real file at expected_dest so stat() doesn't fail
            expected_dest = registry_root / "packs" / "dev" / "my-skill-1.0.0.skillpack"
            expected_dest.parent.mkdir(parents=True, exist_ok=True)
            expected_dest.write_bytes(b"dummy")

            mock_run.return_value = MagicMock(stdout="index.json\n")

            publisher.publish(
                pack_path=pack_path,
                manifest=manifest,
                message="", # Trigger default
                push=False
            )

            calls = [c.args[0] for c in mock_run.call_args_list]
            # Verify default message: "Publish my-skill 1.0.0"
            git_commit_default = [
                "git", "-C", str(registry_root), "commit", "-m", "Publish my-skill 1.0.0"
            ]
            assert git_commit_default in calls

    def test_sha256_calculation_impact(
        self,
        publisher: GitRegistryPublisher,
        registry_root: Path,
        manifest: SkillPackManifest,
        tmp_path: Path
    ) -> None:
        # Create a pack with known content (empty)
        pack_path = tmp_path / "test.skillpack"
        pack_path.write_bytes(b"")
        # SHA256 of empty string: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

        # We must NOT patch _sha256 here, but we need the destination file to exist
        # because the real _sha256(dest) is called.
        expected_dest = registry_root / "packs" / "dev" / "my-skill-1.0.0.skillpack"
        expected_dest.parent.mkdir(parents=True, exist_ok=True)
        expected_dest.write_bytes(b"") # Matches pack_path

        with patch("subprocess.run"), patch("shutil.copyfile"):
            result = publisher.publish(pack_path, manifest, "msg", False)
            expected_sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            assert result.sha256 == expected_sha

    def test_index_upsert_logic(
        self,
        publisher: GitRegistryPublisher,
        registry_root: Path,
        manifest: SkillPackManifest,
        tmp_path: Path
    ) -> None:
        pack_path = tmp_path / "test.skillpack"
        pack_path.write_bytes(b"")

        metadata = PublishMetadata(
            description="New description",
            tags=("new-tag",),
            platforms=("claude",),
            owner=Owner(name="me", email="me@example.com"),
            deprecated=True
        )

        with patch("subprocess.run"), \
             patch("shutil.copyfile"), \
             patch(
                 "skill_forge.infrastructure.adapters.git_registry_publisher._sha256",
                 return_value="a" * 64
             ), \
             patch(
                 "skill_forge.infrastructure.adapters.git_registry_publisher._now_iso",
                 return_value="2026-04-15T12:00:00Z"
             ):

            # Create a real file at expected_dest so stat() doesn't fail
            expected_dest = registry_root / "packs" / "dev" / "my-skill-1.0.0.skillpack"
            expected_dest.parent.mkdir(parents=True, exist_ok=True)
            expected_dest.write_bytes(b"dummy")

            publisher.publish(pack_path, manifest, "msg", False, metadata=metadata)

            # Load the index.json from disk and verify fields
            index_path = registry_root / "index.json"
            data = json.loads(index_path.read_text())

            skill_entry = data["skills"][0]
            assert skill_entry["name"] == "my-skill"
            assert skill_entry["description"] == "New description"
            assert skill_entry["tags"] == ["new-tag"]
            assert skill_entry["platforms"] == ["claude"]
            assert skill_entry["owner"]["name"] == "me"
            assert skill_entry["owner"]["email"] == "me@example.com"
            assert skill_entry["deprecated"] is True

    def test_publish_unsupported_multi_skill_error_message(
        self, publisher: GitRegistryPublisher, tmp_path: Path
    ) -> None:
        pack_path = tmp_path / "test.skillpack"
        pack_path.write_bytes(b"")

        multi_manifest = SkillPackManifest(
            name="multi",
            version="1.0.0",
            author="test-author",
            created_at="2026-04-15T00:00:00Z",
            skills=(
                SkillRef(name="s1", category="c", version="1.0.0"),
                SkillRef(name="s2", category="c", version="1.0.0"),
            )
        )

        with pytest.raises(ValueError) as exc:
            publisher.publish(pack_path, multi_manifest, "msg", False)

        assert "currently supports single-skill packs only" in str(exc.value)
        assert "(got 2 skills)" in str(exc.value)
