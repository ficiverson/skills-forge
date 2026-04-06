"""Use cases: publish a pack to a registry, install a pack from a URL.

Together these turn any git-hosted repo into a free, CDN-backed skill
registry. ``PublishPack`` writes a ``.skillpack`` into the registry
clone and updates ``index.json``; ``InstallFromUrl`` fetches a pack from
``raw.githubusercontent.com`` (or any URL), verifies its sha256 if one
is supplied, unpacks it, and installs the contained skills.

The use cases stay free of HTTP and git details — those live in the
``PackPublisher`` and ``PackFetcher`` adapters.
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from skill_forge.application.use_cases.pack_skill import (
    UnpackSkill,
    UnpackSkillRequest,
)
from skill_forge.domain.model import (
    PublishResult,
    SkillPackManifest,
    SkillScope,
)
from skill_forge.domain.ports import (
    PackFetcher,
    PackPublisher,
    SkillInstaller,
    SkillPacker,
)


@dataclass
class PublishPackRequest:
    pack_path: Path
    message: str = ""
    push: bool = False


@dataclass
class PublishPackResponse:
    result: PublishResult
    manifest: SkillPackManifest


class PublishPack:
    """Publish an existing ``.skillpack`` to a registry."""

    def __init__(
        self,
        publisher: PackPublisher,
        packer: SkillPacker,
    ) -> None:
        self._publisher = publisher
        self._packer = packer

    def execute(self, request: PublishPackRequest) -> PublishPackResponse:
        if not request.pack_path.exists():
            raise FileNotFoundError(f"Pack does not exist: {request.pack_path}")
        manifest = self._packer.read_manifest(request.pack_path)
        result = self._publisher.publish(
            pack_path=request.pack_path,
            manifest=manifest,
            message=request.message,
            push=request.push,
        )
        return PublishPackResponse(result=result, manifest=manifest)


@dataclass
class InstallFromUrlRequest:
    url: str
    dest_dir: Path = field(default_factory=lambda: Path("output_skills"))
    scope: SkillScope = SkillScope.GLOBAL
    expected_sha256: str = ""
    install: bool = True


@dataclass
class InstallFromUrlResponse:
    manifest: SkillPackManifest
    extracted_paths: list[Path]
    installed_paths: list[Path]
    sha256: str


class InstallFromUrl:
    """Download a pack from a URL, unpack it, and install the skills.

    Set ``install=False`` if you only want to fetch and unpack (handy
    when the user wants to inspect or lint a pack before activating it).
    """

    def __init__(
        self,
        fetcher: PackFetcher,
        unpacker: UnpackSkill,
        installer: SkillInstaller,
    ) -> None:
        self._fetcher = fetcher
        self._unpacker = unpacker
        self._installer = installer

    def execute(self, request: InstallFromUrlRequest) -> InstallFromUrlResponse:
        with tempfile.TemporaryDirectory(prefix="skill-forge-fetch-") as tmp:
            tmp_pack = Path(tmp) / "downloaded.skillpack"
            self._fetcher.fetch(request.url, tmp_pack)

            actual_sha = _sha256(tmp_pack)
            if request.expected_sha256 and actual_sha != request.expected_sha256:
                raise ValueError(
                    "sha256 mismatch for downloaded pack: "
                    f"expected {request.expected_sha256}, got {actual_sha}"
                )

            unpack_response = self._unpacker.execute(
                UnpackSkillRequest(
                    pack_path=tmp_pack,
                    dest_dir=request.dest_dir,
                )
            )

            installed: list[Path] = []
            if request.install:
                for path in unpack_response.extracted_paths:
                    installed.append(self._installer.install(path, request.scope))

            return InstallFromUrlResponse(
                manifest=unpack_response.manifest,
                extracted_paths=unpack_response.extracted_paths,
                installed_paths=installed,
                sha256=actual_sha,
            )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
