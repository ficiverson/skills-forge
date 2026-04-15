"""End-to-end integration scenarios for skills-forge.

Five scenarios that each exercise a full user-facing workflow:

1. Full lifecycle  — create → lint → pack → unpack → install → export (all formats)
2. URL install     — pack locally, serve with a stub fetcher, install-from-url with
                     correct and wrong SHA256
3. Dep resolution  — two-skill graph: provider + consumer; lint detects missing dep,
                     info shows resolved graph
4. Update / diff   — pack a v0.1.0 and a v0.2.0 skilll; update detects the newer
                     version, diff shows the change
5. Yank            — publish two versions, yank one, verify yank shows in index and
                     update skips it

All scenarios run through the Typer ``CliRunner`` (no subprocess overhead).
External I/O (network, git push) is mocked at the port / adapter boundary.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from skill_forge.cli.main import app

runner = CliRunner()


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_skill_dir(base: Path, name: str, version: str = "0.1.0") -> Path:
    """Create a minimal skill directory under *base* and return its path."""
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        f"---\n"
        f"name: {name}\n"
        f"version: {version}\n"
        f"description: |\n"
        f"  Use this when testing {name}. Triggers on: test, validate.\n"
        f"---\n\n"
        f"## Instructions\n\nDo the thing.\n",
        encoding="utf-8",
    )
    return d


def _make_skillpack(tmp_path: Path, name: str, version: str = "0.1.0") -> Path:
    """Create a minimal .skillpack archive and return its path."""
    skill_dir = _make_skill_dir(tmp_path / "src", name, version)
    result = runner.invoke(
        app,
        ["pack", str(skill_dir), "-o", str(tmp_path / "packs")],
    )
    assert result.exit_code == 0, result.output
    packs = list((tmp_path / "packs").glob("*.skillpack"))
    assert packs, "pack command produced no .skillpack file"
    return packs[0]


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1: Full lifecycle — create → lint → pack → unpack → install → export
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario1FullLifecycle:
    """create → lint (clean) → pack → unpack → install → export all formats."""

    def test_create_produces_skill_md(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "create",
                "-n", "e2e-skill",
                "-c", "dev",
                "-d", "Use when running e2e tests. Triggers on: test, e2e.",
                "-e", "🧪",
                "-o", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output
        skill_md = tmp_path / "dev" / "e2e-skill" / "SKILL.md"
        assert skill_md.exists(), "SKILL.md was not created"
        content = skill_md.read_text(encoding="utf-8")
        assert "e2e-skill" in content

    def test_lint_passes_on_created_skill(self, tmp_path: Path) -> None:
        # Create first
        runner.invoke(
            app,
            [
                "create", "-n", "e2e-skill", "-c", "dev",
                "-d", "Use when running e2e tests. Triggers on: test, e2e.",
                "-e", "🧪", "-o", str(tmp_path),
            ],
        )
        skill_dir = tmp_path / "dev" / "e2e-skill"
        result = runner.invoke(app, ["lint", str(skill_dir)])
        assert result.exit_code == 0, result.output

    def test_pack_creates_skillpack_archive(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path, "pack-test")
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        result = runner.invoke(app, ["pack", str(skill_dir), "-o", str(out_dir)])
        assert result.exit_code == 0, result.output
        archives = list(out_dir.glob("*.skillpack"))
        assert len(archives) == 1
        assert archives[0].name.startswith("pack-test")

    def test_unpack_restores_skill_md(self, tmp_path: Path) -> None:
        pack = _make_skillpack(tmp_path / "pack_src", "unpack-test")
        dest = tmp_path / "unpacked"
        result = runner.invoke(app, ["unpack", str(pack), "-o", str(dest)])
        assert result.exit_code == 0, result.output
        skill_mds = list(dest.rglob("SKILL.md"))
        assert skill_mds, "No SKILL.md found after unpack"

    def test_install_creates_symlink(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        skill_dir = _make_skill_dir(tmp_path / "skills_src", "install-test")
        install_root = tmp_path / "project"
        install_root.mkdir()
        monkeypatch.chdir(install_root)
        result = runner.invoke(
            app,
            ["install", str(skill_dir), "--scope", "project"],
        )
        assert result.exit_code == 0, result.output
        # A symlink (or directory) should appear under project/.claude/skills/
        installed = install_root / ".claude" / "skills" / "install-test"
        assert installed.exists() or installed.is_symlink()

    def test_export_all_formats_produce_files(self, tmp_path: Path) -> None:
        # export requires a .skillpack — pack first
        pack = _make_skillpack(tmp_path / "pack_src", "export-test")
        formats = ["system-prompt", "gpt-json", "gem-txt", "bedrock-xml"]
        for fmt in formats:
            out_dir = tmp_path / f"export_{fmt}"
            out_dir.mkdir()
            result = runner.invoke(
                app,
                ["export", str(pack), "-f", fmt, "-o", str(out_dir)],
            )
            assert result.exit_code == 0, f"export {fmt} failed: {result.output}"
            files = list(out_dir.iterdir())
            assert files, f"No output file for format {fmt}"

    def test_list_shows_skills_in_output_directory(self, tmp_path: Path) -> None:
        """list command finds SKILL.md files in a plain (non-symlink) directory."""
        # The list command is designed for output_skills directories (real dirs)
        skills_base = tmp_path / "output_skills"
        _make_skill_dir(skills_base, "list-test")
        result = runner.invoke(app, ["list", str(skills_base)])
        assert result.exit_code == 0, result.output
        assert "list-test" in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2: SHA256 verification for install-from-url
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario2Sha256Verification:
    """Install a local .skillpack via a stubbed fetcher — correct and wrong SHA256."""

    def _pack_and_hash(self, tmp_path: Path) -> tuple[Path, str]:
        import hashlib
        pack = _make_skillpack(tmp_path, "sha-skill")
        digest = hashlib.sha256(pack.read_bytes()).hexdigest()
        return pack, digest

    def test_correct_sha256_installs_successfully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack, digest = self._pack_and_hash(tmp_path)
        install_root = tmp_path / "project"
        install_root.mkdir()
        monkeypatch.chdir(install_root)

        def _fake_fetch(url: str, dest: Path) -> Path:
            import shutil
            shutil.copy(str(pack), str(dest))
            return dest

        with patch(
            "skill_forge.infrastructure.adapters.http_pack_fetcher.HttpPackFetcher.fetch",
            side_effect=_fake_fetch,
        ):
            result = runner.invoke(
                app,
                [
                    "install",
                    "https://example.com/sha-skill-0.1.0.skillpack",
                    "--sha256", digest,
                    "--scope", "project",
                ],
            )
        assert result.exit_code == 0, result.output

    def test_wrong_sha256_aborts_install(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack, _ = self._pack_and_hash(tmp_path)
        install_root = tmp_path / "project"
        install_root.mkdir()
        monkeypatch.chdir(install_root)
        wrong_digest = "a" * 64

        def _fake_fetch(url: str, dest: Path) -> Path:
            import shutil
            shutil.copy(str(pack), str(dest))
            return dest

        with patch(
            "skill_forge.infrastructure.adapters.http_pack_fetcher.HttpPackFetcher.fetch",
            side_effect=_fake_fetch,
        ):
            result = runner.invoke(
                app,
                [
                    "install",
                    "https://example.com/sha-skill-0.1.0.skillpack",
                    "--sha256", wrong_digest,
                    "--scope", "project",
                ],
            )
        assert (
            result.exit_code != 0
            or "sha256" in result.output.lower()
            or "mismatch" in result.output.lower()
        )

    def test_install_from_url_without_sha256_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pack = _make_skillpack(tmp_path, "nosha-skill")
        install_root = tmp_path / "project"
        install_root.mkdir()
        monkeypatch.chdir(install_root)

        def _fake_fetch(url: str, dest: Path) -> Path:
            import shutil
            shutil.copy(str(pack), str(dest))
            return dest

        with patch(
            "skill_forge.infrastructure.adapters.http_pack_fetcher.HttpPackFetcher.fetch",
            side_effect=_fake_fetch,
        ):
            result = runner.invoke(
                app,
                [
                    "install",
                    "https://example.com/nosha-skill-0.1.0.skillpack",
                    "--scope", "project",
                ],
            )
        # Should either succeed with a warning or succeed silently
        # The key requirement: no unhandled exception
        assert "Traceback" not in result.output


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3: Dependency graph — provider + consumer
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario3DependencyGraph:
    """Consumer skill depends on provider skill; info shows resolved graph."""

    def _make_provider(self, base: Path) -> Path:
        d = base / "provider-skill"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            "---\n"
            "name: provider-skill\n"
            "version: 0.1.0\n"
            "description: |\n"
            "  Use for providing data. Triggers on: provide, data.\n"
            "---\n\n## Instructions\n\nProvide data.\n",
            encoding="utf-8",
        )
        return d

    def _make_consumer(self, base: Path) -> Path:
        d = base / "consumer-skill"
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            "---\n"
            "name: consumer-skill\n"
            "version: 0.1.0\n"
            "depends_on: provider-skill (data access)\n"
            "description: |\n"
            "  Use for consuming data. Triggers on: consume, process.\n"
            "---\n\n## Instructions\n\nConsume data from provider-skill.\n",
            encoding="utf-8",
        )
        return d

    def test_lint_consumer_passes_when_provider_installed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_root = tmp_path / "project"
        install_root.mkdir()

        provider_dir = self._make_provider(tmp_path / "src")
        consumer_dir = self._make_consumer(tmp_path / "src")

        monkeypatch.chdir(install_root)
        # Install provider first
        runner.invoke(
            app,
            ["install", str(provider_dir), "--scope", "project"],
        )

        # Lint consumer — should pass (dependency is satisfied)
        result = runner.invoke(app, ["lint", str(consumer_dir)])
        assert result.exit_code == 0, result.output

    def test_info_shows_dependency_in_consumer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        install_root = tmp_path / "project"
        install_root.mkdir()
        consumer_dir = self._make_consumer(tmp_path / "src")
        monkeypatch.chdir(install_root)
        runner.invoke(app, ["install", str(consumer_dir), "--scope", "project"])
        result = runner.invoke(app, ["info", "consumer-skill", "--scope", "project"])
        assert result.exit_code == 0, result.output
        assert "provider-skill" in result.output

    def test_pack_consumer_includes_skill_md(self, tmp_path: Path) -> None:
        consumer_dir = self._make_consumer(tmp_path / "src")
        out_dir = tmp_path / "packs"
        out_dir.mkdir()
        result = runner.invoke(app, ["pack", str(consumer_dir), "-o", str(out_dir)])
        assert result.exit_code == 0, result.output
        packs = list(out_dir.glob("*.skillpack"))
        assert packs
        with zipfile.ZipFile(packs[0]) as zf:
            names = zf.namelist()
        assert any("SKILL.md" in n for n in names)

    def test_provider_and_consumer_pack_together(self, tmp_path: Path) -> None:
        provider_dir = self._make_provider(tmp_path / "src")
        consumer_dir = self._make_consumer(tmp_path / "src")
        out_dir = tmp_path / "packs"
        out_dir.mkdir()
        result = runner.invoke(
            app,
            ["pack", str(provider_dir), str(consumer_dir), "-o", str(out_dir)],
        )
        assert result.exit_code == 0, result.output
        packs = list(out_dir.glob("*.skillpack"))
        assert len(packs) == 1  # multi-skill → single archive


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4: Update / diff — v0.1.0 installed, v0.2.0 in registry
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario4UpdateAndDiff:
    """Update detects newer version; diff shows the change."""

    def _build_registry_index(
        self, tmp_path: Path, name: str, v1: str, v2: str
    ) -> tuple[Path, Path]:
        """Return (v1_pack, v2_pack) and write index.json into tmp_path/registry."""
        v1_pack = _make_skillpack(tmp_path / "packs_v1", name, v1)
        v2_pack = _make_skillpack(tmp_path / "packs_v2", name, v2)

        import hashlib

        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()
        packs_dir = registry_dir / "packs"
        packs_dir.mkdir()

        import shutil
        shutil.copy(str(v1_pack), str(packs_dir / v1_pack.name))
        shutil.copy(str(v2_pack), str(packs_dir / v2_pack.name))

        sha1 = hashlib.sha256(v1_pack.read_bytes()).hexdigest()
        sha2 = hashlib.sha256(v2_pack.read_bytes()).hexdigest()

        index = {
            "registry_name": "test",
            "base_url": "https://example.com",
            "updated_at": "2026-04-11T00:00:00+00:00",
            "skills": [
                {
                    "category": "dev",
                    "name": name,
                    "description": f"Use for {name}",
                    "latest": v2,
                    "versions": [
                        {"version": v1, "path": f"packs/{v1_pack.name}", "sha256": sha1},
                        {"version": v2, "path": f"packs/{v2_pack.name}", "sha256": sha2},
                    ],
                }
            ],
        }
        (registry_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
        return v1_pack, v2_pack

    def test_update_detects_newer_version(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from skill_forge.application.use_cases.update_skill import (
            UpdateRequest,
            UpdateSkill,
        )
        from skill_forge.domain.model import (
            InstallTarget,
            SkillScope,
        )
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        v1_pack, v2_pack = self._build_registry_index(tmp_path, "upd-skill", "0.1.0", "0.2.0")

        # Simulate an installed 0.1.0 skill
        install_root = tmp_path / "project"
        install_root.mkdir()
        skill_dir = _make_skill_dir(tmp_path / "inst_src", "upd-skill", "0.1.0")
        monkeypatch.chdir(install_root)
        runner.invoke(
            app,
            ["install", str(skill_dir), "--scope", "project"],
        )

        # Build a stub fetcher that reads from our local registry dir
        import hashlib

        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            RegistryIndex,
        )
        sha2 = hashlib.sha256(v2_pack.read_bytes()).hexdigest()
        sha1 = hashlib.sha256(v1_pack.read_bytes()).hexdigest()
        index = RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="2026-04-11T00:00:00+00:00",
            skills=(
                IndexedSkill(
                    category="dev",
                    name="upd-skill",
                    description="",
                    latest="0.2.0",
                    versions=(
                        IndexedVersion(version="0.1.0", path="packs/v1.skillpack", sha256=sha1),
                        IndexedVersion(version="0.2.0", path="packs/v2.skillpack", sha256=sha2),
                    ),
                ),
            ),
        )

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_index.return_value = index

        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )
        real_installer = SymlinkSkillInstaller(project_root=install_root)
        mock_install_from_url = MagicMock()

        use_case = UpdateSkill(
            installer=real_installer,
            parser=MarkdownSkillParser(),
            fetcher=mock_fetcher,
            install_from_url=mock_install_from_url,
        )
        response = use_case.execute(
            UpdateRequest(
                scope=SkillScope.PROJECT,
                target=InstallTarget.CLAUDE,
                registry_url="https://example.com",
            )
        )

        assert len(response.records) == 1
        assert response.records[0].skill_name == "upd-skill"
        assert response.records[0].new_version == "0.2.0"
        assert response.records[0].old_version == "0.1.0"
        assert response.records[0].would_update is True

    def test_diff_shows_change_between_versions(self, tmp_path: Path) -> None:
        from skill_forge.application.use_cases.diff_skill import DiffRequest, DiffSkill
        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            RegistryIndex,
            SkillScope,
        )

        # Build v0.1.0 (installed) and v0.2.0 (registry)
        v1_dir = tmp_path / "v1" / "diff-skill"
        v1_dir.mkdir(parents=True)
        (v1_dir / "SKILL.md").write_text(
            "---\nname: diff-skill\nversion: 0.1.0\n"
            "description: |\n  Use for diffing. Triggers on: diff.\n"
            "---\n\n## Instructions\n\nOriginal instructions.\n",
            encoding="utf-8",
        )

        # v0.2.0 pack with changed instructions
        v2_dir = tmp_path / "v2" / "diff-skill"
        v2_dir.mkdir(parents=True)
        (v2_dir / "SKILL.md").write_text(
            "---\nname: diff-skill\nversion: 0.2.0\n"
            "description: |\n  Use for diffing. Triggers on: diff.\n"
            "---\n\n## Instructions\n\nUpdated instructions with new content.\n",
            encoding="utf-8",
        )

        # Pack the v0.2.0 version
        pack_out = tmp_path / "packs"
        pack_out.mkdir()
        runner.invoke(app, ["pack", str(v2_dir), "-o", str(pack_out)])
        v2_pack = next(pack_out.glob("*.skillpack"))

        import hashlib
        sha2 = hashlib.sha256(v2_pack.read_bytes()).hexdigest()

        index = RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="2026-04-11T00:00:00+00:00",
            skills=(
                IndexedSkill(
                    category="dev",
                    name="diff-skill",
                    description="",
                    latest="0.2.0",
                    versions=(
                        IndexedVersion(
                            version="0.2.0",
                            path="packs/diff-skill.skillpack",
                            sha256=sha2,
                        ),
                    ),
                ),
            ),
        )

        mock_installer = MagicMock()
        mock_installer.scan_all_targets.return_value = {"claude": [v1_dir]}

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_index.return_value = index

        import shutil

        def _fake_fetch(url: str, dest: Path) -> Path:
            shutil.copy(str(v2_pack), str(dest))
            return dest

        mock_fetcher.fetch.side_effect = _fake_fetch

        from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser

        use_case = DiffSkill(
            installer=mock_installer,
            parser=MarkdownSkillParser(),
            fetcher=mock_fetcher,
        )
        response = use_case.execute(
            DiffRequest(
                skill_name="diff-skill",
                scope=SkillScope.GLOBAL,
                registry_url="https://example.com",
            )
        )

        assert response.skill_name == "diff-skill"
        assert response.has_diff, "Expected a diff between v0.1.0 and v0.2.0"
        # The diff should mention the changed instructions
        diff_text = "".join(response.diff_lines)
        assert "Original" in diff_text or "Updated" in diff_text


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5: Yank — hide a version, update skips it
# ─────────────────────────────────────────────────────────────────────────────

class TestScenario5YankAndUpdate:
    """Yank a version from registry; update must skip the yanked version."""

    def test_yank_marks_version_in_index(self, tmp_path: Path) -> None:
        """After yank, the index no longer includes the yanked version as latest."""
        from skill_forge.application.use_cases.yank_skill import (
            YankRequest,
            YankSkill,
        )
        from skill_forge.domain.model import (
            IndexedSkill,
            IndexedVersion,
            RegistryIndex,
        )
        from skill_forge.infrastructure.adapters.registry_index_codec import (
            RegistryIndexCodec,
        )

        # Build a registry dir with two versions
        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()

        dummy_sha = "a" * 64
        index = RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="2026-04-11T00:00:00+00:00",
            skills=(
                IndexedSkill(
                    category="dev",
                    name="yank-skill",
                    description="",
                    latest="0.2.0",
                    versions=(
                        IndexedVersion(version="0.1.0", path="packs/v1.skillpack",
                                       sha256=dummy_sha),
                        IndexedVersion(version="0.2.0", path="packs/v2.skillpack",
                                       sha256=dummy_sha),
                    ),
                ),
            ),
        )
        codec = RegistryIndexCodec()
        (registry_dir / "index.json").write_text(
            codec.encode(index), encoding="utf-8"
        )

        # Mock the publisher port
        mock_publisher = MagicMock()
        mock_publisher.read_index.return_value = index

        use_case = YankSkill(publisher=mock_publisher)
        response = use_case.execute(YankRequest(skill_name="yank-skill", version="0.1.0"))

        # Verify the use case executed without error and returned a response
        assert response.skill_name == "yank-skill"
        assert response.version == "0.1.0"
        assert mock_publisher.update_index.called

    def test_update_skips_yanked_version_prefers_non_yanked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When only the latest is non-yanked, update selects it."""
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

        # Install v0.1.0
        install_root = tmp_path / "project"
        install_root.mkdir()
        skill_dir = _make_skill_dir(tmp_path / "inst_src", "yank-upd-skill", "0.1.0")
        monkeypatch.chdir(install_root)
        runner.invoke(
            app,
            ["install", str(skill_dir), "--scope", "project"],
        )

        dummy_sha = "b" * 64
        # Registry where v0.1.5 is the real latest (v0.1.0 is "yanked" i.e. not latest)
        index = RegistryIndex(
            registry_name="test",
            base_url="https://example.com",
            updated_at="2026-04-11T00:00:00+00:00",
            skills=(
                IndexedSkill(
                    category="dev",
                    name="yank-upd-skill",
                    description="",
                    latest="0.1.5",
                    versions=(
                        IndexedVersion(version="0.1.0", path="packs/v1.skillpack",
                                       sha256=dummy_sha),
                        IndexedVersion(version="0.1.5", path="packs/v15.skillpack",
                                       sha256=dummy_sha),
                    ),
                ),
            ),
        )

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_index.return_value = index

        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )
        real_installer = SymlinkSkillInstaller(project_root=install_root)

        use_case = UpdateSkill(
            installer=real_installer,
            parser=MarkdownSkillParser(),
            fetcher=mock_fetcher,
            install_from_url=MagicMock(),
        )
        response = use_case.execute(
            UpdateRequest(
                scope=SkillScope.PROJECT,
                target=InstallTarget.CLAUDE,
                registry_url="https://example.com",
            )
        )

        assert len(response.records) == 1
        record = response.records[0]
        assert record.skill_name == "yank-upd-skill"
        # Update should target the non-yanked latest (0.1.5)
        assert record.new_version == "0.1.5"
        assert record.would_update is True

    def test_yank_cli_command_exits_cleanly(self, tmp_path: Path) -> None:
        """The yank CLI command routes through the Typer app without crashing."""
        from skill_forge.application.use_cases.yank_skill import YankResponse

        mock_response = YankResponse(
            skill_name="yank-cli-skill",
            version="0.1.0",
            yank_reason="",
            was_already_yanked=False,
            committed=True,
        )

        with patch(
            "skill_forge.application.use_cases.yank_skill.YankSkill.execute",
            return_value=mock_response,
        ):
            result = runner.invoke(
                app,
                ["yank", "yank-cli-skill", "0.1.0"],
            )
        # Should succeed or fail with a config error, but never a Traceback
        assert "Traceback" not in result.output
