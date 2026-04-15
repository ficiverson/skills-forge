#!/usr/bin/env python3
"""Phase 2: Pack Consistency Check.

Verifies every pack listed in index.json against the .skillpack file on disk.
Checks: file exists, sha256, size_bytes, manifest.version, export_formats, platforms.

Usage:
    python check_packs.py <path-to-skill-registry>
"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

ALL_FORMATS = {"system-prompt", "gpt-json", "gem-txt", "bedrock-xml", "mcp-server"}
ALL_PLATFORMS = {"claude", "gemini", "codex", "vscode", "agents"}


def check_registry(registry_path: Path) -> int:
    index_file = registry_path / "index.json"
    if not index_file.exists():
        print(f"❌ index.json not found at {index_file}")
        return 1

    index = json.loads(index_file.read_text())
    skills = index.get("skills", [])

    passed = 0
    failed = 0

    for skill in skills:
        skill_name = skill["name"]
        idx_platforms = set(skill.get("platforms", []))

        for ver in skill.get("versions", []):
            tag = f"{skill_name}@{ver['version']}"
            pack_path = registry_path / ver["path"]
            issues: list[str] = []

            # 1. File exists
            if not pack_path.exists():
                print(f"❌ {tag}: file missing — {ver['path']}")
                failed += 1
                continue

            # 2. sha256
            actual_sha = hashlib.sha256(pack_path.read_bytes()).hexdigest()
            if actual_sha != ver.get("sha256", ""):
                issues.append(
                    f"sha256 mismatch (index={ver.get('sha256','')[:12]}… disk={actual_sha[:12]}…)"
                )

            # 3. size_bytes
            actual_size = pack_path.stat().st_size
            if actual_size != ver.get("size_bytes", -1):
                issues.append(
                    f"size mismatch (index={ver.get('size_bytes')} disk={actual_size})"
                )

            # 4. manifest.version + manifest metadata
            try:
                with zipfile.ZipFile(pack_path) as zf:
                    manifest = json.loads(zf.read("manifest.json"))
            except Exception as exc:
                issues.append(f"cannot read manifest: {exc}")
                manifest = {}

            if manifest.get("version") != ver["version"]:
                issues.append(
                    f"manifest.version={manifest.get('version')!r} != index={ver['version']!r}"
                )

            # 5. export_formats — must match exactly the 5 core formats
            idx_fmts = set(ver.get("export_formats", []))
            mfst_fmts = set(manifest.get("export_formats", []))
            if idx_fmts != ALL_FORMATS:
                issues.append(f"index export_formats mismatch: {sorted(idx_fmts)}")
            if mfst_fmts != ALL_FORMATS:
                issues.append(f"manifest export_formats mismatch: {sorted(mfst_fmts)}")

            # 6. platforms (skill-level in index)
            if idx_platforms != ALL_PLATFORMS:
                issues.append(f"index platforms incomplete: {sorted(idx_platforms)}")
            mfst_platforms = set(manifest.get("platforms", []))
            if mfst_platforms != ALL_PLATFORMS:
                issues.append(f"manifest platforms incomplete: {sorted(mfst_platforms)}")

            if issues:
                print(f"❌ {tag}:")
                for issue in issues:
                    print(f"     · {issue}")
                failed += 1
            else:
                print(f"✅ {tag}")
                passed += 1

    total = passed + failed
    print()
    if failed == 0:
        print(f"All {total} packs passed ✅")
    else:
        print(f"{failed}/{total} packs FAILED ❌")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: check_packs.py <path-to-skill-registry>")
        sys.exit(1)
    sys.exit(check_registry(Path(sys.argv[1])))
