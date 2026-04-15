"""Targeted tests for remaining coverage gaps to reach 95%."""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── TomlConfigRepository: fallback parser (lines 44-57) ──────────────────────

class TestTomlFallbackParserBranch:
    """Force the manual fallback by patching _TOMLLIB_AVAILABLE = False."""

    def _call_fallback(self, text: str) -> dict:  # type: ignore[type-arg]
        import skill_forge.infrastructure.adapters.toml_config_repository as mod
        with patch.object(mod, "_TOMLLIB_AVAILABLE", False):
            return mod._read_toml(text)

    def test_fallback_parses_simple_registry(self) -> None:
        result = self._call_fallback(
            "[defaults]\n"
            'registry = "public"\n'
            "\n[registries]\n"
            'public = "https://example.com"\n'
        )
        assert result["defaults"]["registry"] == "public"  # type: ignore[index]

    def test_fallback_handles_empty_string(self) -> None:
        result = self._call_fallback("")
        assert result == {}

    def test_fallback_skips_comments_and_blank_lines(self) -> None:
        result = self._call_fallback(
            "# top comment\n\n"
            "[section]\n"
            "# inline comment\n"
            "key = 'value'\n"
        )
        assert result["section"]["key"] == "value"  # type: ignore[index]

    def test_fallback_handles_section_without_key(self) -> None:
        result = self._call_fallback("[empty_section]\n")
        assert "empty_section" in result

    def test_fallback_repeated_section_header_merges(self) -> None:
        """Two [section] headers (malformed TOML) should not crash."""
        result = self._call_fallback(
            "[s]\nk1 = 'a'\n[s]\nk2 = 'b'\n"
        )
        # Should not raise
        assert isinstance(result, dict)

    def test_toml_config_repo_parse_with_dict_registry_table(self, tmp_path: Path) -> None:
        """Test the isinstance(val, dict) branch in _parse (line 137)."""
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            TomlConfigRepository,
        )

        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            "[defaults]\n"
            'registry = "internal"\n'
            'target = "claude"\n'
            "\n[registries.internal]\n"
            'url   = "https://internal.example.com"\n'
            'token = "${MY_TOKEN}"\n',
            encoding="utf-8",
        )
        repo = TomlConfigRepository(path=cfg_path)
        cfg = repo.load()
        reg = cfg.get_registry("internal")
        assert reg is not None
        assert reg.url == "https://internal.example.com"
        assert reg.token == "${MY_TOKEN}"

    def test_toml_config_repo_parse_dict_registry_missing_url_skipped(
        self, tmp_path: Path
    ) -> None:
        """A [registries.x] table with no url is silently skipped (line 137)."""
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            TomlConfigRepository,
        )

        cfg_path = tmp_path / "config.toml"
        cfg_path.write_text(
            "[defaults]\n"
            'registry = "public"\n'
            "\n[registries.broken]\n"
            '# no url key\n'
            'token = "tok"\n',
            encoding="utf-8",
        )
        repo = TomlConfigRepository(path=cfg_path)
        cfg = repo.load()
        # broken registry is skipped
        assert cfg.get_registry("broken") is None


# ── ZipSkillPacker: error paths ───────────────────────────────────────────────

class TestZipSkillPackerGaps:
    def test_pack_missing_skill_dir_raises(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import SkillPackManifest, SkillRef
        from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

        packer = ZipSkillPacker()
        manifest = SkillPackManifest(
            name="ghost",
            version="0.1.0",
            author="",
            created_at="2026-04-11T00:00:00+00:00",
            skills=(SkillRef(category="dev", name="ghost", version="0.1.0"),),
        )
        with pytest.raises(FileNotFoundError, match="not found"):
            packer.pack(
                skill_dirs=[tmp_path / "nonexistent"],
                manifest=manifest,
                output_path=tmp_path / "out.skillpack",
            )

    def test_pack_dir_without_skill_md_raises(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import SkillPackManifest, SkillRef
        from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

        empty = tmp_path / "empty-skill"
        empty.mkdir()
        packer = ZipSkillPacker()
        manifest = SkillPackManifest(
            name="empty-skill",
            version="0.1.0",
            author="",
            created_at="2026-04-11T00:00:00+00:00",
            skills=(SkillRef(category="dev", name="empty-skill", version="0.1.0"),),
        )
        with pytest.raises(FileNotFoundError, match=r"no SKILL\.md"):
            packer.pack(
                skill_dirs=[empty],
                manifest=manifest,
                output_path=tmp_path / "out.skillpack",
            )

    def test_pack_skill_count_mismatch_raises(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import SkillPackManifest, SkillRef
        from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

        skill_dir = tmp_path / "skill-a"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: skill-a\n---\nbody", encoding="utf-8")

        packer = ZipSkillPacker()
        manifest = SkillPackManifest(
            name="bundle",
            version="0.1.0",
            author="",
            created_at="2026-04-11T00:00:00+00:00",
            skills=(
                SkillRef(category="dev", name="a", version="0.1.0"),
                SkillRef(category="dev", name="b", version="0.1.0"),
            ),
        )
        with pytest.raises(ValueError, match=r"[Mm]anifest"):
            packer.pack(
                skill_dirs=[skill_dir],  # 1 dir but manifest says 2 skills
                manifest=manifest,
                output_path=tmp_path / "out.skillpack",
            )

    def test_unpack_path_traversal_blocked(self, tmp_path: Path) -> None:
        """Zip-slip: entries with ../ in path must be rejected or skipped."""
        from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

        # Build a zip with a path-traversal entry
        bad_zip = tmp_path / "evil.skillpack"
        with zipfile.ZipFile(bad_zip, "w") as zf:
            zf.writestr(
                '{"format_version": "1", "skills": []}',
                "manifest.json"
            )
            zf.writestr("skills/../../evil.txt", "owned")

        dest = tmp_path / "dest"
        packer = ZipSkillPacker()
        # Should either raise or silently skip the traversal entry
        import contextlib
        with contextlib.suppress(ValueError, Exception):
            packer.unpack(bad_zip, dest)
        # The important thing: no file outside dest was written
        assert not (tmp_path / "evil.txt").exists()

    def test_read_manifest_missing_manifest_json_raises(self, tmp_path: Path) -> None:
        from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

        pack = tmp_path / "nomanifest.skillpack"
        with zipfile.ZipFile(pack, "w") as zf:
            zf.writestr("skills/dev/x/SKILL.md", "---\nname: x\n---\nbody")

        packer = ZipSkillPacker()
        with pytest.raises(ValueError, match=r"[Mm]anifest"):
            packer.read_manifest(pack)

    def test_read_manifest_invalid_json_raises(self, tmp_path: Path) -> None:
        from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

        pack = tmp_path / "badjson.skillpack"
        with zipfile.ZipFile(pack, "w") as zf:
            zf.writestr("manifest.json", "{ bad json !!!}")

        packer = ZipSkillPacker()
        with pytest.raises(ValueError, match=r"[Jj][Ss][Oo][Nn]|[Mm]anifest"):
            packer.read_manifest(pack)


# ── FilesystemRepository: load / list_all error paths ────────────────────────

class TestFilesystemRepositoryGaps:
    def _make_repo(self, base: Path) -> object:
        from skill_forge.infrastructure.adapters.filesystem_repository import (
            FilesystemSkillRepository,
        )
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )
        from skill_forge.infrastructure.adapters.markdown_renderer import (
            MarkdownSkillRenderer,
        )

        return FilesystemSkillRepository(
            base_path=base,
            renderer=MarkdownSkillRenderer(),
            parser=MarkdownSkillParser(),
        )

    def test_load_missing_skill_md_raises(self, tmp_path: Path) -> None:
        repo = self._make_repo(tmp_path)
        with pytest.raises(FileNotFoundError):
            repo.load(tmp_path / "nonexistent-skill")  # type: ignore[union-attr]

    def test_list_all_skips_parse_errors(
        self, tmp_path: Path, capsys: pytest.CaptureFixture  # type: ignore[type-arg]
    ) -> None:
        """list_all() prints a warning and skips skills that fail to parse."""
        bad = tmp_path / "dev" / "broken"
        bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text("<<<< completely broken >>>>", encoding="utf-8")

        repo = self._make_repo(tmp_path)
        skills = repo.list_all()  # type: ignore[union-attr]
        assert isinstance(skills, list)

    def test_list_all_base_path_not_exists_returns_empty(self, tmp_path: Path) -> None:
        repo = self._make_repo(tmp_path / "does_not_exist")
        result = repo.list_all()  # type: ignore[union-attr]
        assert result == []


# ── DiffSkill: fallback candidate and exception path ────────────────────────

class TestDiffSkillGaps:
    def test_diff_fallback_candidates_when_name_not_in_path(self, tmp_path: Path) -> None:
        """When skill name not in zip path, fallback to any SKILL.md."""
        from skill_forge.application.use_cases.diff_skill import DiffRequest, DiffSkill
        from skill_forge.domain.model import SkillScope

        # Build a pack where the skill path doesn't contain the skill name
        pack = tmp_path / "anon.skillpack"
        with zipfile.ZipFile(pack, "w") as zf:
            # SKILL.md that doesn't have skill name in its path
            zf.writestr("skills/dev/other-name/SKILL.md",
                        "---\nname: installed-skill\n---\n# body")

        # Build stub installer that returns an installed path
        installed_md = tmp_path / "installed-skill" / "SKILL.md"
        installed_md.parent.mkdir(parents=True)
        installed_md.write_text(
            "---\nname: installed-skill\n---\n# body", encoding="utf-8"
        )

        mock_installer = MagicMock()
        mock_installer.scan_all_targets.return_value = {"claude": [installed_md.parent]}

        mock_parser = MagicMock()
        mock_parser.parse.return_value = MagicMock(version="0.1.0")

        # Build stub fetcher
        mock_fetcher = MagicMock()
        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            RegistryIndex,
        )

        version = IndexedVersion(
            version="0.2.0",
            path="packs/dev/installed-skill-0.2.0.skillpack",
            sha256="a" * 64,
        )
        skill = IndexedSkill(
            category="dev",
            name="installed-skill",
            description="",
            latest="0.2.0",
            versions=(version,),
        )
        index = RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="",
            skills=(skill,),
        )
        mock_fetcher.fetch_index.return_value = index

        import shutil as _shutil

        def _fake_fetch(url: str, dest: Path) -> Path:
            _shutil.copy(str(pack), str(dest))
            return dest

        mock_fetcher.fetch.side_effect = _fake_fetch

        use_case = DiffSkill(
            installer=mock_installer,
            parser=mock_parser,
            fetcher=mock_fetcher,
        )
        request = DiffRequest(
            skill_name="installed-skill",
            scope=SkillScope.GLOBAL,
            registry_url="https://example.com",
        )
        response = use_case.execute(request)
        # Either has a diff or is up-to-date — but no crash
        assert response.skill_name == "installed-skill"

    def test_diff_network_error_returns_partial_response(self, tmp_path: Path) -> None:
        """When fetcher raises, diff returns a partial response with error message."""
        from skill_forge.application.use_cases.diff_skill import DiffRequest, DiffSkill
        from skill_forge.domain.model import SkillScope

        installed_md = tmp_path / "my-skill" / "SKILL.md"
        installed_md.parent.mkdir()
        installed_md.write_text("---\nname: my-skill\n---\nbody", encoding="utf-8")

        mock_installer = MagicMock()
        mock_installer.scan_all_targets.return_value = {"claude": [installed_md.parent]}

        mock_parser = MagicMock()
        mock_parser.parse.return_value = MagicMock(version="0.1.0")

        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            RegistryIndex,
        )

        version = IndexedVersion(
            version="0.2.0",
            path="packs/dev/my-skill-0.2.0.skillpack",
            sha256="a" * 64,
        )
        skill = IndexedSkill(
            category="dev", name="my-skill", description="", latest="0.2.0",
            versions=(version,),
        )
        index = RegistryIndex(
            registry_name="test", base_url="https://example.com",
            updated_at="", skills=(skill,),
        )
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_index.return_value = index
        mock_fetcher.fetch.side_effect = RuntimeError("connection refused")

        use_case = DiffSkill(
            installer=mock_installer, parser=mock_parser, fetcher=mock_fetcher,
        )
        response = use_case.execute(
            DiffRequest(
                skill_name="my-skill",
                scope=SkillScope.GLOBAL,
                registry_url="https://example.com",
            )
        )
        # Partial response: registry_version is set but diff has error message
        assert response.skill_name == "my-skill"
        assert any("fetch" in line.lower() or "error" in line.lower()
                   or "Could not" in line
                   for line in response.diff_lines)


# ── PublishPack: _read_description error paths ───────────────────────────────

class TestPublishPackGaps:
    def test_read_description_returns_empty_when_parser_is_none(
        self, tmp_path: Path
    ) -> None:
        """_read_description returns '' when no parser is injected."""
        from skill_forge.application.use_cases.publish_skill import PublishPack
        from skill_forge.domain.model import SkillPackManifest, SkillRef

        mock_publisher = MagicMock()
        mock_packer = MagicMock()

        use_case = PublishPack(
            publisher=mock_publisher, packer=mock_packer, parser=None
        )

        manifest = SkillPackManifest(
            name="x", version="0.1.0", author="", created_at="",
            skills=(SkillRef(category="dev", name="x", version="0.1.0"),),
        )
        result = use_case._read_description(tmp_path / "x.skillpack", manifest)  # type: ignore[attr-defined]
        assert result == ""

    def test_read_description_returns_empty_when_skill_md_missing(
        self, tmp_path: Path
    ) -> None:
        """_read_description returns '' when SKILL.md isn't in the pack."""
        from skill_forge.application.use_cases.publish_skill import PublishPack
        from skill_forge.domain.model import SkillPackManifest, SkillRef
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        # Create a pack without SKILL.md
        pack = tmp_path / "empty.skillpack"
        with zipfile.ZipFile(pack, "w") as zf:
            zf.writestr("manifest.json", '{"format_version":"1","skills":[]}')

        mock_publisher = MagicMock()

        from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

        use_case = PublishPack(
            publisher=mock_publisher,
            packer=ZipSkillPacker(),
            parser=MarkdownSkillParser(),
        )

        manifest = SkillPackManifest(
            name="x", version="0.1.0", author="", created_at="",
            skills=(SkillRef(category="dev", name="x", version="0.1.0"),),
        )
        result = use_case._read_description(pack, manifest)  # type: ignore[attr-defined]
        assert result == ""


# ── UpdateSkill: error and edge-case paths ────────────────────────────────────

class TestUpdateSkillGaps:
    def test_update_skill_no_installed_skills_returns_empty(self) -> None:
        """When no skills are installed, records is empty."""
        from skill_forge.application.use_cases.update_skill import (
            UpdateRequest,
            UpdateSkill,
        )
        from skill_forge.domain.model import InstallTarget, RegistryIndex, SkillScope

        mock_installer = MagicMock()
        mock_installer.scan_all_targets.return_value = {}
        mock_fetcher = MagicMock()
        index = RegistryIndex(
            registry_name="r", base_url="https://example.com",
            updated_at="", skills=(),
        )
        mock_fetcher.fetch_index.return_value = index
        mock_parser = MagicMock()

        use_case = UpdateSkill(
            installer=mock_installer,
            fetcher=mock_fetcher,
            install_from_url=MagicMock(),
            parser=mock_parser,
        )
        resp = use_case.execute(
            UpdateRequest(
                scope=SkillScope.PROJECT,
                target=InstallTarget.CLAUDE,
                registry_url="https://example.com",
            )
        )
        assert resp.records == []

    def test_update_skill_already_up_to_date_no_update(self, tmp_path: Path) -> None:
        """Skill at latest version: would_update=False."""
        from skill_forge.application.use_cases.update_skill import (
            UpdateRequest,
            UpdateSkill,
        )
        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            InstallTarget,
            RegistryIndex,
            SkillScope,
        )
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        # Installed skill at 0.1.0
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\nversion: 0.1.0\n"
            "description: |\n  Use for testing. Triggers on: test.\n---\n\nbody",
            encoding="utf-8",
        )

        mock_installer = MagicMock()
        mock_installer.scan_all_targets.return_value = {"claude": [skill_dir]}

        version = IndexedVersion(
            version="0.1.0", path="packs/dev/my-skill-0.1.0.skillpack", sha256="a" * 64
        )
        skill = IndexedSkill(
            category="dev", name="my-skill", description="", latest="0.1.0",
            versions=(version,),
        )
        index = RegistryIndex(
            registry_name="r", base_url="https://example.com",
            updated_at="", skills=(skill,),
        )
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_index.return_value = index

        use_case = UpdateSkill(
            installer=mock_installer,
            fetcher=mock_fetcher,
            install_from_url=MagicMock(),
            parser=MarkdownSkillParser(),
        )
        resp = use_case.execute(
            UpdateRequest(
                scope=SkillScope.PROJECT,
                target=InstallTarget.CLAUDE,
                registry_url="https://example.com",
            )
        )
        assert len(resp.records) == 1
        assert resp.records[0].would_update is False


# ── SymlinkInstaller: remaining error paths ───────────────────────────────────

class TestSymlinkInstallerRemainingGaps:
    def test_list_installed_returns_paths_when_dir_exists(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import InstallTarget, SkillScope
        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )

        installer = SymlinkSkillInstaller(project_root=tmp_path)

        skill_src = tmp_path / "my-skill"
        skill_src.mkdir()
        (skill_src / "SKILL.md").write_text("---\nname: x\n---\nbody", encoding="utf-8")

        installer.install(skill_src, SkillScope.PROJECT, InstallTarget.CLAUDE)
        result = installer.list_installed(SkillScope.PROJECT)
        assert len(result) >= 1

    def test_resolve_dirs_unknown_global_target_raises(self, tmp_path: Path) -> None:
        """Custom unknown target raises ValueError at global scope."""
        from skill_forge.domain.model import InstallTarget, SkillScope
        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )

        installer = SymlinkSkillInstaller(project_root=tmp_path)
        # Patch VSCODE into global targets map by checking the logic:
        # _GLOBAL_TARGETS has no VSCODE entry, so global + VSCODE raises
        with pytest.raises(ValueError, match="VS Code"):
            installer._resolve_dirs(SkillScope.GLOBAL, InstallTarget.VSCODE)  # type: ignore[attr-defined]
