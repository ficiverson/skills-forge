#!/usr/bin/env python3
"""Phase 4: CLI Sandbox UAT.

Exercises every skills-forge CLI command in an isolated temp directory.
Each command is run, and pass/fail is recorded based on exit code.

Usage:
    python uat_sandbox.py
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PASS = "✅"
FAIL = "❌"

# The CLI binary — tries local install first, then PATH
CLI = shutil.which("skills-forge") or str(
    Path.home() / ".local" / "bin" / "skills-forge"
)


def run(label: str, args: list[str], cwd: Path) -> bool:
    """Run a CLI command and print pass/fail. Returns True if exit 0."""
    cmd = [CLI] + args
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  {PASS}  {label}")
        return True
    else:
        stderr_snippet = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "(no stderr)"
        print(f"  {FAIL}  {label}: exit {result.returncode} — {stderr_snippet}")
        return False


def main() -> int:
    tmpdir = Path(tempfile.mkdtemp(prefix="skills-forge-uat-"))
    print(f"UAT sandbox: {tmpdir}\n")

    results: list[bool] = []

    try:
        # 1. init
        ws = tmpdir / "workspace"
        ws.mkdir()
        results.append(run("skills-forge init", ["init"], cwd=ws))

        # 2. create
        results.append(run(
            "skills-forge create",
            ["create", "-n", "uat-skill", "-c", "testing",
             "-d", "UAT test skill for preflight verification", "-e", "🧪"],
            cwd=ws,
        ))

        skill_dir = ws / "output_skills" / "testing" / "uat-skill"

        # 3. lint
        results.append(run(
            "skills-forge lint",
            ["lint", str(skill_dir)],
            cwd=ws,
        ))

        # 4. install (project, claude)
        results.append(run(
            "skills-forge install --scope project --target claude",
            ["install", str(skill_dir), "--scope", "project", "--target", "claude"],
            cwd=ws,
        ))

        # 5. install (project, agents)
        results.append(run(
            "skills-forge install --scope project --target agents",
            ["install", str(skill_dir), "--scope", "project", "--target", "agents"],
            cwd=ws,
        ))

        # 6. list
        results.append(run(
            "skills-forge list",
            ["list", str(ws / "output_skills")],
            cwd=ws,
        ))

        # 7. pack
        pack_out = tmpdir / "uat-skill-0.1.0.skillpack"
        results.append(run(
            "skills-forge pack",
            ["pack", str(skill_dir), "-o", str(pack_out)],
            cwd=ws,
        ))

        # 8. unpack
        unpack_dir = tmpdir / "unpacked"
        unpack_dir.mkdir()
        results.append(run(
            "skills-forge unpack",
            ["unpack", str(pack_out), "-o", str(unpack_dir)],
            cwd=ws,
        ))

        # 9. export (system-prompt) — export takes the .skillpack file, not the source dir
        results.append(run(
            "skills-forge export (system-prompt)",
            ["export", str(pack_out), "-f", "system-prompt"],
            cwd=ws,
        ))

        # 10. export (gpt-json)
        results.append(run(
            "skills-forge export (gpt-json)",
            ["export", str(pack_out), "-f", "gpt-json"],
            cwd=ws,
        ))

        # 11. uninstall
        results.append(run(
            "skills-forge uninstall",
            ["uninstall", "uat-skill", "--scope", "project"],
            cwd=ws,
        ))

        # 12. uninstall idempotent (re-run on already-removed skill must exit 0)
        results.append(run(
            "skills-forge uninstall (idempotent)",
            ["uninstall", "uat-skill", "--scope", "project"],
            cwd=ws,
        ))

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    passed = sum(results)
    total = len(results)
    print()
    if passed == total:
        print(f"All {total} commands passed ✅")
        return 0
    else:
        failed = total - passed
        print(f"{failed}/{total} commands FAILED ❌")
        return 1


if __name__ == "__main__":
    sys.exit(main())
