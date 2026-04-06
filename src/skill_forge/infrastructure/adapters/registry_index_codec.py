"""Serialize/deserialize a ``RegistryIndex`` to and from ``index.json``.

Kept separate from the publisher and fetcher so both adapters share one
canonical encoding. The format is intentionally tiny — a flat JSON file
that any client (Python, curl + jq, etc.) can read without ceremony.
"""

from __future__ import annotations

import json
from typing import Any

from skill_forge.domain.model import (
    IndexedSkill,
    IndexedVersion,
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
            "skills": [
                {
                    "category": s.category,
                    "name": s.name,
                    "latest": s.latest,
                    "versions": [
                        {
                            "version": v.version,
                            "path": v.path,
                            "sha256": v.sha256,
                        }
                        for v in s.versions
                    ],
                }
                for s in index.skills
            ],
        }
        return json.dumps(payload, indent=2, sort_keys=False) + "\n"

    def decode(self, text: str) -> RegistryIndex:
        data: dict[str, Any] = json.loads(text)
        format_version = str(data.get("format_version", "1"))
        if format_version != RegistryIndex.FORMAT_VERSION:
            raise ValueError(
                f"Unsupported registry index format version: {format_version}"
            )
        skills_raw = data.get("skills", [])
        skills: list[IndexedSkill] = []
        for s in skills_raw:
            versions = tuple(
                IndexedVersion(
                    version=v["version"],
                    path=v["path"],
                    sha256=v["sha256"],
                )
                for v in s.get("versions", [])
            )
            if not versions:
                continue
            latest = s.get("latest") or versions[-1].version
            skills.append(
                IndexedSkill(
                    category=s["category"],
                    name=s["name"],
                    latest=latest,
                    versions=versions,
                )
            )
        return RegistryIndex(
            registry_name=data["registry_name"],
            base_url=data["base_url"],
            updated_at=data.get("updated_at", ""),
            skills=tuple(skills),
        )
