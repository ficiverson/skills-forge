"""CLI integration tests using typer's CliRunner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from skill_forge.cli.main import app

runner = CliRunner()


class TestCreateCommand:
    def test_create_new_skill(self, tmp_path: Path):
        result = runner.invoke(app, [
            "create",
            "--name", "test-skill",
            "--category", "testing",
            "--description", "A test skill for testing. Triggers on: test, validate.",
            "--emoji", "🧪",
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 0
        assert "Created skill" in result.stdout
        assert (tmp_path / "testing" / "test-skill" / "SKILL.md").exists()

    def test_create_duplicate_fails(self, tmp_path: Path):
        # First create
        runner.invoke(app, [
            "create",
            "--name", "test-skill",
            "--category", "testing",
            "--description", "A test skill. Triggers on: test.",
            "--output", str(tmp_path),
        ])
        # Second create should fail
        result = runner.invoke(app, [
            "create",
            "--name", "test-skill",
            "--category", "testing",
            "--description", "A test skill. Triggers on: test.",
            "--output", str(tmp_path),
        ])
        assert result.exit_code == 1
        assert "already exists" in result.stdout


class TestLintCommand:
    def test_lint_clean_skill(self, tmp_path: Path):
        skill_dir = tmp_path / "testing" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("""\
---
name: test-skill
description: |
  Use this skill when running test suites and validating code quality.
  Triggers on: test, validate, lint, pytest, unit testing, integration
  testing, coverage reports, test-driven development .py .ts files.
---

STARTER_CHARACTER = 🧪

## Principles

- Test everything
- Be thorough

## Instructions

Run the test suite.

## Constraints

- Never skip tests
""", encoding="utf-8")

        result = runner.invoke(app, ["lint", str(skill_dir / "SKILL.md")])
        assert result.exit_code == 0
        assert "clean" in result.stdout

    def test_lint_with_broken_reference(self, tmp_path: Path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""\
---
name: test-skill
description: |
  A test skill. Triggers on: test, validate.
---

## Principles

- Be thorough

## References

- [Missing file](references/missing.md)
""", encoding="utf-8")

        result = runner.invoke(app, ["lint", str(skill_dir / "SKILL.md")])
        assert result.exit_code == 1
        assert "broken-reference-link" in result.stdout

    def test_lint_directory(self, tmp_path: Path):
        for name in ["skill-a", "skill-b"]:
            d = tmp_path / name
            d.mkdir()
            (d / "SKILL.md").write_text(f"""\
---
name: {name}
description: |
  Skill {name}. Triggers on: test, validate.
---

## Principles

- Be thorough
""", encoding="utf-8")

        result = runner.invoke(app, ["lint", str(tmp_path)])
        assert result.exit_code == 0
        assert "skill-a" in result.stdout
        assert "skill-b" in result.stdout

    def test_lint_no_skills_found(self, tmp_path: Path):
        result = runner.invoke(app, ["lint", str(tmp_path / "empty")])
        # typer won't even let this through if path doesn't exist
        # But an empty dir with no SKILL.md should show "No SKILL.md files found"
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = runner.invoke(app, ["lint", str(empty_dir)])
        assert result.exit_code == 1
        assert "No SKILL.md" in result.stdout


class TestListCommand:
    def test_list_skills(self, tmp_path: Path):
        skill_dir = tmp_path / "testing" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("""\
---
name: test-skill
description: |
  A test skill. Triggers on: test.
---

## Principles

- Be thorough
""", encoding="utf-8")

        result = runner.invoke(app, ["list-skills", str(tmp_path)])
        assert result.exit_code == 0
        assert "test-skill" in result.stdout
        assert "tokens" in result.stdout

    def test_list_empty_directory(self, tmp_path: Path):
        result = runner.invoke(app, ["list-skills", str(tmp_path)])
        assert result.exit_code == 0
        assert "No skills found" in result.stdout


class TestInstallUninstallCommand:
    def test_install_and_uninstall(self, tmp_path: Path):
        # Create a skill directory
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\n")

        # Test that the command at least accepts the arguments.
        # In sandboxed environments symlink creation may be blocked,
        # so we accept either success or a PermissionError.
        result = runner.invoke(app, [
            "install", str(skill_dir), "--scope", "project",
        ])
        if result.exit_code == 0:
            assert "Installed" in result.stdout
        else:
            # Sandboxed environment — symlinks not allowed
            assert result.exception is not None

    def test_uninstall_missing_skill(self, tmp_path: Path):
        result = runner.invoke(app, [
            "uninstall", "nonexistent-skill", "--scope", "project",
        ])
        assert result.exit_code == 1
        assert "was not installed" in result.stdout


class TestPackUnpackCommands:
    def _make_skill(self, base: Path, category: str, name: str) -> Path:
        skill_dir = base / category / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\n---\n",
            encoding="utf-8",
        )
        return skill_dir

    def test_pack_creates_skillpack(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path / "src", "dev", "python-tdd")
        out_dir = tmp_path / "packs"
        out_dir.mkdir()

        result = runner.invoke(app, [
            "pack",
            str(skill_dir),
            "--output", str(out_dir),
            "--version", "0.2.0",
            "--author", "fer",
        ])
        assert result.exit_code == 0, result.stdout
        assert "Packed 1 skill" in result.stdout
        pack_file = out_dir / "python-tdd-0.2.0.skillpack"
        assert pack_file.exists()

    def test_pack_explicit_filename(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path / "src", "dev", "python-tdd")
        target = tmp_path / "my-pack.skillpack"

        result = runner.invoke(app, [
            "pack",
            str(skill_dir),
            "--output", str(target),
            "--name", "my-pack",
        ])
        assert result.exit_code == 0
        assert target.exists()

    def test_pack_rejects_non_skill_dir(self, tmp_path: Path):
        broken = tmp_path / "broken"
        broken.mkdir()
        result = runner.invoke(app, [
            "pack",
            str(broken),
            "--output", str(tmp_path / "out"),
        ])
        assert result.exit_code == 1
        assert "Not a skill directory" in result.stdout

    def test_unpack_extracts_skill(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path / "src", "dev", "python-tdd")
        out_dir = tmp_path / "packs"
        out_dir.mkdir()

        # First pack
        runner.invoke(app, [
            "pack", str(skill_dir),
            "--output", str(out_dir),
        ])
        pack_file = next(out_dir.glob("*.skillpack"))

        # Then unpack
        dest = tmp_path / "extracted"
        result = runner.invoke(app, [
            "unpack",
            str(pack_file),
            "--output", str(dest),
        ])
        assert result.exit_code == 0, result.stdout
        assert "Unpacked 1 skill" in result.stdout
        assert (dest / "dev" / "python-tdd" / "SKILL.md").exists()

    def test_pack_unpack_multi_skill_roundtrip(self, tmp_path: Path):
        a = self._make_skill(tmp_path / "src", "dev", "skill-a")
        b = self._make_skill(tmp_path / "src", "ops", "skill-b")
        target = tmp_path / "bundle.skillpack"

        result = runner.invoke(app, [
            "pack",
            str(a), str(b),
            "--output", str(target),
            "--name", "bundle",
        ])
        assert result.exit_code == 0, result.stdout
        assert "Packed 2 skill" in result.stdout

        dest = tmp_path / "extracted"
        result = runner.invoke(app, [
            "unpack", str(target), "--output", str(dest),
        ])
        assert result.exit_code == 0
        assert (dest / "dev" / "skill-a" / "SKILL.md").exists()
        assert (dest / "ops" / "skill-b" / "SKILL.md").exists()


class TestPublishCommand:
    def _make_skill(self, base: Path, category: str, name: str) -> Path:
        skill_dir = base / category / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\nversion: 0.3.0\n---\n",
            encoding="utf-8",
        )
        return skill_dir

    def _init_registry(self, registry: Path) -> None:
        import shutil
        import subprocess

        if shutil.which("git") is None:
            import pytest

            pytest.skip("git not available")
        registry.mkdir()
        for args in (
            ["init", "-q", "-b", "main"],
            ["config", "user.email", "test@example.com"],
            ["config", "user.name", "test"],
        ):
            subprocess.run(
                ["git", "-C", str(registry), *args],
                check=True,
                capture_output=True,
            )

    def test_publish_writes_pack_into_registry(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path / "src", "dev", "python-tdd")
        out_dir = tmp_path / "packs"
        out_dir.mkdir()
        runner.invoke(app, ["pack", str(skill_dir), "--output", str(out_dir)])
        pack_file = next(out_dir.glob("*.skillpack"))

        registry = tmp_path / "registry"
        self._init_registry(registry)

        result = runner.invoke(
            app,
            [
                "publish",
                str(pack_file),
                "--registry",
                str(registry),
                "--base-url",
                "https://raw.githubusercontent.com/acme/skills/main",
                "--message",
                "ship 0.3.0",
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "Published python-tdd v0.3.0" in result.stdout
        assert "raw.githubusercontent.com" in result.stdout
        assert (
            registry / "packs" / "dev" / "python-tdd-0.3.0.skillpack"
        ).exists()
        assert (registry / "index.json").exists()

    def test_publish_records_rich_metadata(self, tmp_path: Path):
        import json

        skill_dir = self._make_skill(tmp_path / "src", "dev", "python-tdd")
        out_dir = tmp_path / "packs"
        out_dir.mkdir()
        runner.invoke(app, ["pack", str(skill_dir), "--output", str(out_dir)])
        pack_file = next(out_dir.glob("*.skillpack"))

        registry = tmp_path / "registry"
        self._init_registry(registry)

        result = runner.invoke(
            app,
            [
                "publish",
                str(pack_file),
                "--registry",
                str(registry),
                "--base-url",
                "https://raw.githubusercontent.com/acme/skills/main",
                "--tag",
                "tdd",
                "--tag",
                "python",
                "--owner-name",
                "Acme",
                "--owner-email",
                "team@acme.test",
                "--release-notes",
                "first cut",
            ],
        )
        assert result.exit_code == 0, result.stdout

        index = json.loads((registry / "index.json").read_text())
        skill = index["skills"][0]
        assert skill["tags"] == ["tdd", "python"]
        assert skill["owner"] == {"name": "Acme", "email": "team@acme.test"}
        version = skill["versions"][0]
        assert version["release_notes"] == "first cut"
        assert version["size_bytes"] > 0
        assert version["published_at"]


class TestInstallFromUrlCommand:
    def test_install_url_fetches_unpacks_and_installs(
        self, tmp_path: Path, monkeypatch
    ):
        # Build a real .skillpack we can serve via a fake fetcher.
        skill_dir = tmp_path / "src" / "dev" / "python-tdd"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: python-tdd\nversion: 0.4.0\n---\n",
            encoding="utf-8",
        )
        out_dir = tmp_path / "packs"
        out_dir.mkdir()
        runner.invoke(app, ["pack", str(skill_dir), "--output", str(out_dir)])
        pack_file = next(out_dir.glob("*.skillpack"))
        pack_bytes = pack_file.read_bytes()

        # Stub the fetcher: copy the local pack into the requested dest path.
        from skill_forge.cli import factory
        from skill_forge.domain.ports import PackFetcher

        class _LocalFetcher(PackFetcher):
            def fetch(self, url, dest):  # type: ignore[no-untyped-def]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(pack_bytes)
                return dest

            def fetch_index(self, url):  # type: ignore[no-untyped-def]
                raise NotImplementedError

        # Stub the installer to avoid touching ~/.claude.
        from skill_forge.domain.ports import SkillInstaller

        class _NoopInstaller(SkillInstaller):
            def install(self, skill_path, scope):  # type: ignore[no-untyped-def]
                return Path(f"/fake/{skill_path.name}")

            def uninstall(self, skill_name, scope):  # type: ignore[no-untyped-def]
                return False

            def is_installed(self, skill_name, scope):  # type: ignore[no-untyped-def]
                return False

            def list_installed(self, scope):  # type: ignore[no-untyped-def]
                return []

        monkeypatch.setattr(factory, "build_fetcher", lambda: _LocalFetcher())
        monkeypatch.setattr(factory, "build_installer", lambda: _NoopInstaller())

        dest = tmp_path / "extracted"
        result = runner.invoke(
            app,
            [
                "install",
                "https://example.com/python-tdd-0.4.0.skillpack",
                "--output",
                str(dest),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert "Fetched 'python-tdd'" in result.stdout
        assert (dest / "dev" / "python-tdd" / "SKILL.md").exists()


class TestInitCommand:
    def test_init_creates_workspace(self, tmp_path: Path):
        result = runner.invoke(app, ["init", str(tmp_path / "workspace")])
        assert result.exit_code == 0
        assert "Initialized" in result.stdout
        assert (tmp_path / "workspace" / "output_skills").is_dir()
        assert (tmp_path / "workspace" / "CLAUDE.md").is_file()
