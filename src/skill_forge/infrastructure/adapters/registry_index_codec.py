"""Serialize/deserialize a ``RegistryIndex`` to and from ``index.json``.

Kept separate from the publisher and fetcher so both adapters share one
canonical encoding. The format is intentionally tiny — a flat JSON file
that any client (Python, curl + jq, etc.) can read without ceremony.

Schema evolution: new fields are written by the encoder when they have a
non-default value, and the decoder fills them in with safe defaults when
absent. That keeps older ``index.json`` files installable by newer
clients and lets newer publishers add metadata without breaking older
ones that ignore unknown keys.
"""

from __future__ import annotations

import json
from typing import Any

from skill_forge.domain.model import (
    IndexedSkill,
    IndexedVersion,
    Owner,
    RegistryIndex,
)


class RegistryIndexCodec:
    """Pure JSON ↔ ``RegistryIndex`` translator. No I/O."""

    def encode(self, index: RegistryIndex) -> str:
        payload = {
            "format_version": RegistryIndex.FORMAT_VERSION,
            "registry_name": index.registry_name,
            "base_url": index.base_url,
            "updated_at": index.updated_at,
            "skills": [self._encode_skill(s) for s in index.skills],
        }
        return json.dumps(payload, indent=2, sort_keys=False) + "\n"

    def decode(self, text: str) -> RegistryIndex:
        data: dict[str, Any] = json.loads(text)
        format_version = str(data.get("format_version", "1"))
        _supported = {"1", "2", "3"}
        if format_version not in _supported:
            raise ValueError(
                f"Unsupported registry index format version: {format_version!r} "
                f"(supported: {sorted(_supported)})"
            )
        skills_raw = data.get("skills", [])
        skills: list[IndexedSkill] = []
        for s in skills_raw:
            decoded = self._decode_skill(s)
            if decoded is not None:
                skills.append(decoded)
        return RegistryIndex(
            registry_name=data["registry_name"],
            base_url=data["base_url"],
            updated_at=data.get("updated_at", ""),
            skills=tuple(skills),
        )

    # ----------------------------------------------------------------- helpers

    def _encode_skill(self, s: IndexedSkill) -> dict[str, Any]:
        out: dict[str, Any] = {
            "category": s.category,
            "name": s.name,
            "latest": s.latest,
        }
        if s.description:
            out["description"] = s.description
        if s.tags:
            out["tags"] = list(s.tags)
        if s.platforms:
            out["platforms"] = list(s.platforms)
        if s.owner is not None:
            owner_payload: dict[str, Any] = {"name": s.owner.name}
            if s.owner.email:
                owner_payload["email"] = s.owner.email
            out["owner"] = owner_payload
        if s.deprecated:
            out["deprecated"] = True
        out["versions"] = [self._encode_version(v) for v in s.versions]
        return out

    def _encode_version(self, v: IndexedVersion) -> dict[str, Any]:
        out: dict[str, Any] = {
            "version": v.version,
            "path": v.path,
            "sha256": v.sha256,
        }
        if v.published_at:
            out["published_at"] = v.published_at
        if v.size_bytes:
            out["size_bytes"] = v.size_bytes
        if v.release_notes:
            out["release_notes"] = v.release_notes
        if v.yanked:
            out["yanked"] = True
        if v.export_formats:
            out["export_formats"] = list(v.export_formats)
        return out

    def _decode_skill(self, s: dict[str, Any]) -> IndexedSkill | None:
        versions = tuple(self._decode_version(v) for v in s.get("versions", []))
        if not versions:
            return None
        latest = s.get("latest") or versions[-1].version
        owner_raw = s.get("owner")
        owner: Owner | None = None
        if isinstance(owner_raw, dict) and owner_raw.get("name"):
            owner = Owner(
                name=str(owner_raw["name"]),
                email=str(owner_raw.get("email", "")),
            )
        tags_raw = s.get("tags") or []
        platforms_raw = s.get("platforms") or []
        return IndexedSkill(
            category=s["category"],
            name=s["name"],
            latest=latest,
            versions=versions,
            description=str(s.get("description", "")),
            tags=tuple(str(t) for t in tags_raw),
            platforms=tuple(str(p) for p in platforms_raw),
            owner=owner,
            deprecated=bool(s.get("deprecated", False)),
        )

    def _decode_version(self, v: dict[str, Any]) -> IndexedVersion:
        export_formats_raw = v.get("export_formats") or []
        return IndexedVersion(
            version=v["version"],
            path=v["path"],
            sha256=v["sha256"],
            published_at=str(v.get("published_at", "")),
            size_bytes=int(v.get("size_bytes", 0) or 0),
            release_notes=str(v.get("release_notes", "")),
            yanked=bool(v.get("yanked", False)),
            export_formats=tuple(str(f) for f in export_formats_raw),
        )
