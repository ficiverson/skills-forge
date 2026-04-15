"""Tests for TomlConfigRepository."""

from __future__ import annotations

from pathlib import Path

import pytest

from skill_forge.domain.config_model import ForgeConfig, RegistryConfig
from skill_forge.infrastructure.adapters.toml_config_repository import (
    TomlConfigRepository,
)


@pytest.fixture
def repo(tmp_path: Path) -> TomlConfigRepository:
    return TomlConfigRepository(path=tmp_path / ".skills-forge" / "config.toml")


class TestLoad:
    def test_missing_file_returns_default(self, repo: TomlConfigRepository) -> None:
        cfg = repo.load()
        assert cfg.default_registry == "public"
        assert len(cfg.registries) >= 1

    def test_invalid_toml_raises(self, repo: TomlConfigRepository, tmp_path: Path) -> None:
        config_path = tmp_path / ".skills-forge" / "config.toml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("{bad toml [[[", encoding="utf-8")
        with pytest.raises(ValueError, match="parse config"):
            repo.load()


class TestRoundTrip:
    def test_save_and_load(self, repo: TomlConfigRepository) -> None:
        cfg = ForgeConfig(
            registries=[
                RegistryConfig(name="public", url="https://pub.example.com"),
                RegistryConfig(name="internal", url="https://priv.example.com", token="${MY_TOK}"),
            ],
            default_registry="internal",
            default_target="gemini",
        )
        repo.save(cfg)
        loaded = repo.load()
        assert loaded.default_registry == "internal"
        assert loaded.default_target == "gemini"
        assert len(loaded.registries) == 2

        pub = loaded.get_registry("public")
        assert pub is not None
        assert pub.url == "https://pub.example.com"

        internal = loaded.get_registry("internal")
        assert internal is not None
        assert internal.token == "${MY_TOK}"

    def test_creates_parent_dirs(self, repo: TomlConfigRepository) -> None:
        cfg = ForgeConfig.with_public_registry()
        repo.save(cfg)
        assert repo.path.exists()

    def test_empty_registries_roundtrip(self, repo: TomlConfigRepository) -> None:
        cfg = ForgeConfig(registries=[], default_registry="public")
        repo.save(cfg)
        loaded = repo.load()
        assert loaded.registries == []
