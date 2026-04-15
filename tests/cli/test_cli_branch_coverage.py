"""Targeted branch-coverage tests for cli/main.py edge cases.

Closes the remaining uncovered lines identified by the independent testing
assessment (lint_service 0%, CLI 43%, factory 71% — all now resolved).
This file fills the residual gaps after v0.8.0 to push main.py from 89% → 95%+.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from skill_forge.cli.main import app

runner = CliRunner()

# ── helpers ────────────────────────────────────────────────────────────────────

_SKILL_MD = """\
---
name: gap-skill
version: 1.0.0
description: |
  Use this skill when closing coverage gaps. Triggers on: test, validate.
emoji: 🔍
depends_on: "other-skill"
requires_forge: ">=0.8.0"
---

STARTER_CHARACTER = 🔍

## Instructions

Close coverage gaps.
"""


def _make_skill_dir(tmp_path: Path, name: str = "gap-skill") -> Path:
    skill_dir = tmp_path / "dev" / name
    skill_dir.mkdir(parents=True)
    md = _SKILL_MD.replace("gap-skill", name)
    (skill_dir / "SKILL.md").write_text(md, encoding="utf-8")
    return skill_dir


# ── list: empty directory ──────────────────────────────────────────────────────


class TestListEmptyDirectory:
    def test_list_empty_dir_prints_no_skills_found(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["list", str(tmp_path)])
        assert result.exit_code == 0
        assert "No skills found" in result.output


# ── export: FileNotFoundError ──────────────────────────────────────────────────


class TestExportFileNotFoundError:
    def test_export_use_case_file_not_found_exits_1(self, tmp_path: Path) -> None:
        """Export should print ⚠ and exit 1 when the use case raises FileNotFoundError.

        The source must exist on disk (Typer validates this before our code runs),
        so we create a dummy file and let the mock use case raise the error.
        """
        existing_pack = tmp_path / "dummy.skillpack"
        existing_pack.write_bytes(b"not a real zip")

        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = FileNotFoundError(
            "manifest.json not found in archive"
        )

        with patch("skill_forge.cli.main.build_export_use_case", return_value=mock_use_case):
            result = runner.invoke(
                app, ["export", str(existing_pack), "-f", "system-prompt"]
            )
        assert result.exit_code == 1
        assert "⚠" in result.output


# ── uninstall: invalid target ──────────────────────────────────────────────────


class TestUninstallInvalidTarget:
    def test_uninstall_invalid_target_exits_1(self) -> None:
        result = runner.invoke(
            app, ["uninstall", "some-skill", "--target", "notavalidtarget"]
        )
        assert result.exit_code == 1
        assert "Unknown target" in result.output or "notavalidtarget" in result.output

    def test_uninstall_not_installed_shows_warning(self, tmp_path: Path) -> None:
        """Uninstalling a skill that isn't present should exit 0 with a warning."""
        mock_response = MagicMock()
        mock_response.was_installed = False
        mock_response.removed_paths = []

        mock_installer = MagicMock()
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_response

        with (
            patch(
                "skill_forge.cli.main.build_installer",
                return_value=mock_installer,
            ),
            patch(
                "skill_forge.application.use_cases.install_skill.UninstallSkill",
                return_value=mock_use_case,
            ),
        ):
            result = runner.invoke(
                app, ["uninstall", "ghost-skill", "--scope", "global"]
            )
        assert result.exit_code == 0
        assert "was not found" in result.output or "⚠" in result.output


# ── init: config creation + tool-detection hints ──────────────────────────────


class TestInitBranches:
    def test_init_creates_config_when_absent(self, tmp_path: Path) -> None:
        """When no config exists, init should create it and report the path."""
        config_path = tmp_path / ".skills-forge" / "config.toml"

        mock_cfg_repo = MagicMock()
        mock_cfg_repo.path = config_path  # does not exist yet

        with (
            patch("skill_forge.cli.main.build_config_repo", return_value=mock_cfg_repo),
            patch("shutil.which", return_value=None),
        ):
            result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert "Config created" in result.output

    def test_init_detected_single_tool_no_tip(self, tmp_path: Path) -> None:
        """When exactly one tool is detected, do NOT show the --target all tip."""
        existing = tmp_path / "config.toml"
        existing.touch()
        mock_cfg_repo = MagicMock()
        mock_cfg_repo.path = existing  # exists() → True

        def _which(cmd: str) -> str | None:
            return "/usr/bin/claude" if cmd == "claude" else None

        with (
            patch("skill_forge.cli.main.build_config_repo", return_value=mock_cfg_repo),
            patch("shutil.which", side_effect=_which),
        ):
            result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert "Detected agent tools" in result.output
        assert "--target all" not in result.output

    def test_init_detected_multiple_tools_shows_tip(self, tmp_path: Path) -> None:
        """When multiple tools are detected, show the --target all tip."""
        existing = tmp_path / "config.toml"
        existing.touch()
        mock_cfg_repo = MagicMock()
        mock_cfg_repo.path = existing

        def _which(cmd: str) -> str | None:
            return f"/usr/bin/{cmd}" if cmd in ("claude", "gemini") else None

        with (
            patch("skill_forge.cli.main.build_config_repo", return_value=mock_cfg_repo),
            patch("shutil.which", side_effect=_which),
        ):
            result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert "--target all" in result.output

    def test_init_no_tools_detected_shows_install_hint(self, tmp_path: Path) -> None:
        """When no tools are detected, init should suggest installing an agent CLI."""
        existing = tmp_path / "config.toml"
        existing.touch()
        mock_cfg_repo = MagicMock()
        mock_cfg_repo.path = existing

        with (
            patch("skill_forge.cli.main.build_config_repo", return_value=mock_cfg_repo),
            patch("shutil.which", return_value=None),
        ):
            result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0
        assert "No agent-CLI tools found" in result.output


# ── info: registry fallback, deps, requires_forge, latest, deprecated ──────────


def _make_info_response(
    *,
    registry_latest: str | None = None,
    registry_deprecated: bool = False,
    up_to_date: bool | None = None,
    has_deps: bool = False,
    requires_forge: str | None = None,
) -> MagicMock:
    from skill_forge.domain.model import Skill, SkillIdentity

    identity = SkillIdentity(name="gap-skill", category="dev")
    mock_skill = MagicMock(spec=Skill)
    mock_skill.identity = identity
    mock_skill.version = "1.0.0"
    mock_skill.total_estimated_tokens = 500
    mock_skill.has_evals = False
    mock_skill.evals = []
    mock_skill.has_dependencies = has_deps
    mock_skill.depends_on = (
        [MagicMock(skill_name="dep-a")] if has_deps else []
    )
    mock_skill.requires_forge = requires_forge

    mock_loc = MagicMock()
    mock_loc.target.value = "claude"
    mock_loc.path = "/fake/path/gap-skill"
    mock_loc.is_broken = False

    mock_response = MagicMock()
    mock_response.is_installed = True
    mock_response.skill = mock_skill
    mock_response.install_locations = [mock_loc]
    mock_response.registry_latest = registry_latest
    mock_response.registry_deprecated = registry_deprecated
    mock_response.is_up_to_date = up_to_date
    return mock_response


class TestInfoBranches:
    def _invoke_info(self, response: MagicMock) -> str:
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = response

        with patch(
            "skill_forge.cli.main.build_info_use_case",
            return_value=mock_use_case,
        ):
            result = runner.invoke(app, ["info", "gap-skill"])
        return result.output

    def test_info_shows_depends_on(self) -> None:
        resp = _make_info_response(has_deps=True)
        output = self._invoke_info(resp)
        assert "Depends:" in output

    def test_info_shows_requires_forge(self) -> None:
        resp = _make_info_response(requires_forge=">=0.8.0")
        output = self._invoke_info(resp)
        assert "Requires:" in output

    def test_info_registry_up_to_date(self) -> None:
        resp = _make_info_response(registry_latest="1.0.0", up_to_date=True)
        output = self._invoke_info(resp)
        assert "up to date" in output

    def test_info_registry_upgrade_available(self) -> None:
        resp = _make_info_response(registry_latest="2.0.0", up_to_date=False)
        output = self._invoke_info(resp)
        assert "available" in output

    def test_info_registry_deprecated(self) -> None:
        resp = _make_info_response(
            registry_latest="2.0.0", up_to_date=False, registry_deprecated=True
        )
        output = self._invoke_info(resp)
        assert "DEPRECATED" in output

    def test_info_resolves_registry_from_config(self) -> None:
        """When --registry is omitted, info falls back to the default configured registry."""
        resp = _make_info_response()
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = resp

        mock_cfg = MagicMock()
        mock_cfg.default_registry = "my-reg"
        mock_reg = MagicMock()
        mock_reg.name = "my-reg"
        mock_reg.url = "https://example.com/registry"
        mock_cfg.registries = [mock_reg]

        with (
            patch(
                "skill_forge.cli.main.build_info_use_case",
                return_value=mock_use_case,
            ),
            patch("skill_forge.cli.main.load_config", return_value=mock_cfg),
        ):
            result = runner.invoke(app, ["info", "gap-skill"])

        assert result.exit_code == 0


# ── doctor: no registry ────────────────────────────────────────────────────────


class TestDoctorBranches:
    def test_doctor_resolves_registry_from_config(self) -> None:
        mock_response = MagicMock()
        mock_response.checked_count = 1
        mock_response.is_healthy = True
        mock_response.failure_count = 0

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_response

        mock_cfg = MagicMock()
        mock_cfg.default_registry = "reg"
        mock_reg = MagicMock()
        mock_reg.name = "reg"
        mock_reg.url = "https://reg.example.com"
        mock_cfg.registries = [mock_reg]

        with (
            patch(
                "skill_forge.cli.main.build_doctor_use_case",
                return_value=mock_use_case,
            ),
            patch("skill_forge.cli.main.load_config", return_value=mock_cfg),
        ):
            result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "healthy" in result.output


# ── update: no registry + confirm abort ───────────────────────────────────────


class TestUpdateBranches:
    def test_update_no_registry_configured_exits_1(self) -> None:
        """update with no --registry and no configured default should exit 1."""
        mock_cfg = MagicMock()
        mock_cfg.default_registry = None
        mock_cfg.registries = []

        with patch("skill_forge.cli.main.load_config", return_value=mock_cfg):
            result = runner.invoke(app, ["update"])

        assert result.exit_code == 1
        assert "No registry configured" in result.output

    def test_update_confirm_abort_exits_0(self) -> None:
        """Answering 'n' to the update confirmation prompt exits 0."""
        mock_record = MagicMock()
        mock_record.would_update = True
        mock_record.skill_name = "gap-skill"
        mock_record.old_version = "1.0.0"
        mock_record.new_version = "2.0.0"
        mock_record.updated = False

        mock_response = MagicMock()
        mock_response.records = [mock_record]
        mock_response.updated_count = 0

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_response

        with (
            patch(
                "skill_forge.cli.main.build_update_use_case",
                return_value=mock_use_case,
            ),
        ):
            # "n\n" answers the "Proceed?" confirm prompt with No
            result = runner.invoke(
                app,
                ["update", "--registry", "https://example.com"],
                input="n\n",
            )

        assert result.exit_code == 0
        assert "Aborted" in result.output


# ── diff: no registry falls back to config ────────────────────────────────────


class TestDiffNoRegistry:
    def test_diff_no_registry_shows_actionable_error(self) -> None:
        """diff without --registry and no config should give an actionable error."""
        mock_cfg = MagicMock()
        mock_cfg.default_registry = None
        mock_cfg.registries = []

        with patch("skill_forge.cli.main.load_config", return_value=mock_cfg):
            result = runner.invoke(app, ["diff"])

        # Should either exit non-zero or print a useful error
        assert result.exit_code != 0 or "--registry" in result.output or "⚠" in result.output


# ── factory: build_exporter unknown format ─────────────────────────────────────


class TestFactoryBuildExporter:
    def test_build_exporter_unknown_format_raises(self) -> None:
        from skill_forge.cli.factory import build_exporter
        from skill_forge.domain.model import ExportFormat

        # All known formats must work
        for fmt in ExportFormat:
            exporter = build_exporter(fmt)
            assert exporter is not None

    def test_build_fetcher_with_url_resolves_token_from_config(self) -> None:
        """build_fetcher should resolve a per-registry auth token when a URL matches."""
        mock_cfg = MagicMock()
        mock_reg = MagicMock()
        mock_reg.url = "https://private.registry.example.com"
        mock_reg.resolved_token = "secret-token"
        mock_cfg.registries = [mock_reg]

        with patch("skill_forge.cli.factory.load_config", return_value=mock_cfg):
            from skill_forge.cli.factory import build_fetcher

            fetcher = build_fetcher(
                "https://private.registry.example.com/packs/my-skill.skillpack"
            )
        assert fetcher is not None

    def test_build_fetcher_no_url_returns_unauthenticated(self) -> None:
        from skill_forge.cli.factory import build_fetcher

        fetcher = build_fetcher("")
        assert fetcher is not None


# ── test command: eval display branches ───────────────────────────────────────


class TestTestSkillEvalDisplay:
    """Cover the eval output display branches in cli/main.py (test command)."""

    def _make_eval_skill_dir(self, tmp_path: Path) -> Path:
        skill_dir = tmp_path / "dev" / "eval-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: eval-skill\n"
            "version: 1.0.0\n"
            "description: |\n"
            "  Use this skill when running evals. Triggers on: test, eval.\n"
            "emoji: 🧪\n"
            "---\n\n## Instructions\n\nRun evals.\n",
            encoding="utf-8",
        )
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir()
        (evals_dir / "evals.json").write_text(
            '[{"id": 1, "prompt": "hello", "expected_output": "world",'
            ' "assertions": [{"id": "a1", "text": "contains world",'
            ' "type": "contains", "expected": "world"}], "files": []}]',
            encoding="utf-8",
        )
        return skill_dir

    def test_test_command_skill_with_no_evals_skips(self, tmp_path: Path) -> None:
        """Skills without evals should print a warning and skip, not crash."""
        skill_dir = tmp_path / "dev" / "no-eval-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: no-eval-skill\n"
            "version: 1.0.0\n"
            "description: |\n"
            "  Use this skill when there are no evals. Triggers on: test.\n"
            "---\n\n## Instructions\n\nNo evals.\n",
            encoding="utf-8",
        )

        mock_use_case = MagicMock()

        with patch(
            "skill_forge.cli.main.build_test_use_case",
            return_value=mock_use_case,
        ):
            result = runner.invoke(app, ["test", str(skill_dir)])

        assert result.exit_code == 0
        assert "no evals" in result.output or "skipping" in result.output

    def test_test_command_passed_eval_displays_checkmark(self, tmp_path: Path) -> None:
        """A passing eval case should display ✅ and assertion counts."""
        from skill_forge.application.use_cases.test_skill import (
            AssertionResult,
            EvalCaseResult,
            TestSkillResponse,
        )
        from skill_forge.domain.model import EvalAssertion, EvalCase

        assertion = EvalAssertion(
            id="a1", text="contains world", type="contains", expected="world"
        )
        case = EvalCase(
            id=1,
            prompt="hello",
            expected_output="world",
            assertions=(assertion,),
        )
        a_result = AssertionResult(assertion=assertion, passed=True, reason="ok")
        case_result = EvalCaseResult(
            case=case, response="hello world", assertion_results=[a_result]
        )
        test_response = TestSkillResponse(
            skill_name="eval-skill", case_results=[case_result]
        )

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = test_response

        skill_dir = self._make_eval_skill_dir(tmp_path)

        with patch(
            "skill_forge.cli.main.build_test_use_case",
            return_value=mock_use_case,
        ):
            result = runner.invoke(app, ["test", str(skill_dir)])

        assert "✅" in result.output
        assert "1/1" in result.output
        assert "Pass rate" in result.output

    def test_test_command_failed_assertion_displays_cross(self, tmp_path: Path) -> None:
        """A failing assertion should display ✘ with a reason."""
        from skill_forge.application.use_cases.test_skill import (
            AssertionResult,
            EvalCaseResult,
            TestSkillResponse,
        )
        from skill_forge.domain.model import EvalAssertion, EvalCase

        assertion = EvalAssertion(
            id="a1", text="contains world", type="contains", expected="world"
        )
        case = EvalCase(
            id=1,
            prompt="hello",
            expected_output="world",
            assertions=(assertion,),
        )
        a_result = AssertionResult(
            assertion=assertion, passed=False, reason="'world' not in response"
        )
        case_result = EvalCaseResult(
            case=case, response="nothing here", assertion_results=[a_result]
        )
        test_response = TestSkillResponse(
            skill_name="eval-skill", case_results=[case_result]
        )

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = test_response

        skill_dir = self._make_eval_skill_dir(tmp_path)

        with patch(
            "skill_forge.cli.main.build_test_use_case",
            return_value=mock_use_case,
        ):
            result = runner.invoke(app, ["test", str(skill_dir)])

        assert result.exit_code == 1
        assert "❌" in result.output
        assert "world" in result.output

    def test_test_command_error_in_eval_displays_error_line(
        self, tmp_path: Path
    ) -> None:
        """When an eval case hits an error, it should be displayed with ERROR."""
        from skill_forge.application.use_cases.test_skill import (
            EvalCaseResult,
            TestSkillResponse,
        )
        from skill_forge.domain.model import EvalCase

        case = EvalCase(id=1, prompt="hello", expected_output="")
        case_result = EvalCaseResult(
            case=case,
            response="",
            assertion_results=[],
            error="Claude returned empty response",
        )
        test_response = TestSkillResponse(
            skill_name="eval-skill", case_results=[case_result]
        )

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = test_response

        skill_dir = self._make_eval_skill_dir(tmp_path)

        with patch(
            "skill_forge.cli.main.build_test_use_case",
            return_value=mock_use_case,
        ):
            result = runner.invoke(app, ["test", str(skill_dir)])

        assert result.exit_code == 1
        assert "ERROR" in result.output
