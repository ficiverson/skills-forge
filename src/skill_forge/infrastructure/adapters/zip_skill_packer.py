"""Zip-based implementation of the SkillPacker port.

A `.skillpack` is a deflate-compressed zip with this layout:

    manifest.json                 # Pack metadata (see SkillPackManifest)
    skills/<category>/<name>/...  # One subtree per packed skill

The format is intentionally boring: any zip tool can inspect or extract
a pack, and the manifest is plain JSON.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from skill_forge.domain.model import Owner, SkillPackManifest, SkillRef
from skill_forge.domain.ports import SkillPacker

_MANIFEST_NAME = "manifest.json"
_SKILLS_PREFIX = "skills"

# Files we never include in a pack — keeps cruft out and prevents accidental
# leakage of editor / VCS state.
_EXCLUDED_NAMES = {
    ".git",
    ".gitignore",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".DS_Store",
    ".venv",
}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


class ZipSkillPacker(SkillPacker):
    """Pack and unpack skills using the stdlib `zipfile` module."""

    def pack(
        self,
        skill_dirs: list[Path],
        manifest: SkillPackManifest,
        output_path: Path,
    ) -> Path:
        if not skill_dirs:
            raise ValueError("Cannot pack zero skills")
        if len(skill_dirs) != manifest.skill_count:
            raise ValueError(
                f"Manifest references {manifest.skill_count} skills "
                f"but {len(skill_dirs)} directories were provided"
            )

        for skill_dir in skill_dirs:
            if not skill_dir.exists() or not skill_dir.is_dir():
                raise FileNotFoundError(f"Skill directory not found: {skill_dir}")
            if not (skill_dir / "SKILL.md").exists():
                raise FileNotFoundError(
                    f"Directory is not a skill (no SKILL.md): {skill_dir}"
                )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(_MANIFEST_NAME, _serialize_manifest(manifest))

            for skill_dir, ref in zip(skill_dirs, manifest.skills, strict=True):
                arc_root = f"{_SKILLS_PREFIX}/{ref.category}/{ref.name}"
                _add_directory(zf, skill_dir, arc_root)

        return output_path

    def unpack(self, pack_path: Path, dest_dir: Path) -> SkillPackManifest:
        if not pack_path.exists():
            raise FileNotFoundError(f"Pack not found: {pack_path}")

        with zipfile.ZipFile(pack_path, "r") as zf:
            manifest = _read_manifest_from_zip(zf)
            dest_dir.mkdir(parents=True, exist_ok=True)

            for member in zf.namelist():
                if member == _MANIFEST_NAME:
                    continue
                if not member.startswith(f"{_SKILLS_PREFIX}/"):
                    continue
                if member.endswith("/"):
                    continue
                # Strip the "skills/" prefix so contents land at
                # dest_dir/<category>/<name>/...
                relative = member[len(_SKILLS_PREFIX) + 1 :]
                target = _safe_join(dest_dir, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as source, open(target, "wb") as out:
                    out.write(source.read())

        return manifest

    def read_manifest(self, pack_path: Path) -> SkillPackManifest:
        if not pack_path.exists():
            raise FileNotFoundError(f"Pack not found: {pack_path}")
        with zipfile.ZipFile(pack_path, "r") as zf:
            return _read_manifest_from_zip(zf)


def _serialize_manifest(manifest: SkillPackManifest) -> str:
    # Optional fields are only written when set, so older readers that
    # don't know about them stay forwards-compatible and the on-disk
    # JSON stays minimal.
    payload: dict[str, object] = {
        "format_version": SkillPackManifest.FORMAT_VERSION,
        "name": manifest.name,
        "version": manifest.version,
        "author": manifest.author,
        "created_at": manifest.created_at,
        "description": manifest.description,
        "skills": [
            {
                "category": s.category,
                "name": s.name,
                "version": s.version,
            }
            for s in manifest.skills
        ],
    }
    if manifest.tags:
        payload["tags"] = list(manifest.tags)
    if manifest.owner is not None:
        owner_payload: dict[str, object] = {"name": manifest.owner.name}
        if manifest.owner.email:
            owner_payload["email"] = manifest.owner.email
        payload["owner"] = owner_payload
    if manifest.deprecated:
        payload["deprecated"] = True
    return json.dumps(payload, indent=2, sort_keys=True)


def _read_manifest_from_zip(zf: zipfile.ZipFile) -> SkillPackManifest:
    try:
        raw = zf.read(_MANIFEST_NAME).decode("utf-8")
    except KeyError as exc:
        raise ValueError("Pack is missing manifest.json") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Pack manifest is not valid JSON: {exc}") from exc

    format_version = data.get("format_version")
    if format_version != SkillPackManifest.FORMAT_VERSION:
        raise ValueError(
            f"Unsupported pack format version: {format_version!r} "
            f"(expected {SkillPackManifest.FORMAT_VERSION!r})"
        )

    skills_data = data.get("skills") or []
    if not skills_data:
        raise ValueError("Pack manifest lists zero skills")

    skills = tuple(
        SkillRef(
            category=s["category"],
            name=s["name"],
            # Older packs (format_version 1, pre per-skill version) won't
            # have this key — fall back to the pack-level version so the
            # SkillRef invariant (non-empty version) still holds.
            version=s.get("version") or data.get("version", "0.1.0"),
        )
        for s in skills_data
    )

    owner_raw = data.get("owner")
    owner: Owner | None = None
    if isinstance(owner_raw, dict) and owner_raw.get("name"):
        owner = Owner(
            name=str(owner_raw["name"]),
            email=str(owner_raw.get("email", "")),
        )
    tags_raw = data.get("tags") or []

    return SkillPackManifest(
        name=data.get("name", ""),
        version=data.get("version", ""),
        author=data.get("author", ""),
        created_at=data.get("created_at", ""),
        description=data.get("description", ""),
        skills=skills,
        tags=tuple(str(t) for t in tags_raw),
        owner=owner,
        deprecated=bool(data.get("deprecated", False)),
    )


def _add_directory(zf: zipfile.ZipFile, source_dir: Path, arc_root: str) -> None:
    for path in sorted(source_dir.rglob("*")):
        if _should_exclude(path, source_dir):
            continue
        if not path.is_file():
            continue
        relative = path.relative_to(source_dir)
        arcname = f"{arc_root}/{relative.as_posix()}"
        zf.write(path, arcname)


def _should_exclude(path: Path, root: Path) -> bool:
    if path.suffix in _EXCLUDED_SUFFIXES:
        return True
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return False
    return any(part in _EXCLUDED_NAMES for part in rel_parts)


def _safe_join(base: Path, relative: str) -> Path:
    """Resolve `relative` under `base` and refuse path-traversal escapes.

    Defends against the ``zip-slip`` family of vulnerabilities where a
    crafted archive uses ``../`` entries to write outside the destination.
    """
    candidate = (base / relative).resolve()
    base_resolved = base.resolve()
    try:
        candidate.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(
            f"Refusing to extract entry outside destination: {relative}"
        ) from exc
    return candidate
