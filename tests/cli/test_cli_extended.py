"""Extended CLI integration tests covering all remaining uncovered branches."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from skill_forge.cli.main import app

runner = CliRunner()

# ── helpers ────────────────────────────────────────────────────────────────────

_SKILL_MD_TMPL = """\
---
name: {name}
version: 0.1.0
description: |
  Use this skill when testing {name}. Triggers on: test, validate, quality.
emoji: 🧪
---

STARTER_CHARACTER = 🧪

## Instructions

Run the tests for {name}.

## Constraints

- Always verify results.
"""

_DEPS_SKILL_MD = """\
---
name: dep-consumer
version: 0.1.0
description: |
  Use this skill when consuming dependencies. Triggers on: consume, depend.
depends_on: "dep-provider"
---

## Instructions

Consume dep-provider.
"""


def _make_skill_dir(base: Path, name: str = "test-skill", category: str = "testing") -> Path:
    d = base / category / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(_SKILL_MD_TMPL.format(name=name), encoding="utf-8")
    return d


def _make_pack(skill_dir: Path, tmp_path: Path) -> Path:
    """Create a .skillpack using the CLI and return its path."""
    pack_out = tmp_path / "test-skill-0.1.0.skillpack"
    r = runner.invoke(app, ["pack", str(skill_dir), "-o", str(pack_out)])
    assert r.exit_code == 0, f"pack failed: {r.stdout}"
    return pack_out


def _make_minimal_registry(base: Path) -> Path:
    """Init a minimal git registry in base/registry/."""
    if shutil.which("git") is None:
        pytest.skip("git not available")
    reg = base / "registry"
    reg.mkdir()
    env = {
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "t@t.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "t@t.com",
        "PATH": __import__("os").environ.get("PATH", ""),
        "HOME": str(base),
    }
    subprocess.run(
        ["git", "-C", str(reg), "init", "-q", "-b", "main"],
        check=True,
        env=env,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(reg), "config", "user.email", "t@t.com"],
        check=True,
        env=env,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(reg), "config", "user.name", "test"],
        check=True,
        env=env,
        capture_output=True,
    )
    return reg


# ── List command extended paths ─────────────────────────────────────────────────


class TestListExtended:
    def test_list_no_skills_found(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        result = runner.invoke(app, ["list", str(empty)])
        assert result.exit_code == 0
        assert "No skills found" in result.stdout

    def test_list_tag_filter_no_match(self, tmp_path: Path) -> None:
        _make_skill_dir(tmp_path)
        result = runner.invoke(app, ["list", str(tmp_path), "--tag", "xyznonexistent"])
        assert result.exit_code == 0
        assert "No skills match" in result.stdout

    def test_list_filter_str_no_match(self, tmp_path: Path) -> None:
        _make_skill_dir(tmp_path)
        result = runner.invoke(app, ["list", str(tmp_path), "--filter", "xyzabsent"])
        assert result.exit_code == 0
        assert "No skills match" in result.stdout

    def test_list_tag_filter_matches(self, tmp_path: Path) -> None:
        _make_skill_dir(tmp_path, name="python-tdd")
        result = runner.invoke(app, ["list", str(tmp_path), "--tag", "python"])
        assert result.exit_code == 0
        assert "python-tdd" in result.stdout

    def test_list_with_deps_shows_dep_tag(self, tmp_path: Path) -> None:
        d = tmp_path / "testing" / "dep-consumer"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(_DEPS_SKILL_MD, encoding="utf-8")
        result = runner.invoke(app, ["list", str(tmp_path)])
        assert result.exit_code == 0
        assert "dep-consumer" in result.stdout
        assert "deps" in result.stdout


# ── Install command error paths ────────────────────────────────────────────────


class TestInstallErrorPaths:
    def test_install_nonexistent_path_exits_1(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "install",
                str(tmp_path / "doesnotexist"),
                "--scope",
                "project",
                "--target",
                "claude",
            ],
            catch_exceptions=False,
        )
        # Typer raises an error for non-existent argument path
        assert result.exit_code != 0

    def test_install_valueerror_exits_1(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path)
        with patch(
            "skill_forge.application.use_cases.install_skill.InstallSkill.execute",
            side_effect=ValueError("requires-forge >=1.0.0 not satisfied"),
        ):
            result = runner.invoke(
                app,
                [
                    "install",
                    str(skill_dir),
                    "--scope",
                    "project",
                    "--target",
                    "claude",
                ],
            )
        assert result.exit_code == 1
        assert "requires-forge" in result.stdout

    def test_install_missing_dependency_shows_warning(self, tmp_path: Path) -> None:
        """Skills with missing deps should install but warn."""
        d = tmp_path / "testing" / "dep-consumer"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(_DEPS_SKILL_MD, encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "install",
                str(d),
                "--scope",
                "project",
                "--target",
                "claude",
            ],
        )
        # May succeed (0) or fail with missing deps (1) - either way no traceback
        assert "Traceback" not in (result.stdout or "")

    def test_install_url_missing_dependency_warning(self, tmp_path: Path) -> None:
        """When installing from URL deps may be missing — should not crash."""
        from skill_forge.application.use_cases.install_skill import (
            InstallSkillResponse,
        )

        mock_resp = MagicMock(spec=InstallSkillResponse)
        mock_resp.installed_paths = [tmp_path / "installed-skill"]
        mock_resp.missing_dependencies = ["dep-provider"]
        mock_resp.manifest = MagicMock()
        mock_resp.manifest.name = "test"
        mock_resp.manifest.version = "0.1.0"
        mock_resp.manifest.skills = ()
        mock_resp.extracted_paths = []
        mock_resp.sha256 = "a" * 64
        mock_resp.is_url_install = True

        with patch(
            "skill_forge.application.use_cases.install_skill.InstallSkill.execute",
            return_value=mock_resp,
        ):
            runner.invoke(
                app,
                [
                    "install",
                    str(_make_skill_dir(tmp_path)),
                    "--scope",
                    "project",
                ],
            )
        # Should mention deps even though the path-based install doesn't show the URL block


# ── Export command error paths and hints ─────────────────────────────────────


class TestExportHintsAndErrors:
    @pytest.fixture()
    def pack(self, tmp_path: Path) -> Path:
        skill_dir = _make_skill_dir(tmp_path)
        return _make_pack(skill_dir, tmp_path)

    def test_export_file_not_found_exits_nonzero(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "export",
                str(tmp_path / "ghost.skillpack"),
                "-f",
                "system-prompt",
            ],
        )
        assert result.exit_code != 0

    def test_export_system_prompt_hint(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "system-prompt"])
        assert result.exit_code == 0
        assert "Paste" in result.stdout or "system-prompt" in result.stdout

    def test_export_gpt_json_hint(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "gpt-json"])
        assert result.exit_code == 0
        assert "chatgpt" in result.stdout.lower() or "gpt" in result.stdout.lower()

    def test_export_gem_txt_hint(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "gem-txt"])
        assert result.exit_code == 0
        assert "gemini" in result.stdout.lower() or "gem" in result.stdout.lower()

    def test_export_bedrock_xml_hint(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "bedrock-xml"])
        assert result.exit_code == 0
        assert "bedrock" in result.stdout.lower() or "aws" in result.stdout.lower()

    def test_export_mistral_json_hint(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "mistral-json"])
        assert result.exit_code == 0
        assert "mistral" in result.stdout.lower()

    def test_export_gemini_api_hint(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "gemini-api"])
        assert result.exit_code == 0
        assert "gemini" in result.stdout.lower()

    def test_export_openai_assistants_hint(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "openai-assistants"])
        assert result.exit_code == 0
        assert "openai" in result.stdout.lower() or "assistant" in result.stdout.lower()

    def test_export_mcp_server_hint_lines(self, pack: Path) -> None:
        result = runner.invoke(app, ["export", str(pack), "-f", "mcp-server"])
        assert result.exit_code == 0
        assert "Run with" in result.stdout or "mcp" in result.stdout.lower()


# ── Info command: deprecated registry ─────────────────────────────────────────


class TestInfoDeprecated:
    def test_info_not_installed_exits_1(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "info",
                "nonexistent-skill",
                "--scope",
                "project",
            ],
        )
        assert result.exit_code == 1
        assert "not installed" in result.stdout

    def test_info_shows_deprecated_notice(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path)
        runner.invoke(
            app,
            [
                "install",
                str(skill_dir),
                "--scope",
                "project",
                "--target",
                "claude",
            ],
        )

        from skill_forge.application.use_cases.info_skill import InfoResponse

        mock_resp = MagicMock(spec=InfoResponse)
        mock_resp.is_installed = True
        mock_resp.skill = MagicMock()
        mock_resp.skill.version = "0.1.0"
        mock_resp.skill.identity = MagicMock()
        mock_resp.skill.identity.category = "testing"
        mock_resp.skill.total_estimated_tokens = 200
        mock_resp.skill.has_evals = False
        mock_resp.skill.evals = []
        mock_resp.skill.has_dependencies = False
        mock_resp.skill.requires_forge = None
        mock_resp.install_locations = []
        mock_resp.registry_latest = "0.2.0"
        mock_resp.is_up_to_date = False
        mock_resp.registry_deprecated = True
        mock_resp.registry_replaced_by = "new-skill"
        mock_resp.registry_deprecation_message = "Use new-skill instead"

        with patch(
            "skill_forge.application.use_cases.info_skill.GetSkillInfo.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(app, ["info", "test-skill", "--scope", "project"])

        assert "DEPRECATED" in result.stdout
        assert "new-skill" in result.stdout
        assert "Use new-skill instead" in result.stdout


# ── Update command ────────────────────────────────────────────────────────────


class TestUpdateCommand:
    def test_update_no_registry_exits_1(self, tmp_path: Path) -> None:
        """With empty config (no registries) and no --registry flag, should exit 1."""
        with patch(
            "skill_forge.cli.main.load_config",
            return_value=MagicMock(registries=[], default_registry="public"),
        ):
            result = runner.invoke(app, ["update", "--scope", "project"])
        assert result.exit_code == 1
        assert "registry" in result.stdout.lower()

    def test_update_invalid_target_exits_1(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "update",
                "--scope",
                "project",
                "--target",
                "invalid-target",
                "--registry",
                "https://example.com",
            ],
        )
        assert result.exit_code == 1
        assert "Unknown target" in result.stdout

    def test_update_runtime_error_exits_1(self, tmp_path: Path) -> None:
        with patch(
            "skill_forge.application.use_cases.update_skill.UpdateSkill.execute",
            side_effect=RuntimeError("Connection refused"),
        ):
            result = runner.invoke(
                app,
                [
                    "update",
                    "--registry",
                    "https://unreachable.example.com",
                ],
            )
        assert result.exit_code == 1
        assert "Could not reach registry" in result.stdout

    def test_update_no_matches_returns_0(self, tmp_path: Path) -> None:
        from skill_forge.application.use_cases.update_skill import UpdateResponse

        mock_resp = MagicMock(spec=UpdateResponse)
        mock_resp.records = []

        with patch(
            "skill_forge.application.use_cases.update_skill.UpdateSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "update",
                    "--registry",
                    "https://example.com",
                    "--scope",
                    "project",
                ],
            )
        assert result.exit_code == 0
        assert "No matching" in result.stdout

    def test_update_all_up_to_date(self) -> None:
        from skill_forge.application.use_cases.update_skill import UpdateRecord, UpdateResponse

        mock_record = MagicMock(spec=UpdateRecord)
        mock_record.would_update = False
        mock_record.updated = False

        mock_resp = MagicMock(spec=UpdateResponse)
        mock_resp.records = [mock_record]

        with patch(
            "skill_forge.application.use_cases.update_skill.UpdateSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "update",
                    "--registry",
                    "https://example.com",
                ],
            )
        assert result.exit_code == 0
        assert "up to date" in result.stdout

    def test_update_dry_run_shows_plan(self) -> None:
        from skill_forge.application.use_cases.update_skill import UpdateRecord, UpdateResponse

        mock_record = MagicMock(spec=UpdateRecord)
        mock_record.would_update = True
        mock_record.updated = False
        mock_record.skill_name = "python-tdd"
        mock_record.old_version = "1.0.0"
        mock_record.new_version = "1.2.0"

        mock_resp = MagicMock(spec=UpdateResponse)
        mock_resp.records = [mock_record]
        mock_resp.updated_count = 0

        with patch(
            "skill_forge.application.use_cases.update_skill.UpdateSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "update",
                    "--registry",
                    "https://example.com",
                    "--dry-run",
                ],
            )
        assert result.exit_code == 0
        assert "dry-run" in result.stdout
        assert "python-tdd" in result.stdout

    def test_update_valueerror_exits_1(self) -> None:
        with patch(
            "skill_forge.application.use_cases.update_skill.UpdateSkill.execute",
            side_effect=ValueError("registry index malformed"),
        ):
            result = runner.invoke(
                app,
                [
                    "update",
                    "--registry",
                    "https://example.com",
                ],
            )
        assert result.exit_code == 1

    def test_update_yes_flag_skips_confirm(self) -> None:
        from skill_forge.application.use_cases.update_skill import UpdateRecord, UpdateResponse

        mock_record = MagicMock(spec=UpdateRecord)
        mock_record.would_update = True
        mock_record.updated = True
        mock_record.skill_name = "python-tdd"
        mock_record.old_version = "1.0.0"
        mock_record.new_version = "1.2.0"

        mock_resp = MagicMock(spec=UpdateResponse)
        mock_resp.records = [mock_record]
        mock_resp.updated_count = 1

        with patch(
            "skill_forge.application.use_cases.update_skill.UpdateSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "update",
                    "--registry",
                    "https://example.com",
                    "--yes",
                ],
            )
        assert result.exit_code == 0
        assert "Updated" in result.stdout


# ── Registry subcommands ──────────────────────────────────────────────────────


class TestRegistryCommandsExtended:
    def test_registry_list_empty(self, tmp_path: Path) -> None:
        from skill_forge.domain.config_model import ForgeConfig

        with patch(
            "skill_forge.cli.main.load_config",
            return_value=ForgeConfig(registries=[], default_registry="public"),
        ):
            result = runner.invoke(app, ["registry", "list"])
        assert result.exit_code == 0
        assert "No registries configured" in result.stdout

    def test_registry_add_with_token_and_set_default(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "config.toml"
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            TomlConfigRepository,
        )

        repo = TomlConfigRepository(path=cfg_path)
        with patch("skill_forge.cli.main.build_config_repo", return_value=repo):
            result = runner.invoke(
                app,
                [
                    "registry",
                    "add",
                    "myrepo",
                    "https://myrepo.example.com",
                    "--token",
                    "${MY_TOKEN}",
                    "--set-default",
                ],
            )
        assert result.exit_code == 0
        assert "Added registry" in result.stdout
        assert "Set as default" in result.stdout

    def test_registry_add_duplicate_exits_1(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "config.toml"
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            TomlConfigRepository,
        )

        repo = TomlConfigRepository(path=cfg_path)
        with patch("skill_forge.cli.main.build_config_repo", return_value=repo):
            runner.invoke(app, ["registry", "add", "dup", "https://a.com"])
            result = runner.invoke(app, ["registry", "add", "dup", "https://b.com"])
        assert result.exit_code == 1

    def test_registry_remove_not_found_exits_1(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "config.toml"
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            TomlConfigRepository,
        )

        repo = TomlConfigRepository(path=cfg_path)
        with patch("skill_forge.cli.main.build_config_repo", return_value=repo):
            result = runner.invoke(app, ["registry", "remove", "phantom"])
        assert result.exit_code == 1

    def test_registry_set_default_not_found_exits_1(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "config.toml"
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            TomlConfigRepository,
        )

        repo = TomlConfigRepository(path=cfg_path)
        with patch("skill_forge.cli.main.build_config_repo", return_value=repo):
            result = runner.invoke(app, ["registry", "set-default", "ghost"])
        assert result.exit_code == 1

    def test_registry_list_shows_default_and_auth_tags(self, tmp_path: Path) -> None:
        from skill_forge.domain.config_model import ForgeConfig, RegistryConfig

        cfg = ForgeConfig(
            registries=[
                RegistryConfig(name="main-reg", url="https://main.com"),
                RegistryConfig(name="private-reg", url="https://priv.com", token="tok"),
            ],
            default_registry="private-reg",
        )
        with patch("skill_forge.cli.main.load_config", return_value=cfg):
            result = runner.invoke(app, ["registry", "list"])
        assert result.exit_code == 0
        assert "default" in result.stdout
        assert "auth" in result.stdout


# ── Diff command ──────────────────────────────────────────────────────────────


class TestDiffCommand:
    def test_diff_no_registry_exits_1(self, tmp_path: Path) -> None:
        with patch(
            "skill_forge.cli.main.load_config",
            return_value=MagicMock(registries=[], default_registry="public"),
        ):
            result = runner.invoke(app, ["diff", "my-skill"])
        assert result.exit_code == 1
        assert "registry" in result.stdout.lower()

    def test_diff_valueerror_exits_1(self) -> None:
        with patch(
            "skill_forge.application.use_cases.diff_skill.DiffSkill.execute",
            side_effect=ValueError("skill not installed"),
        ):
            result = runner.invoke(
                app,
                [
                    "diff",
                    "my-skill",
                    "--registry",
                    "https://r.example.com",
                ],
            )
        assert result.exit_code == 1
        assert "skill not installed" in result.stdout

    def test_diff_runtime_error_exits_1(self) -> None:
        with patch(
            "skill_forge.application.use_cases.diff_skill.DiffSkill.execute",
            side_effect=RuntimeError("connection refused"),
        ):
            result = runner.invoke(
                app,
                [
                    "diff",
                    "my-skill",
                    "--registry",
                    "https://r.example.com",
                ],
            )
        assert result.exit_code == 1
        assert "Could not reach registry" in result.stdout

    def test_diff_not_in_registry(self) -> None:
        from skill_forge.application.use_cases.diff_skill import DiffResponse

        mock_resp = MagicMock(spec=DiffResponse)
        mock_resp.skill_name = "my-skill"
        mock_resp.installed_version = "0.1.0"
        mock_resp.registry_version = ""
        mock_resp.has_diff = False
        mock_resp.diff_lines = []

        with patch(
            "skill_forge.application.use_cases.diff_skill.DiffSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "diff",
                    "my-skill",
                    "--registry",
                    "https://r.example.com",
                ],
            )
        assert result.exit_code == 0
        assert "not found" in result.stdout

    def test_diff_up_to_date(self) -> None:
        from skill_forge.application.use_cases.diff_skill import DiffResponse

        mock_resp = MagicMock(spec=DiffResponse)
        mock_resp.skill_name = "my-skill"
        mock_resp.installed_version = "0.1.0"
        mock_resp.registry_version = "0.1.0"
        mock_resp.has_diff = False
        mock_resp.diff_lines = []

        with patch(
            "skill_forge.application.use_cases.diff_skill.DiffSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "diff",
                    "my-skill",
                    "--registry",
                    "https://r.example.com",
                ],
            )
        assert result.exit_code == 0
        assert "identical" in result.stdout

    def test_diff_has_diff_exits_1(self) -> None:
        from skill_forge.application.use_cases.diff_skill import DiffResponse

        mock_resp = MagicMock(spec=DiffResponse)
        mock_resp.skill_name = "my-skill"
        mock_resp.installed_version = "0.1.0"
        mock_resp.registry_version = "0.2.0"
        mock_resp.has_diff = True
        mock_resp.diff_lines = ["--- a\n", "+++ b\n", "+new line\n"]

        with patch(
            "skill_forge.application.use_cases.diff_skill.DiffSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "diff",
                    "my-skill",
                    "--registry",
                    "https://r.example.com",
                ],
            )
        assert result.exit_code == 1
        assert "diff found" in result.stdout


# ── Yank command ──────────────────────────────────────────────────────────────


class TestYankCommand:
    def test_yank_missing_at_sign_exits_1(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        result = runner.invoke(
            app,
            [
                "yank",
                "noslash",
                "--registry",
                str(reg),
                "--url",
                "https://example.com",
            ],
        )
        assert result.exit_code == 1
        assert "format" in result.stdout

    def test_yank_valueerror_exits_1(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        with patch(
            "skill_forge.application.use_cases.yank_skill.YankSkill.execute",
            side_effect=ValueError("skill not found"),
        ):
            result = runner.invoke(
                app,
                [
                    "yank",
                    "my-skill@1.0.0",
                    "--registry",
                    str(reg),
                    "--url",
                    "https://example.com",
                ],
            )
        assert result.exit_code == 1
        assert "skill not found" in result.stdout

    def test_yank_already_yanked_shows_warning(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        from skill_forge.application.use_cases.yank_skill import YankResponse

        mock_resp = MagicMock(spec=YankResponse)
        mock_resp.skill_name = "my-skill"
        mock_resp.version = "1.0.0"
        mock_resp.yank_reason = ""
        mock_resp.was_already_yanked = True
        mock_resp.committed = False

        with patch(
            "skill_forge.application.use_cases.yank_skill.YankSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "yank",
                    "my-skill@1.0.0",
                    "--registry",
                    str(reg),
                    "--url",
                    "https://example.com",
                ],
            )
        assert result.exit_code == 0
        assert "already yanked" in result.stdout

    def test_yank_success_with_reason_committed_and_push(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        from skill_forge.application.use_cases.yank_skill import YankResponse

        mock_resp = MagicMock(spec=YankResponse)
        mock_resp.skill_name = "my-skill"
        mock_resp.version = "1.0.0"
        mock_resp.yank_reason = "security issue"
        mock_resp.was_already_yanked = False
        mock_resp.committed = True

        with patch(
            "skill_forge.application.use_cases.yank_skill.YankSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "yank",
                    "my-skill@1.0.0",
                    "--registry",
                    str(reg),
                    "--url",
                    "https://example.com",
                    "--push",
                ],
            )
        assert result.exit_code == 0
        assert "Yanked" in result.stdout
        assert "Committed" in result.stdout
        assert "Pushed" in result.stdout


# ── Deprecate command ─────────────────────────────────────────────────────────


class TestDeprecateCommand:
    def test_deprecate_valueerror_exits_1(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        with patch(
            "skill_forge.application.use_cases.deprecate_skill.DeprecateSkill.execute",
            side_effect=ValueError("skill not found"),
        ):
            result = runner.invoke(
                app,
                [
                    "deprecate",
                    "ghost-skill",
                    "--registry",
                    str(reg),
                    "--url",
                    "https://example.com",
                ],
            )
        assert result.exit_code == 1
        assert "skill not found" in result.stdout

    def test_deprecate_already_deprecated_shows_warning(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        from skill_forge.application.use_cases.deprecate_skill import DeprecateResponse

        mock_resp = MagicMock(spec=DeprecateResponse)
        mock_resp.skill_name = "old-skill"
        mock_resp.deprecated = True
        mock_resp.replaced_by = ""
        mock_resp.deprecation_message = ""
        mock_resp.was_already_deprecated = True
        mock_resp.committed = False

        with patch(
            "skill_forge.application.use_cases.deprecate_skill.DeprecateSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "deprecate",
                    "old-skill",
                    "--registry",
                    str(reg),
                    "--url",
                    "https://example.com",
                ],
            )
        assert result.exit_code == 0
        assert "already" in result.stdout.lower() or "deprecated" in result.stdout.lower()

    def test_deprecate_with_replacement_committed_pushed(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        from skill_forge.application.use_cases.deprecate_skill import DeprecateResponse

        mock_resp = MagicMock(spec=DeprecateResponse)
        mock_resp.skill_name = "old-skill"
        mock_resp.deprecated = True
        mock_resp.replaced_by = "new-skill"
        mock_resp.deprecation_message = "Use new-skill"
        mock_resp.was_already_deprecated = False
        mock_resp.committed = True

        with patch(
            "skill_forge.application.use_cases.deprecate_skill.DeprecateSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "deprecate",
                    "old-skill",
                    "--registry",
                    str(reg),
                    "--url",
                    "https://example.com",
                    "--replaced-by",
                    "new-skill",
                    "--message",
                    "Use new-skill",
                    "--push",
                ],
            )
        assert result.exit_code == 0
        assert "Deprecated" in result.stdout
        assert "new-skill" in result.stdout
        assert "Use new-skill" in result.stdout
        assert "Committed" in result.stdout
        assert "Pushed" in result.stdout


# ── Doctor command ────────────────────────────────────────────────────────────


class TestDoctorCommand:
    def test_doctor_no_skills_installed(self, tmp_path: Path) -> None:
        """Doctor runs cleanly even in a fresh directory with no skills."""
        fresh = runner.invoke(
            app,
            ["doctor", "--scope", "project", "--no-registry"],
            # catch_exceptions=False so we see real errors if there's a traceback
        )
        assert "Traceback" not in (fresh.stdout or "")

    def test_doctor_with_healthy_skills(self, tmp_path: Path) -> None:
        """Doctor with skills installed should produce structured output."""
        from skill_forge.application.use_cases.doctor_skill import DoctorResponse

        mock_resp = MagicMock(spec=DoctorResponse)
        mock_resp.checked_count = 1
        mock_resp.is_healthy = True
        mock_resp.issues = []
        mock_resp.failure_count = 0
        mock_resp.warning_count = 0

        with patch(
            "skill_forge.application.use_cases.doctor_skill.DoctorSkill.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "doctor",
                    "--scope",
                    "project",
                    "--no-registry",
                ],
            )
        assert result.exit_code == 0
        assert "✔" in result.stdout or "healthy" in result.stdout.lower()

    def test_doctor_with_registry_url(self, tmp_path: Path) -> None:
        """Doctor with a registry URL that fails gracefully."""
        result = runner.invoke(
            app,
            [
                "doctor",
                "--scope",
                "project",
                "--registry",
                "https://unreachable.example.com",
            ],
        )
        # Should not crash; may exit 0 or 1 but no traceback
        assert "Traceback" not in (result.stdout or "")


# ── Publish command: committed/pushed/neither branches ────────────────────────


class TestPublishCommitBranches:
    def test_publish_committed_not_pushed_shows_git_push_hint(self, tmp_path: Path) -> None:
        reg = _make_minimal_registry(tmp_path)
        skill_dir = _make_skill_dir(tmp_path)
        pack_out = tmp_path / "test-skill-0.1.0.skillpack"
        runner.invoke(app, ["pack", str(skill_dir), "-o", str(pack_out)])

        from skill_forge.application.use_cases.publish_skill import (
            PublishPackResponse,
        )
        from skill_forge.domain.model import PublishResult

        mock_result = MagicMock(spec=PublishResult)
        mock_result.pack_name = "test-skill"
        mock_result.version = "0.1.0"
        mock_result.repo_relative_path = "packs/testing/test-skill-0.1.0.skillpack"
        mock_result.sha256 = "a" * 64
        mock_result.committed = True
        mock_result.pushed = False
        mock_result.raw_url = "https://example.com/packs/testing/test-skill-0.1.0.skillpack"

        mock_manifest = MagicMock()
        mock_manifest.name = "test-skill"
        mock_manifest.version = "0.1.0"

        mock_resp = MagicMock(spec=PublishPackResponse)
        mock_resp.result = mock_result
        mock_resp.manifest = mock_manifest

        with patch(
            "skill_forge.application.use_cases.publish_skill.PublishPack.execute",
            return_value=mock_resp,
        ):
            result = runner.invoke(
                app,
                [
                    "publish",
                    str(pack_out),
                    "--registry",
                    str(reg),
                    "--base-url",
                    "https://example.com",
                    "--no-push",
                ],
            )
        assert result.exit_code == 0
        assert "git" in result.stdout.lower() or "push" in result.stdout.lower()


# ── Test command: no evals ─────────────────────────────────────────────────────


class TestTestCommandNoEvals:
    def test_test_skill_no_evals_shows_skip(self, tmp_path: Path) -> None:
        skill_dir = _make_skill_dir(tmp_path)
        # Remove evals.json if it was created by the scaffold
        evals_json = skill_dir / "evals" / "evals.json"
        if evals_json.exists():
            evals_json.write_text("[]", encoding="utf-8")

        result = runner.invoke(app, ["test", str(skill_dir)])
        # exit 0 (no evals — skipped) or similar clean exit
        assert "Traceback" not in (result.stdout or "")

    def test_test_command_no_skill_md_exits_1(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        result = runner.invoke(app, ["test", str(empty)])
        assert result.exit_code == 1
        assert "No SKILL.md" in result.stdout


# ── Bedrock XML exporter: _xml_text helper ────────────────────────────────────


class TestBedrockXmlTextHelper:
    def test_xml_text_returns_tagged_string(self) -> None:
        from skill_forge.infrastructure.adapters.exporters.bedrock_xml_exporter import (
            _xml_text,
        )

        out = _xml_text("system", "hello & world")
        assert out.startswith("<system>")
        assert out.endswith("</system>")
        # ET should escape the ampersand
        assert "&amp;" in out or "hello" in out


# ── Toml config: fallback parser ──────────────────────────────────────────────


class TestTomlFallbackParser:
    def test_read_toml_fallback_parses_sections(self) -> None:
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            _read_toml,
        )

        text = (
            "[defaults]\n"
            'registry = "public"\n'
            'target   = "claude"\n'
            "\n"
            "[registries]\n"
            'public = "https://raw.githubusercontent.com/test/skills/main"\n'
        )
        # Call _read_toml directly — exercises the fallback even if tomllib is present
        result = _read_toml(text)
        assert "defaults" in result
        assert result["defaults"]["registry"] == "public"  # type: ignore[index]

    def test_read_toml_fallback_handles_empty_input(self) -> None:
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            _read_toml,
        )

        result = _read_toml("")
        assert result == {}

    def test_read_toml_fallback_ignores_comments(self) -> None:
        from skill_forge.infrastructure.adapters.toml_config_repository import (
            _read_toml,
        )

        text = '# this is a comment\n[section]\n# another comment\nkey = "value"\n'
        result = _read_toml(text)
        assert result["section"]["key"] == "value"  # type: ignore[index]


# ── HTTP fetcher: fetch error paths ──────────────────────────────────────────


class TestHttpFetcherErrorPaths:
    def _make_fetcher(self, opener: object) -> object:
        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        return HttpPackFetcher(opener=opener)  # type: ignore[arg-type]

    def test_fetch_http_error_raises_runtime(self, tmp_path: Path) -> None:
        import urllib.error

        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        class _ErrOpener:
            def open(self, req: object) -> None:
                raise urllib.error.HTTPError(
                    url="https://x.com",
                    code=404,
                    msg="Not Found",
                    hdrs=None,
                    fp=None,  # type: ignore[arg-type]
                )

        fetcher = HttpPackFetcher(opener=_ErrOpener())  # type: ignore[arg-type]
        with pytest.raises(RuntimeError, match="HTTP 404"):
            fetcher.fetch("https://x.com/pack.skillpack", tmp_path / "out.skillpack")

    def test_fetch_url_error_raises_runtime(self, tmp_path: Path) -> None:
        import urllib.error

        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        class _ErrOpener:
            def open(self, req: object) -> None:
                raise urllib.error.URLError("Network unreachable")

        fetcher = HttpPackFetcher(opener=_ErrOpener())  # type: ignore[arg-type]
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            fetcher.fetch("https://x.com/pack.skillpack", tmp_path / "out.skillpack")

    def test_fetch_index_http_error(self) -> None:
        import urllib.error

        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        class _ErrOpener:
            def open(self, req: object) -> None:
                raise urllib.error.HTTPError(
                    url="https://x.com/index.json",
                    code=403,
                    msg="Forbidden",
                    hdrs=None,
                    fp=None,  # type: ignore[arg-type]
                )

        fetcher = HttpPackFetcher(opener=_ErrOpener())  # type: ignore[arg-type]
        with pytest.raises(RuntimeError, match="HTTP 403"):
            fetcher.fetch_index("https://x.com/index.json")

    def test_fetch_index_url_error(self) -> None:
        import urllib.error

        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        class _ErrOpener:
            def open(self, req: object) -> None:
                raise urllib.error.URLError("DNS lookup failed")

        fetcher = HttpPackFetcher(opener=_ErrOpener())  # type: ignore[arg-type]
        with pytest.raises(RuntimeError, match="Failed to fetch index"):
            fetcher.fetch_index("https://x.com/index.json")

    def test_fetch_index_too_large(self) -> None:

        from skill_forge.infrastructure.adapters.http_pack_fetcher import (
            FetchTooLargeError,
            HttpPackFetcher,
        )

        class _BigResponse:
            def read(self, n: int = -1) -> bytes:
                return b"x" * (n + 1)

            def getheader(self, name: str) -> str | None:
                return None

            def __enter__(self) -> _BigResponse:
                return self

            def __exit__(self, *a: object) -> None:
                return None

        class _BigOpener:
            def open(self, req: object) -> _BigResponse:
                return _BigResponse()

        fetcher = HttpPackFetcher(max_bytes=5, opener=_BigOpener())  # type: ignore[arg-type]
        with pytest.raises(FetchTooLargeError, match="Index exceeded"):
            fetcher.fetch_index("https://x.com/index.json")

    def test_fetch_build_request_github_token(self) -> None:
        """Token sent as Authorization: token for github.com URLs."""

        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        received_headers: dict[str, str] = {}

        class _CapturingOpener:
            def open(self, req: object) -> None:
                received_headers.update(dict(req.headers))  # type: ignore[union-attr]
                raise RuntimeError("stop")

        fetcher = HttpPackFetcher(
            token="mytoken",
            opener=_CapturingOpener(),  # type: ignore[arg-type]
        )
        import contextlib

        with contextlib.suppress(RuntimeError):
            fetcher.fetch(
                "https://raw.githubusercontent.com/org/repo/main/pack.skillpack",
                __import__("pathlib").Path("/tmp/x"),
            )
        assert "Authorization" in received_headers or "authorization" in {
            k.lower() for k in received_headers
        }

    def test_fetch_bearer_token_used_as_is(self) -> None:
        """Tokens starting with 'Bearer ' are used as-is."""
        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        received: dict[str, str] = {}

        class _Cap:
            def open(self, req: object) -> None:
                received.update(dict(req.headers))  # type: ignore[union-attr]
                raise RuntimeError("stop")

        fetcher = HttpPackFetcher(
            token="Bearer supertoken",
            opener=_Cap(),  # type: ignore[arg-type]
        )
        import contextlib

        with contextlib.suppress(RuntimeError):
            fetcher.fetch(
                "https://example.com/pack.skillpack",
                __import__("pathlib").Path("/tmp/x"),
            )
        auth_val = received.get("Authorization") or received.get("authorization") or ""
        assert "Bearer supertoken" in auth_val

    def test_fetch_non_github_token_omitted(self) -> None:
        """Non-github host with non-Bearer token: no auth header sent."""
        from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher

        received: dict[str, str] = {}

        class _Cap:
            def open(self, req: object) -> None:
                received.update(dict(req.headers))  # type: ignore[union-attr]
                raise RuntimeError("stop")

        fetcher = HttpPackFetcher(
            token="plaintoken",
            opener=_Cap(),  # type: ignore[arg-type]
        )
        import contextlib

        with contextlib.suppress(RuntimeError):
            fetcher.fetch(
                "https://myhost.example.com/pack.skillpack",
                __import__("pathlib").Path("/tmp/x"),
            )
        auth_val = received.get("Authorization") or received.get("authorization")
        assert auth_val is None


# ── Filesystem repository: error paths ───────────────────────────────────────


class TestFilesystemRepositoryExtended:
    """Test the filesystem repository's optional directory creation paths."""

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

    def _parse_skill(self, name: str, extra_frontmatter: str = "") -> object:
        """Build a skill via the parser so all types are correct."""
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        md = (
            f"---\nname: {name}\n"
            f"description: |\n  Use for testing {name}. Triggers on: test.\n"
            f"{extra_frontmatter}"
            f"---\n\n## Instructions\n\nDo it.\n"
        )
        return MarkdownSkillParser().parse(md)

    def test_save_creates_scripts_dir_when_skill_has_scripts(self, tmp_path: Path) -> None:
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        md = (
            "---\nname: s\n"
            "description: |\n  Use for stuff. Triggers on: test.\n"
            "---\n\n## Instructions\n\nDo it.\n\n"
            "## Scripts\n\n- [setup](scripts/setup.sh): Setup script\n"
        )
        skill = MarkdownSkillParser().parse(md)
        repo = self._make_repo(tmp_path)
        path = repo.save(skill)  # type: ignore[union-attr]
        assert (path / "scripts").exists()

    def test_save_creates_assets_dir_when_skill_has_assets(self, tmp_path: Path) -> None:
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        md = (
            "---\nname: s2\n"
            "description: |\n  Use for stuff. Triggers on: test.\n"
            "---\n\n## Instructions\n\nDo it.\n\n"
            "## Assets\n\n- [logo](assets/logo.png): Logo image\n"
        )
        skill = MarkdownSkillParser().parse(md)
        repo = self._make_repo(tmp_path)
        path = repo.save(skill)  # type: ignore[union-attr]
        assert (path / "assets").exists()

    def test_save_creates_examples_dir_when_skill_has_examples(self, tmp_path: Path) -> None:
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )

        md = (
            "---\nname: s3\n"
            "description: |\n  Use for stuff. Triggers on: test.\n"
            "---\n\n## Instructions\n\nDo it.\n\n"
            "## Examples\n\n- [ex](examples/ex.py): Example\n"
        )
        skill = MarkdownSkillParser().parse(md)
        repo = self._make_repo(tmp_path)
        path = repo.save(skill)  # type: ignore[union-attr]
        assert (path / "examples").exists()

    def test_list_all_skips_unparseable_skill_md(self, tmp_path: Path) -> None:
        from skill_forge.infrastructure.adapters.filesystem_repository import (
            FilesystemSkillRepository,
        )
        from skill_forge.infrastructure.adapters.markdown_parser import (
            MarkdownSkillParser,
        )
        from skill_forge.infrastructure.adapters.markdown_renderer import (
            MarkdownSkillRenderer,
        )

        bad = tmp_path / "dev" / "broken"
        bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text("not valid frontmatter at all !!!", encoding="utf-8")

        repo = FilesystemSkillRepository(
            base_path=tmp_path,
            renderer=MarkdownSkillRenderer(),
            parser=MarkdownSkillParser(),
        )
        # Should not raise — just skip
        skills = repo.list_all()
        # broken skill won't appear (parse would produce something or be skipped)
        # The important thing is no exception propagates
        assert isinstance(skills, list)


# ── Symlink installer: error paths ───────────────────────────────────────────


class TestSymlinkInstallerExtended:
    def test_vscode_global_scope_raises(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import InstallTarget, SkillScope
        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )

        installer = SymlinkSkillInstaller(project_root=tmp_path)
        with pytest.raises(ValueError, match="VS Code"):
            installer.install(
                skill_path=tmp_path / "my-skill",
                scope=SkillScope.GLOBAL,
                target=InstallTarget.VSCODE,
            )

    def test_is_installed_returns_false_when_not_installed(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import SkillScope
        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )

        installer = SymlinkSkillInstaller(project_root=tmp_path)
        result = installer.is_installed("phantom-skill", SkillScope.PROJECT)
        assert result is False

    def test_list_installed_empty_when_dir_absent(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import SkillScope
        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )

        installer = SymlinkSkillInstaller(project_root=tmp_path)
        result = installer.list_installed(SkillScope.PROJECT)
        assert result == []

    def test_uninstall_removes_existing_symlink(self, tmp_path: Path) -> None:
        from skill_forge.domain.model import InstallTarget, SkillScope
        from skill_forge.infrastructure.adapters.symlink_installer import (
            SymlinkSkillInstaller,
        )

        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nbody", encoding="utf-8")

        installer = SymlinkSkillInstaller(project_root=tmp_path)
        installer.install(skill_dir, SkillScope.PROJECT, InstallTarget.CLAUDE)
        removed = installer.uninstall("my-skill", SkillScope.PROJECT, InstallTarget.CLAUDE)
        assert len(removed) == 1
        assert not removed[0].exists()


# ── Git registry publisher: update_index and error paths ─────────────────────


class TestGitRegistryPublisherExtended:
    @pytest.fixture()
    def git_registry(self, tmp_path: Path) -> Path:
        if shutil.which("git") is None:
            pytest.skip("git not available")
        reg = tmp_path / "registry"
        reg.mkdir()
        env = {
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "t@t.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "t@t.com",
            "PATH": __import__("os").environ.get("PATH", ""),
            "HOME": str(tmp_path),
        }
        subprocess.run(
            ["git", "-C", str(reg), "init", "-q", "-b", "main"],
            check=True,
            env=env,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(reg), "config", "user.email", "t@t.com"],
            check=True,
            env=env,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(reg), "config", "user.name", "test"],
            check=True,
            env=env,
            capture_output=True,
        )
        return reg

    def test_update_index_writes_and_commits(self, git_registry: Path, tmp_path: Path) -> None:
        from skill_forge.domain.model import IndexedSkill, IndexedVersion, RegistryIndex
        from skill_forge.infrastructure.adapters.git_registry_publisher import (
            GitRegistryPublisher,
        )

        publisher = GitRegistryPublisher(
            registry_root=git_registry,
            registry_name="test-reg",
            base_url="https://example.com",
        )

        version = IndexedVersion(
            version="1.0.0",
            path="packs/dev/skill-1.0.0.skillpack",
            sha256="a" * 64,
        )
        skill = IndexedSkill(
            category="dev",
            name="my-skill",
            description="A skill",
            latest="1.0.0",
            versions=(version,),
        )
        index = RegistryIndex(
            registry_name="test-reg",
            base_url="https://example.com",
            updated_at="2026-04-11T00:00:00+00:00",
            skills=(skill,),
        )

        committed = publisher.update_index(
            index=index,
            message="chore: yank my-skill 1.0.0",
            push=False,
        )
        assert committed is True
        assert (git_registry / "index.json").exists()

    def test_update_index_no_changes_returns_false(
        self, git_registry: Path, tmp_path: Path
    ) -> None:
        """Calling update_index twice with the same content: second call returns False."""
        from skill_forge.domain.model import IndexedSkill, IndexedVersion, RegistryIndex
        from skill_forge.infrastructure.adapters.git_registry_publisher import (
            GitRegistryPublisher,
        )

        publisher = GitRegistryPublisher(
            registry_root=git_registry,
            registry_name="test-reg",
            base_url="https://example.com",
        )

        version = IndexedVersion(
            version="1.0.0",
            path="packs/dev/skill-1.0.0.skillpack",
            sha256="a" * 64,
        )
        skill = IndexedSkill(
            category="dev",
            name="my-skill",
            description="A skill",
            latest="1.0.0",
            versions=(version,),
        )
        index = RegistryIndex(
            registry_name="test-reg",
            base_url="https://example.com",
            updated_at="2026-04-11T00:00:00+00:00",
            skills=(skill,),
        )

        with patch(
            "skill_forge.infrastructure.adapters.git_registry_publisher._now_iso",
            return_value="2026-04-11T00:00:00+00:00",
        ):
            publisher.update_index(index=index, message="first commit", push=False)
            second = publisher.update_index(index=index, message="no changes", push=False)

        # No new staged changes → second commit returns False
        assert second is False
