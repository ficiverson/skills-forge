#!/usr/bin/env python3
"""check_pipeline.py — mirrors the CI 'Lint & Type Check' job locally.

Runs the exact three commands the GitHub Actions lint job runs, in the same
order, and produces a structured pass/fail report so the preflight can catch
pipeline failures before a push triggers CI.

Usage:
    python output_skills/distribution/release-preflight/scripts/check_pipeline.py

Exit code:
    0  all checks passed
    1  one or more checks failed

The script does NOT require any arguments. It always runs from the project root
(auto-detected as the directory that contains pyproject.toml).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────

RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BOLD = "\033[1m"


def _find_project_root() -> Path:
    """Walk up from the script location until we find pyproject.toml."""
    candidate = Path(__file__).resolve()
    for _ in range(10):
        candidate = candidate.parent
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("Could not locate project root (no pyproject.toml found in parents).")


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Run *cmd* and return (returncode, combined stdout+stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode, result.stdout


def _print_check(label: str, passed: bool, detail: str = "") -> None:
    icon = f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"
    status = "PASSED" if passed else "FAILED"
    print(f"  {icon}  {label:<35} {status}")
    if not passed and detail.strip():
        for line in detail.strip().splitlines():
            print(f"       {YELLOW}{line}{RESET}")


# ── CI lint job steps ─────────────────────────────────────────────────────────

CHECKS: list[tuple[str, list[str]]] = [
    # label                 command (maps 1-to-1 with ci.yml lint job steps)
    ("ruff check src/ tests/",        ["ruff", "check", "src/", "tests/"]),
    ("ruff format --check src/ tests/", ["ruff", "format", "--check", "src/", "tests/"]),
    ("mypy src/",                     ["mypy", "src/"]),
]


def main() -> int:
    root = _find_project_root()

    # Make sure tools are on PATH (handles pip --user installs)
    local_bin = Path.home() / ".local" / "bin"
    env_path = os.environ.get("PATH", "")
    if str(local_bin) not in env_path:
        os.environ["PATH"] = f"{local_bin}{os.pathsep}{env_path}"

    print()
    print(f"{BOLD}{'─' * 55}{RESET}")
    print(f"{BOLD}  CI Pipeline Check — Lint & Type Check job{RESET}")
    print(f"{BOLD}{'─' * 55}{RESET}")
    print(f"  Project root: {root}")
    print()

    results: list[tuple[str, bool, str]] = []

    for label, cmd in CHECKS:
        rc, output = _run(cmd, cwd=root)
        passed = rc == 0
        results.append((label, passed, output))
        _print_check(label, passed, "" if passed else output)

    # ── summary ───────────────────────────────────────────────────────────────
    failed = [label for label, ok, _ in results if not ok]
    passed_count = len(results) - len(failed)

    print()
    print(f"{BOLD}{'─' * 55}{RESET}")
    if not failed:
        print(f"  {GREEN}{BOLD}All {len(results)} checks passed — pipeline gate: ✅ CLEAR{RESET}")
    else:
        print(
            f"  {RED}{BOLD}{len(failed)}/{len(results)} checks FAILED — pipeline gate: ❌ BLOCKED{RESET}"
        )
        print(f"  {YELLOW}Failing:{RESET}")
        for label in failed:
            print(f"    • {label}")
    print(f"{BOLD}{'─' * 55}{RESET}")
    print()

    # Print full output for failed checks at the end for easy copy-paste
    if failed:
        print(f"{BOLD}Full output for failing checks:{RESET}")
        for label, ok, output in results:
            if not ok:
                print(f"\n{YELLOW}── {label} ──{RESET}")
                print(output)

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
