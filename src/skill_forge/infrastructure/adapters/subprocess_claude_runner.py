"""Adapter: runs Claude via the ``claude -p`` CLI subprocess.

Requires the Claude Code CLI to be installed and available on PATH.
If the CLI is not found, every call raises ``RuntimeError`` with a
clear install instruction — so the error surfaces at the first eval
run, not at import time.
"""

from __future__ import annotations

import shutil
import subprocess

from skill_forge.domain.ports import ClaudeRunner


class SubprocessClaudeRunner(ClaudeRunner):
    """Shells out to ``claude -p <prompt>`` and returns stdout."""

    def __init__(self, claude_path: str | None = None) -> None:
        self._claude_path = claude_path or shutil.which("claude") or "claude"

    def run(self, prompt: str, timeout: int = 120) -> str:
        try:
            result = subprocess.run(
                [self._claude_path, "-p", prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Claude CLI not found. Install it with: "
                "npm install -g @anthropic-ai/claude-code"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Claude CLI timed out after {timeout}s"
            ) from exc

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Claude CLI exited {result.returncode}"
                + (f": {stderr}" if stderr else "")
            )

        return result.stdout
