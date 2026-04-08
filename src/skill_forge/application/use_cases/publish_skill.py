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
    Owner,
    PublishMetadata,
    PublishResult,
    SkillPackManifest,
    SkillScope,
)
from skill_forge.domain.ports import (
    PackFetcher,
    PackPublisher,
    SkillInstaller,
    SkillPacker,
    SkillParser,
)


@dataclass
class PublishPackRequest:
    pack_path: Path
    message: str = ""
    push: bool = False
    tags: tuple[str, ...] = ()
    owner_name: str = ""
    owner_email: str = ""
    deprecated: bool = False
    release_notes: str = ""
    yanked: bool = False


@dataclass
class PublishPackResponse:
    result: PublishResult
    manifest: SkillPackManifest


class PublishPack:
    """Publish an existing ``.skillpack`` to a registry.

    Reads the skill's description out of the pack (so the registry index
    can mirror it without the user typing it twice) and combines it with
    publish-time metadata supplied via the request.
    """

    def __init__(
        self,
        publisher: PackPublisher,
        packer: SkillPacker,
        parser: SkillParser | None = None,
    ) -> None:
        self._publisher = publisher
        self._packer = packer
        self._parser = parser

    def execute(self, request: PublishPackRequest) -> PublishPackResponse:
        if not request.pack_path.exists():
            raise FileNotFoundError(f"Pack does not exist: {request.pack_path}")
        manifest = self._packer.read_manifest(request.pack_path)

        # Defaults flow from the manifest (baked in at pack time);
        # CLI flags on the request override.
        description = (
            manifest.description
            or self._read_description(request.pack_path, manifest)
        )
        tags = tuple(request.tags) if request.tags else manifest.tags
        if request.owner_name:
            owner: Owner | None = Owner(
                name=request.owner_name,
                email=request.owner_email,
            )
        else:
            owner = manifest.owner
        deprecated = request.deprecated or manifest.deprecated

        # Enforce required registry metadata — fail fast with actionable messages
        # so the registry never receives incomplete entries.
        _errors: list[str] = []
        if not description:
            _errors.append(
                "description is required — bake it in with "
                '`skills-forge pack --description "..."`'
            )
        if not tags:
            _errors.append(
                "at least one tag is required — bake it in with "
                "`skills-forge pack --tag <tag>`"
            )
        if owner is None or not owner.name or not owner.email:
            _errors.append(
                "owner name and email are required — bake them in with "
                '`skills-forge pack --owner-name "..." --owner-email "..."`'
                " (or override at publish time with --owner-name / --owner-email)"
            )
        if _errors:
            raise ValueError(
                "Cannot publish: missing required registry metadata:\n"
                + "\n".join(f"  • {e}" for e in _errors)
            )

        metadata = PublishMetadata(
            description=description,
            tags=tags,
            owner=owner,
            deprecated=deprecated,
            release_notes=request.release_notes,
            yanked=request.yanked,
        )

        result = self._publisher.publish(
            pack_path=request.pack_path,
            manifest=manifest,
            message=request.message,
            push=request.push,
            metadata=metadata,
        )
        return PublishPackResponse(result=result, manifest=manifest)

    def _read_description(
        self, pack_path: Path, manifest: SkillPackManifest
    ) -> str:
        """Pull the SKILL.md description out of the pack via a temp unpack.

        Returns ``""`` if anything goes wrong — the upsert preserves the
        existing index value when no description is supplied, so a parse
        miss is a soft fall-through rather than a hard failure.
        """
        if self._parser is None:
            return ""
        ref = manifest.skills[0]
        try:
            with tempfile.TemporaryDirectory(prefix="skills-forge-pub-") as tmp:
                tmp_dir = Path(tmp)
                self._packer.unpack(pack_path, tmp_dir)
                skill_md = tmp_dir / ref.category / ref.name / "SKILL.md"
                if not skill_md.exists():
                    return ""
                skill = self._parser.parse(
                    skill_md.read_text(encoding="utf-8"),
                    base_path=skill_md.parent,
                )
                return skill.description.text
        except Exception:
            return ""


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
        with tempfile.TemporaryDirectory(prefix="skills-forge-fetch-") as tmp:
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
                    installed.extend(self._installer.install(path, request.scope))

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
