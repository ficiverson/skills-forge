"""Tests for SubprocessClaudeRunner."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from skill_forge.infrastructure.adapters.subprocess_claude_runner import (
    SubprocessClaudeRunner,
)


class TestSubprocessClaudeRunnerInit:
    def test_uses_provided_path(self) -> None:
        runner = SubprocessClaudeRunner(claude_path="/usr/local/bin/claude")
        assert runner._claude_path == "/usr/local/bin/claude"

    def test_falls_back_to_shutil_which(self) -> None:
        with patch("shutil.which", return_value="/custom/claude"):
            runner = SubprocessClaudeRunner()
        assert runner._claude_path == "/custom/claude"

    def test_falls_back_to_claude_when_not_on_path(self) -> None:
        with patch("shutil.which", return_value=None):
            runner = SubprocessClaudeRunner()
        assert runner._claude_path == "claude"


class TestSubprocessClaudeRunnerRun:
    def _make_runner(self) -> SubprocessClaudeRunner:
        return SubprocessClaudeRunner(claude_path="/fake/claude")

    def test_returns_stdout_on_success(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Great output\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            runner = self._make_runner()
            result = runner.run("hello prompt")

        assert result == "Great output\n"

    def test_raises_runtime_error_on_file_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError("claude: not found")):
            runner = self._make_runner()
            with pytest.raises(RuntimeError, match="Claude CLI not found"):
                runner.run("test")

    def test_raises_runtime_error_on_timeout(self) -> None:
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=30),
        ):
            runner = self._make_runner()
            with pytest.raises(RuntimeError, match="timed out after 30s"):
                runner.run("test", timeout=30)

    def test_raises_runtime_error_on_nonzero_exit_no_stderr(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            runner = self._make_runner()
            with pytest.raises(RuntimeError, match="Claude CLI exited 1"):
                runner.run("test")

    def test_raises_runtime_error_on_nonzero_exit_with_stderr(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "authentication failed"

        with patch("subprocess.run", return_value=mock_result):
            runner = self._make_runner()
            with pytest.raises(RuntimeError, match="authentication failed"):
                runner.run("test")

    def test_passes_prompt_to_subprocess(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner = self._make_runner()
            runner.run("my prompt")

        args = mock_run.call_args[0][0]
        assert args == ["/fake/claude", "-p", "my prompt"]

    def test_custom_timeout_is_forwarded(self) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            runner = self._make_runner()
            runner.run("prompt", timeout=60)

        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == 60
