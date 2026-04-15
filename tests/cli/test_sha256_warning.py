"""BKL-013: SHA256 warning on remote install + mismatch error E2E tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

from typer.testing import CliRunner

from skill_forge.cli.main import app

runner = CliRunner()


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_pack(tmp_path: Path) -> tuple[Path, str]:
    """Build a minimal .skillpack and return (pack_path, sha256_hex)."""
    skill_dir = tmp_path / "src" / "dev" / "sha-test"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: sha-test\nversion: 0.1.0\ndescription: |\n"
        "  SHA test skill. Triggers on: sha.\n---\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "packs"
    out_dir.mkdir()
    r = runner.invoke(app, ["pack", str(skill_dir), "--output", str(out_dir)])
    assert r.exit_code == 0, r.stdout
    pack_file = next(out_dir.glob("*.skillpack"))
    sha = hashlib.sha256(pack_file.read_bytes()).hexdigest()
    return pack_file, sha


def _stub_fetcher_and_installer(monkeypatch, pack_bytes: bytes) -> None:
    from skill_forge.cli import factory
    from skill_forge.domain.ports import PackFetcher, SkillInstaller

    class _LocalFetcher(PackFetcher):
        def fetch(self, url, dest):  # type: ignore[no-untyped-def]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(pack_bytes)
            return dest

        def fetch_index(self, url):  # type: ignore[no-untyped-def]
            raise NotImplementedError

    class _NoopInstaller(SkillInstaller):
        def install(self, skill_path, scope, target=None):  # type: ignore[no-untyped-def]
            return [Path(f"/fake/{skill_path.name}")]

        def uninstall(self, skill_name, scope, target=None):  # type: ignore[no-untyped-def]
            return []

        def is_installed(self, skill_name, scope):  # type: ignore[no-untyped-def]
            return False

        def list_installed(self, scope):  # type: ignore[no-untyped-def]
            return []

        def scan_all_targets(self, scope):  # type: ignore[no-untyped-def]
            from skill_forge.domain.model import InstallTarget
            return {InstallTarget.CLAUDE: []}

    monkeypatch.setattr(factory, "build_fetcher", lambda url="": _LocalFetcher())
    monkeypatch.setattr(factory, "build_installer", lambda: _NoopInstaller())


# ── tests ─────────────────────────────────────────────────────────────────────


class TestSha256Warning:
    def test_warning_when_no_sha256_provided(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Installing from URL without --sha256 prints a visible warning."""
        pack_file, _ = _make_pack(tmp_path)
        _stub_fetcher_and_installer(monkeypatch, pack_file.read_bytes())

        result = runner.invoke(
            app,
            [
                "install",
                "https://example.com/sha-test-0.1.0.skillpack",
                "--output",
                str(tmp_path / "out"),
            ],
        )
        assert result.exit_code == 0, result.output
        # Warning is printed (to stderr, but CliRunner merges by default)
        assert "Installing without SHA256" in result.output

    def test_no_warning_when_sha256_provided(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """When --sha256 is supplied, no warning is printed."""
        pack_file, sha = _make_pack(tmp_path)
        _stub_fetcher_and_installer(monkeypatch, pack_file.read_bytes())

        result = runner.invoke(
            app,
            [
                "install",
                "https://example.com/sha-test-0.1.0.skillpack",
                "--output",
                str(tmp_path / "out"),
                "--sha256",
                sha,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Installing without SHA256" not in result.output

    def test_wrong_sha256_fails(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Providing a wrong --sha256 exits non-zero with a clear error."""
        pack_file, _ = _make_pack(tmp_path)
        _stub_fetcher_and_installer(monkeypatch, pack_file.read_bytes())

        wrong_sha = "a" * 64  # valid-looking but wrong digest

        result = runner.invoke(
            app,
            [
                "install",
                "https://example.com/sha-test-0.1.0.skillpack",
                "--output",
                str(tmp_path / "out"),
                "--sha256",
                wrong_sha,
            ],
        )
        # Should fail
        assert result.exit_code != 0

    def test_correct_sha256_passes(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Providing the correct --sha256 succeeds."""
        pack_file, sha = _make_pack(tmp_path)
        _stub_fetcher_and_installer(monkeypatch, pack_file.read_bytes())

        result = runner.invoke(
            app,
            [
                "install",
                "https://example.com/sha-test-0.1.0.skillpack",
                "--output",
                str(tmp_path / "out"),
                "--sha256",
                sha,
            ],
        )
        assert result.exit_code == 0, result.stdout
