"""Tests for the GitRegistryPublisher adapter.

These tests instantiate a real local git repo via subprocess so we
exercise the actual ``git add``/``commit`` path. They skip if ``git``
isn't on PATH (which is rare but possible in minimal sandboxes).
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from skill_forge.domain.model import SkillPackManifest, SkillRef
from skill_forge.infrastructure.adapters.git_registry_publisher import (
    GitRegistryPublisher,
)
from skill_forge.infrastructure.adapters.registry_index_codec import (
    RegistryIndexCodec,
)


def _make_pack(path: Path, name: str, version: str) -> Path:
    """Write a minimal valid .skillpack zip at ``path``."""
    pack_path = path / f"{name}-{version}.skillpack"
    with zipfile.ZipFile(pack_path, "w") as zf:
        zf.writestr("manifest.json", "{}")
        zf.writestr(f"skills/dev/{name}/SKILL.md", "---\nname: x\n---\nbody")
    return pack_path


def _manifest(name: str, version: str) -> SkillPackManifest:
    return SkillPackManifest(
        name=name,
        version=version,
        author="fer@example.com",
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        skills=(SkillRef(category="dev", name=name, version=version),),
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "PATH": __import__("os").environ.get("PATH", ""),
            "HOME": str(cwd),
        },
    )


@pytest.fixture()
def git_registry(tmp_path: Path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("git not available")
    root = tmp_path / "registry"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "test")
    return root


class TestGitRegistryPublisher:
    def test_publish_copies_pack_and_writes_index(
        self, tmp_path: Path, git_registry: Path
    ) -> None:
        pack = _make_pack(tmp_path, "python-tdd", "0.1.0")
        publisher = GitRegistryPublisher(
            registry_root=git_registry,
            registry_name="acme",
            base_url="https://raw.githubusercontent.com/acme/skills/main",
        )

        result = publisher.publish(
            pack_path=pack,
            manifest=_manifest("python-tdd", "0.1.0"),
            message="ship 0.1.0",
            push=False,
        )

        published = git_registry / "packs" / "dev" / "python-tdd-0.1.0.skillpack"
        assert published.exists()
        assert (git_registry / "index.json").exists()
        assert result.committed is True
        assert result.pushed is False
        assert result.repo_relative_path == "packs/dev/python-tdd-0.1.0.skillpack"
        assert result.raw_url.endswith(result.repo_relative_path)
        assert len(result.sha256) == 64

    def test_publish_updates_index_on_second_publish(
        self, tmp_path: Path, git_registry: Path
    ) -> None:
        publisher = GitRegistryPublisher(
            registry_root=git_registry,
            registry_name="acme",
            base_url="https://raw.githubusercontent.com/acme/skills/main",
        )

        pack_a = _make_pack(tmp_path, "python-tdd", "0.1.0")
        publisher.publish(pack_a, _manifest("python-tdd", "0.1.0"), "v1", push=False)

        pack_b = _make_pack(tmp_path, "python-tdd", "0.2.0")
        publisher.publish(pack_b, _manifest("python-tdd", "0.2.0"), "v2", push=False)

        codec = RegistryIndexCodec()
        index = codec.decode((git_registry / "index.json").read_text("utf-8"))
        skill = index.find("dev", "python-tdd")
        assert skill is not None
        assert skill.latest == "0.2.0"
        assert {v.version for v in skill.versions} == {"0.1.0", "0.2.0"}

    def test_publish_rejects_multi_skill_pack(
        self, tmp_path: Path, git_registry: Path
    ) -> None:
        pack = _make_pack(tmp_path, "bundle", "0.1.0")
        manifest = SkillPackManifest(
            name="bundle",
            version="0.1.0",
            author="",
            created_at="2026-04-06T00:00:00+00:00",
            skills=(
                SkillRef(category="dev", name="a", version="0.1.0"),
                SkillRef(category="dev", name="b", version="0.1.0"),
            ),
        )
        publisher = GitRegistryPublisher(
            registry_root=git_registry,
            registry_name="acme",
            base_url="https://raw.githubusercontent.com/acme/skills/main",
        )
        with pytest.raises(ValueError, match="single-skill"):
            publisher.publish(pack, manifest, "x", push=False)

    def test_missing_registry_root_errors(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            GitRegistryPublisher(
                registry_root=tmp_path / "nope",
                registry_name="acme",
                base_url="https://example.com",
            )
