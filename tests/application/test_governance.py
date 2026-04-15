"""v0.7.0 governance tests: codec roundtrip for new fields + doctor yanked check."""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import (
    IndexedSkill,
    IndexedVersion,
    RegistryIndex,
)
from skill_forge.infrastructure.adapters.registry_index_codec import RegistryIndexCodec

# ── helpers ───────────────────────────────────────────────────────────────────


def _base_index(skill_name: str = "python-tdd") -> RegistryIndex:
    return RegistryIndex(
        registry_name="test",
        base_url="https://reg.example.com",
        updated_at="2026-04-11T00:00:00Z",
        skills=(
            IndexedSkill(
                category="dev",
                name=skill_name,
                latest="1.1.0",
                versions=(
                    IndexedVersion(
                        version="1.0.0",
                        path=f"packs/dev/{skill_name}-1.0.0.skillpack",
                        sha256="a" * 64,
                        yanked=True,
                        yank_reason="security issue",
                    ),
                    IndexedVersion(
                        version="1.1.0",
                        path=f"packs/dev/{skill_name}-1.1.0.skillpack",
                        sha256="b" * 64,
                    ),
                ),
                deprecated=True,
                replaced_by="new-skill",
                deprecation_message="Use new-skill v2",
            ),
        ),
    )


# ── codec roundtrip ───────────────────────────────────────────────────────────


class TestCodecRoundtrip:
    def test_yank_reason_survives_encode_decode(self) -> None:
        codec = RegistryIndexCodec()
        index = _base_index()
        decoded = codec.decode(codec.encode(index))
        skill = decoded.find("dev", "python-tdd")
        assert skill is not None
        v = skill.find("1.0.0")
        assert v is not None
        assert v.yanked is True
        assert v.yank_reason == "security issue"

    def test_non_yanked_version_has_empty_yank_reason(self) -> None:
        codec = RegistryIndexCodec()
        index = _base_index()
        decoded = codec.decode(codec.encode(index))
        skill = decoded.find("dev", "python-tdd")
        assert skill is not None
        v = skill.find("1.1.0")
        assert v is not None
        assert v.yanked is False
        assert v.yank_reason == ""

    def test_replaced_by_survives_encode_decode(self) -> None:
        codec = RegistryIndexCodec()
        index = _base_index()
        decoded = codec.decode(codec.encode(index))
        skill = decoded.find("dev", "python-tdd")
        assert skill is not None
        assert skill.replaced_by == "new-skill"

    def test_deprecation_message_survives_encode_decode(self) -> None:
        codec = RegistryIndexCodec()
        index = _base_index()
        decoded = codec.decode(codec.encode(index))
        skill = decoded.find("dev", "python-tdd")
        assert skill is not None
        assert skill.deprecation_message == "Use new-skill v2"

    def test_deprecated_flag_survives_encode_decode(self) -> None:
        codec = RegistryIndexCodec()
        index = _base_index()
        decoded = codec.decode(codec.encode(index))
        skill = decoded.find("dev", "python-tdd")
        assert skill is not None
        assert skill.deprecated is True

    def test_missing_fields_default_safely(self) -> None:
        """Older index.json without new fields should still decode cleanly."""
        codec = RegistryIndexCodec()
        _sha = "a" * 64
        raw = f"""{{
            "format_version": "3",
            "registry_name": "test",
            "base_url": "https://reg.example.com",
            "updated_at": "",
            "skills": [
                {{
                    "category": "dev",
                    "name": "python-tdd",
                    "latest": "1.0.0",
                    "versions": [
                        {{
                            "version": "1.0.0",
                            "path": "packs/dev/python-tdd-1.0.0.skillpack",
                            "sha256": "{_sha}"
                        }}
                    ]
                }}
            ]
        }}"""
        decoded = codec.decode(raw)
        skill = decoded.find("dev", "python-tdd")
        assert skill is not None
        assert skill.deprecated is False
        assert skill.replaced_by == ""
        assert skill.deprecation_message == ""
        v = skill.find("1.0.0")
        assert v is not None
        assert v.yanked is False
        assert v.yank_reason == ""

    def test_yank_reason_omitted_when_empty(self) -> None:
        """Non-yanked versions must not emit 'yank_reason' key in JSON."""
        import json

        codec = RegistryIndexCodec()
        index = RegistryIndex(
            registry_name="t",
            base_url="https://x.example.com",
            updated_at="",
            skills=(
                IndexedSkill(
                    category="dev",
                    name="x",
                    latest="1.0.0",
                    versions=(
                        IndexedVersion(
                            version="1.0.0",
                            path="packs/dev/x-1.0.0.skillpack",
                            sha256="a" * 64,
                        ),
                    ),
                ),
            ),
        )
        payload = json.loads(codec.encode(index))
        ver_obj = payload["skills"][0]["versions"][0]
        assert "yank_reason" not in ver_obj
        assert "yanked" not in ver_obj

    def test_replaced_by_omitted_when_empty(self) -> None:
        import json

        codec = RegistryIndexCodec()
        index = RegistryIndex(
            registry_name="t",
            base_url="https://x.example.com",
            updated_at="",
            skills=(
                IndexedSkill(
                    category="dev",
                    name="x",
                    latest="1.0.0",
                    versions=(
                        IndexedVersion(
                            version="1.0.0",
                            path="packs/dev/x-1.0.0.skillpack",
                            sha256="a" * 64,
                        ),
                    ),
                ),
            ),
        )
        payload = json.loads(codec.encode(index))
        skill_obj = payload["skills"][0]
        assert "replaced_by" not in skill_obj
        assert "deprecation_message" not in skill_obj


# ── doctor yanked check ───────────────────────────────────────────────────────


class TestDoctorYankedCheck:
    """Integration tests: doctor reports yanked-version when installed version is yanked."""

    def _make_skill_dir(self, tmp_path: Path, skill_name: str, version: str) -> Path:
        d = tmp_path / skill_name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {skill_name}\nversion: {version}\ndescription: test\n---\n",
            encoding="utf-8",
        )
        return d

    def test_doctor_flags_yanked_installed_version(self, tmp_path: Path) -> None:
        from skill_forge.application.use_cases.doctor_skill import DoctorSkill
        from skill_forge.domain.model import InstallTarget, SkillScope
        from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

        skill_dir = self._make_skill_dir(tmp_path, "python-tdd", "1.0.0")

        class _StubInstaller:
            def scan_all_targets(self, scope):  # type: ignore[no-untyped-def]
                return {InstallTarget.CLAUDE: [skill_dir]}

            def is_installed(self, name, scope):  # type: ignore[no-untyped-def]
                return True

        class _StubFetcher:
            def fetch_index(self, url):  # type: ignore[no-untyped-def]
                return RegistryIndex(
                    registry_name="t",
                    base_url="https://x",
                    updated_at="",
                    skills=(
                        IndexedSkill(
                            category="dev",
                            name="python-tdd",
                            latest="1.0.0",
                            versions=(
                                IndexedVersion(
                                    version="1.0.0",
                                    path="packs/dev/python-tdd-1.0.0.skillpack",
                                    sha256="a" * 64,
                                    yanked=True,
                                    yank_reason="security: injection vector",
                                ),
                            ),
                        ),
                    ),
                )

        use_case = DoctorSkill(
            installer=_StubInstaller(),  # type: ignore[arg-type]
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(),  # type: ignore[arg-type]
        )
        response = use_case.execute(
            scope=SkillScope.GLOBAL,
            registry_url="https://reg.example.com",
        )

        yanked_issues = [i for i in response.issues if i.kind == "yanked-version"]
        assert len(yanked_issues) == 1
        assert "1.0.0" in yanked_issues[0].message
        assert "yanked" in yanked_issues[0].message.lower()
        assert "injection vector" in yanked_issues[0].message

    def test_doctor_no_yanked_issue_when_not_yanked(self, tmp_path: Path) -> None:
        from skill_forge.application.use_cases.doctor_skill import DoctorSkill
        from skill_forge.domain.model import InstallTarget, SkillScope
        from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

        skill_dir = self._make_skill_dir(tmp_path, "python-tdd", "1.0.0")

        class _StubInstaller:
            def scan_all_targets(self, scope):  # type: ignore[no-untyped-def]
                return {InstallTarget.CLAUDE: [skill_dir]}

            def is_installed(self, name, scope):  # type: ignore[no-untyped-def]
                return True

        class _StubFetcher:
            def fetch_index(self, url):  # type: ignore[no-untyped-def]
                return RegistryIndex(
                    registry_name="t",
                    base_url="https://x",
                    updated_at="",
                    skills=(
                        IndexedSkill(
                            category="dev",
                            name="python-tdd",
                            latest="1.0.0",
                            versions=(
                                IndexedVersion(
                                    version="1.0.0",
                                    path="packs/dev/python-tdd-1.0.0.skillpack",
                                    sha256="a" * 64,
                                    yanked=False,
                                ),
                            ),
                        ),
                    ),
                )

        use_case = DoctorSkill(
            installer=_StubInstaller(),  # type: ignore[arg-type]
            parser=MarkdownSkillParser(),
            fetcher=_StubFetcher(),  # type: ignore[arg-type]
        )
        response = use_case.execute(
            scope=SkillScope.GLOBAL,
            registry_url="https://reg.example.com",
        )

        yanked_issues = [i for i in response.issues if i.kind == "yanked-version"]
        assert len(yanked_issues) == 0
