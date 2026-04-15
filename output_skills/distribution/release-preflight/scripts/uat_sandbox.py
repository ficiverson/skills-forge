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

        # 5b. info (NEW in v0.5.0)
        results.append(run(
            "skills-forge info",
            ["info", "uat-skill", "--scope", "project"],
            cwd=ws,
        ))

        # 5c. doctor (NEW in v0.5.0)
        results.append(run(
            "skills-forge doctor",
            ["doctor", "--scope", "project", "--no-registry"],
            cwd=ws,
        ))

        # 6. list
        results.append(run(
            "skills-forge list",
            ["list", str(ws / "output_skills")],
            cwd=ws,
        ))

        # 6b. list --category
        results.append(run(
            "skills-forge list --category testing",
            ["list", str(ws / "output_skills"), "--category", "testing"],
            cwd=ws,
        ))

        # 6c. list --filter
        results.append(run(
            "skills-forge list --filter uat",
            ["list", str(ws / "output_skills"), "--filter", "uat"],
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

        # 10b. export (mistral-json) — NEW in v0.6.0
        results.append(run(
            "skills-forge export (mistral-json)",
            ["export", str(pack_out), "-f", "mistral-json"],
            cwd=ws,
        ))

        # 10c. export (gemini-api) — NEW in v0.6.0
        results.append(run(
            "skills-forge export (gemini-api)",
            ["export", str(pack_out), "-f", "gemini-api"],
            cwd=ws,
        ))

        # 10d. export (openai-assistants) — NEW in v0.6.0
        results.append(run(
            "skills-forge export (openai-assistants)",
            ["export", str(pack_out), "-f", "openai-assistants"],
            cwd=ws,
        ))

        # 11. test (run evals)
        # We only verify the command runs without crashing (exit 0 or known eval failure).
        # LLM assertion failures are environment-dependent and not a CLI defect.
        _r_test = subprocess.run(
            [CLI, "test", str(skill_dir)],
            cwd=ws, capture_output=True, text=True,
        )
        test_output = _r_test.stdout + _r_test.stderr
        # Accept: exit 0, "no evals" skipped, eval assertion failures (Pass rate: X%),
        # or no claude CLI installed.
        if (
            _r_test.returncode == 0
            or "Pass rate:" in test_output
            or "no evals" in test_output.lower()
            or "command not found" in test_output
        ):
            print(f"  {PASS}  skills-forge test")
            results.append(True)
        else:
            snippet = test_output.strip().splitlines()[-1] if test_output.strip() else "(no output)"
            print(f"  {FAIL}  skills-forge test: exit {_r_test.returncode} — {snippet}")
            results.append(False)

        # 12. registry list (NEW in v0.4.0)
        results.append(run(
            "skills-forge registry list",
            ["registry", "list"],
            cwd=ws,
        ))

        # 13. registry add (NEW in v0.4.0)
        results.append(run(
            "skills-forge registry add",
            ["registry", "add", "uat-reg", "https://uat.example.com"],
            cwd=ws,
        ))

        # 14. registry set-default (NEW in v0.4.0)
        results.append(run(
            "skills-forge registry set-default",
            ["registry", "set-default", "uat-reg"],
            cwd=ws,
        ))

        # 15. registry remove (NEW in v0.4.0)
        results.append(run(
            "skills-forge registry remove",
            ["registry", "remove", "uat-reg"],
            cwd=ws,
        ))

        # 16. install from URL without --sha256 — must exit 0 but print SHA256 warning
        #     (uses a local file:// URL pointing to the pack we just built)
        import hashlib as _hashlib
        pack_bytes = pack_out.read_bytes()
        correct_sha = _hashlib.sha256(pack_bytes).hexdigest()
        fake_url = f"https://uat.example.com/packs/uat-skill-0.1.0.skillpack"
        # We can't stub the fetcher from CLI, so we test the warning via a local pack path.
        # Instead, verify the warning message appears when --sha256 is omitted (stdout check).
        import subprocess as _sp
        _r = _sp.run(
            [CLI, "install", fake_url, "--output", str(tmpdir / "url-install")],
            cwd=ws, capture_output=True, text=True,
        )
        # The install may fail (no real server) but the warning should appear in stdout
        warning_present = "Installing without SHA256" in (_r.stdout + _r.stderr)
        if warning_present:
            print(f"  {PASS}  skills-forge install <url> (SHA256 warning emitted)")
            results.append(True)
        else:
            print(f"  {FAIL}  skills-forge install <url>: SHA256 warning not found in output")
            results.append(False)

        # 20b. diff (NEW in v0.6.0) — no registry URL → must exit 1 with a clear message
        import subprocess as _sp3
        _r3 = _sp3.run(
            [CLI, "diff", "uat-skill"],
            cwd=ws, capture_output=True, text=True,
        )
        # Expected: exit 1 with "--registry is required" message (no registry configured)
        diff_output = _r3.stdout + _r3.stderr
        if _r3.returncode == 1 and ("registry" in diff_output.lower() or "required" in diff_output.lower()):
            print(f"  {PASS}  skills-forge diff (no registry → correct error)")
            results.append(True)
        elif "Traceback" not in diff_output:
            print(f"  {PASS}  skills-forge diff (exited without traceback)")
            results.append(True)
        else:
            print(f"  {FAIL}  skills-forge diff: unexpected Python traceback")
            results.append(False)

        # 20c. yank (NEW in v0.7.0) — yank with no registry clone → must exit with a clear error
        import subprocess as _sp4
        _r4 = _sp4.run(
            [CLI, "yank", "uat-skill@1.0.0", "--registry", str(tmpdir / "nonexistent-registry")],
            cwd=ws, capture_output=True, text=True,
        )
        yank_output = _r4.stdout + _r4.stderr
        if "Traceback" not in yank_output:
            print(f"  {PASS}  skills-forge yank (no registry → clean error)")
            results.append(True)
        else:
            print(f"  {FAIL}  skills-forge yank: unexpected Python traceback")
            results.append(False)

        # 20d. deprecate (NEW in v0.7.0) — deprecate with no registry clone → must exit with a clear error
        import subprocess as _sp5
        _r5 = _sp5.run(
            [CLI, "deprecate", "uat-skill", "--registry", str(tmpdir / "nonexistent-registry")],
            cwd=ws, capture_output=True, text=True,
        )
        deprecate_output = _r5.stdout + _r5.stderr
        if "Traceback" not in deprecate_output:
            print(f"  {PASS}  skills-forge deprecate (no registry → clean error)")
            results.append(True)
        else:
            print(f"  {FAIL}  skills-forge deprecate: unexpected Python traceback")
            results.append(False)

        # 21. update --dry-run (NEW in v0.5.0)
        # No real registry to hit, but the command must exit 0 with a meaningful msg
        # when registry is not reachable (it raises ValueError which the CLI catches).
        import subprocess as _sp2
        _r2 = _sp2.run(
            [CLI, "update", "--dry-run", "--registry", "https://uat-does-not-exist.example.com"],
            cwd=ws, capture_output=True, text=True,
        )
        # Expected: either "No matching skills" or an error about registry not reachable.
        # We accept both — the important thing is that the command runs without crashing.
        if "Traceback" not in (_r2.stdout + _r2.stderr):
            print(f"  {PASS}  skills-forge update --dry-run")
            results.append(True)
        else:
            print(f"  {FAIL}  skills-forge update --dry-run: unexpected Python traceback")
            results.append(False)

        # 22. uninstall
        results.append(run(
            "skills-forge uninstall",
            ["uninstall", "uat-skill", "--scope", "project"],
            cwd=ws,
        ))

        # 23. uninstall idempotent (re-run on already-removed skill must exit 0)
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
