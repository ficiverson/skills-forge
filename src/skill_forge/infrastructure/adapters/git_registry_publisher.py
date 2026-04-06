"""Publish skill packs to a git-backed registry (e.g. a GitHub repo).

The repo layout this adapter writes/reads:

    <registry-root>/
    ├── index.json
    └── packs/
        └── <category>/
            └── <name>-<version>.skillpack

Once pushed to GitHub, every pack is reachable via the public raw CDN at
``https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<repo-path>``
without any GitHub Actions, releases, or registry server.

The publisher shells out to the local ``git`` CLI rather than depending
on PyGithub or GitPython — it works against any remote (GitHub, GitLab,
Gitea, plain SSH), and you don't pay for an extra dependency just to
move a file and make a commit.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from skill_forge.domain.model import (
    IndexedVersion,
    PublishResult,
    RegistryIndex,
    SkillPackManifest,
)
from skill_forge.domain.ports import PackPublisher
from skill_forge.infrastructure.adapters.registry_index_codec import (
    RegistryIndexCodec,
)


class GitRegistryPublisher(PackPublisher):
    """Publish packs into a local clone of a git-hosted registry repo."""

    def __init__(
        self,
        registry_root: Path,
        registry_name: str,
        base_url: str,
        codec: RegistryIndexCodec | None = None,
        git_command: str = "git",
    ) -> None:
        self._root = registry_root.resolve()
        self._registry_name = registry_name
        self._base_url = base_url.rstrip("/")
        self._codec = codec or RegistryIndexCodec()
        self._git = git_command

        if not self._root.exists():
            raise FileNotFoundError(f"Registry directory does not exist: {self._root}")
        if not self._root.is_dir():
            raise NotADirectoryError(f"Registry path is not a directory: {self._root}")

    # ------------------------------------------------------------------ public

    def publish(
        self,
        pack_path: Path,
        manifest: SkillPackManifest,
        message: str,
        push: bool,
    ) -> PublishResult:
        if not pack_path.exists():
            raise FileNotFoundError(f"Pack does not exist: {pack_path}")
        if pack_path.suffix != ".skillpack":
            raise ValueError(f"Not a .skillpack file: {pack_path}")
        if len(manifest.skills) != 1:
            # The first cut only supports single-skill packs in the registry.
            # Multi-skill bundles can still be shared as raw files; they just
            # don't get an index entry yet.
            raise ValueError(
                "GitRegistryPublisher currently supports single-skill packs only "
                f"(got {len(manifest.skills)} skills)"
            )

        ref = manifest.skills[0]
        rel_dir = Path("packs") / ref.category
        rel_path = rel_dir / f"{ref.name}-{ref.version}.skillpack"
        dest = self._root / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pack_path, dest)

        sha = _sha256(dest)
        index = self._read_or_seed_index().upsert(
            ref.category,
            ref.name,
            IndexedVersion(
                version=ref.version,
                path=rel_path.as_posix(),
                sha256=sha,
            ),
        )
        index = self._stamped_now(index)
        index_path = self._root / "index.json"
        index_path.write_text(self._codec.encode(index), encoding="utf-8")

        committed = False
        pushed = False
        if self._is_git_repo():
            self._git_add(rel_path.as_posix(), "index.json")
            if self._has_staged_changes():
                self._git_commit(message or f"Publish {ref.name} {ref.version}")
                committed = True
                if push:
                    self._git_push()
                    pushed = True

        raw_url = f"{self._base_url}/{rel_path.as_posix()}"
        return PublishResult(
            pack_name=manifest.name,
            version=ref.version,
            raw_url=raw_url,
            repo_relative_path=rel_path.as_posix(),
            sha256=sha,
            committed=committed,
            pushed=pushed,
        )

    def read_index(self) -> RegistryIndex:
        return self._read_or_seed_index()

    # ----------------------------------------------------------------- helpers

    def _read_or_seed_index(self) -> RegistryIndex:
        index_path = self._root / "index.json"
        if index_path.exists():
            return self._codec.decode(index_path.read_text(encoding="utf-8"))
        return RegistryIndex(
            registry_name=self._registry_name,
            base_url=self._base_url,
            updated_at=_now_iso(),
            skills=(),
        )

    def _stamped_now(self, index: RegistryIndex) -> RegistryIndex:
        return RegistryIndex(
            registry_name=index.registry_name,
            base_url=index.base_url,
            updated_at=_now_iso(),
            skills=index.skills,
        )

    def _is_git_repo(self) -> bool:
        return (self._root / ".git").exists()

    def _git_add(self, *paths: str) -> None:
        subprocess.run(
            [self._git, "-C", str(self._root), "add", *paths],
            check=True,
            capture_output=True,
        )

    def _has_staged_changes(self) -> bool:
        result = subprocess.run(
            [self._git, "-C", str(self._root), "diff", "--cached", "--name-only"],
            check=True,
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())

    def _git_commit(self, message: str) -> None:
        subprocess.run(
            [self._git, "-C", str(self._root), "commit", "-m", message],
            check=True,
            capture_output=True,
        )

    def _git_push(self) -> None:
        subprocess.run(
            [self._git, "-C", str(self._root), "push"],
            check=True,
            capture_output=True,
        )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
