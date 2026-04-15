"""Use cases: pack skills into a .skillpack and unpack them back out.

The pack format lets teams share skills via Slack, Notion, email, or any
other channel that can move a single file. The use cases here own the
business rules (validation, manifest construction); the actual zip I/O
lives in the SkillPacker adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from skill_forge.domain.model import (
    DEFAULT_SKILL_VERSION,
    ExportFormat,
    InstallTarget,
    Owner,
    Skill,
    SkillPackManifest,
    SkillRef,
)
from skill_forge.domain.ports import SkillPacker, SkillParser


@dataclass
class PackSkillRequest:
    """Pack one or more skill directories into a single .skillpack file.

    Each directory must contain a SKILL.md. The pack name defaults to
    the first skill's name when packing a single skill.

    If ``version`` is left empty, the pack version is derived from the
    skill itself (when packing a single skill) or falls back to the
    skill's default version (when packing a multi-skill bundle).
    """

    skill_dirs: list[Path]
    output_path: Path
    version: str = ""
    author: str = ""
    pack_name: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    export_formats: tuple[str, ...] = ()
    owner_name: str = ""
    owner_email: str = ""
    deprecated: bool = False


@dataclass
class PackSkillResponse:
    pack_path: Path
    manifest: SkillPackManifest


@dataclass
class UnpackSkillRequest:
    pack_path: Path
    dest_dir: Path = field(default_factory=lambda: Path("output_skills"))


@dataclass
class UnpackSkillResponse:
    manifest: SkillPackManifest
    extracted_paths: list[Path]


class PackSkill:
    """Bundle one or more skills into a portable .skillpack archive."""

    def __init__(self, packer: SkillPacker, parser: SkillParser) -> None:
        self._packer = packer
        self._parser = parser

    def execute(self, request: PackSkillRequest) -> PackSkillResponse:
        if not request.skill_dirs:
            raise ValueError("PackSkillRequest must include at least one skill")

        skills_with_dirs = [(self._load_skill(d), d) for d in request.skill_dirs]
        refs = [self._build_ref(skill, skill_dir) for skill, skill_dir in skills_with_dirs]

        pack_name = request.pack_name or refs[0].name
        pack_version = self._resolve_pack_version(request.version, refs)

        # Mirror the first skill's frontmatter description into the
        # manifest when the caller didn't supply one — saves typing the
        # same string twice and lets `publish` carry it into the index.
        description = request.description or skills_with_dirs[0][0].description.text
        owner = (
            Owner(name=request.owner_name, email=request.owner_email)
            if request.owner_name
            else None
        )

        # Default to all supported platforms and formats if not explicitly specified.
        # This makes the registry index entries high-fidelity by default.
        platforms = tuple(request.platforms)
        if not platforms:
            platforms = tuple(t.value for t in InstallTarget if t != InstallTarget.ALL)

        export_formats = tuple(request.export_formats)
        if not export_formats:
            export_formats = tuple(f.value for f in ExportFormat)

        manifest = SkillPackManifest(
            name=pack_name,
            version=pack_version,
            author=request.author,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            description=description,
            skills=tuple(refs),
            tags=tuple(request.tags),
            platforms=platforms,
            export_formats=export_formats,
            owner=owner,
            deprecated=request.deprecated,
        )

        output = request.output_path
        if output.is_dir() or output.suffix != ".skillpack":
            output = output / f"{pack_name}-{pack_version}.skillpack"

        pack_path = self._packer.pack(request.skill_dirs, manifest, output)
        return PackSkillResponse(pack_path=pack_path, manifest=manifest)

    def _load_skill(self, skill_dir: Path) -> Skill:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise FileNotFoundError(f"Directory is not a skill (no SKILL.md): {skill_dir}")
        return self._parser.parse(skill_md.read_text(encoding="utf-8"), base_path=skill_md)

    def _build_ref(self, skill: Skill, skill_dir: Path) -> SkillRef:
        # The convention everywhere is `<base>/<category>/<name>/SKILL.md`,
        # so the immediate parent of skill_dir is the authoritative category.
        # The parser's category inference is only reliable when paths sit
        # under `output_skills/`, which isn't always the case at pack time.
        category = skill_dir.parent.name
        return SkillRef(
            category=category,
            name=skill.identity.name,
            version=skill.version,
        )

    def _resolve_pack_version(self, requested_version: str, refs: list[SkillRef]) -> str:
        """Pick the version printed on the pack itself.

        Precedence:
        1. Explicit ``--version`` from the request (overrides everything).
        2. Single-skill pack: use that skill's own version.
        3. Multi-skill bundle without an explicit version: fall back to
           the default. Bundles really should specify their own version,
           but we don't error out — we let the caller ship something.
        """
        if requested_version:
            return requested_version
        if len(refs) == 1:
            return refs[0].version
        return DEFAULT_SKILL_VERSION


class UnpackSkill:
    """Extract a .skillpack into a destination directory."""

    def __init__(self, packer: SkillPacker) -> None:
        self._packer = packer

    def execute(self, request: UnpackSkillRequest) -> UnpackSkillResponse:
        manifest = self._packer.unpack(request.pack_path, request.dest_dir)
        extracted = [request.dest_dir / ref.category / ref.name for ref in manifest.skills]
        return UnpackSkillResponse(manifest=manifest, extracted_paths=extracted)
