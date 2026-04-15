"""Tests for ForgeConfig domain model and env-var expansion."""

from __future__ import annotations

import pytest

from skill_forge.domain.config_model import (
    DEFAULT_REGISTRY_NAME,
    ForgeConfig,
    RegistryConfig,
    _expand_env,
)

# ── _expand_env ───────────────────────────────────────────────────────────────


class TestExpandEnv:
    def test_no_placeholders(self) -> None:
        assert _expand_env("https://example.com") == "https://example.com"

    def test_curly_placeholder_known(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "secret123")
        assert _expand_env("${MY_TOKEN}") == "secret123"

    def test_dollar_placeholder_known(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "abc")
        assert _expand_env("$MY_TOKEN") == "abc"

    def test_unknown_var_left_as_is(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NONEXISTENT_VAR_XYZ", raising=False)
        result = _expand_env("${NONEXISTENT_VAR_XYZ}")
        assert result == "${NONEXISTENT_VAR_XYZ}"

    def test_mixed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TOKEN", "tok")
        result = _expand_env("Bearer ${TOKEN}")
        assert result == "Bearer tok"


# ── RegistryConfig ────────────────────────────────────────────────────────────


class TestRegistryConfig:
    def test_basic(self) -> None:
        r = RegistryConfig(name="public", url="https://example.com")
        assert r.name == "public"
        assert r.resolved_token == ""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError):
            RegistryConfig(name="", url="https://x.com")

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValueError):
            RegistryConfig(name="x", url="")

    def test_resolved_token_expands_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "resolved")
        r = RegistryConfig(name="r", url="u", token="${MY_TOKEN}")
        assert r.resolved_token == "resolved"


# ── ForgeConfig ───────────────────────────────────────────────────────────────


class TestForgeConfig:
    def _cfg(self) -> ForgeConfig:
        return ForgeConfig(
            registries=[
                RegistryConfig(name="public", url="https://pub.example.com"),
                RegistryConfig(name="internal", url="https://priv.example.com"),
            ],
            default_registry="public",
        )

    def test_get_registry_found(self) -> None:
        assert self._cfg().get_registry("internal") is not None

    def test_get_registry_not_found(self) -> None:
        assert self._cfg().get_registry("missing") is None

    def test_get_default_registry(self) -> None:
        cfg = self._cfg()
        default = cfg.get_default_registry()
        assert default is not None
        assert default.name == "public"

    def test_add_registry(self) -> None:
        cfg = self._cfg()
        cfg.add_registry("new", "https://new.example.com")
        assert cfg.get_registry("new") is not None

    def test_add_duplicate_raises(self) -> None:
        cfg = self._cfg()
        with pytest.raises(ValueError, match="already exists"):
            cfg.add_registry("public", "https://other.com")

    def test_remove_registry(self) -> None:
        cfg = self._cfg()
        cfg.remove_registry("internal")
        assert cfg.get_registry("internal") is None

    def test_remove_nonexistent_raises(self) -> None:
        cfg = self._cfg()
        with pytest.raises(KeyError):
            cfg.remove_registry("ghost")

    def test_set_default(self) -> None:
        cfg = self._cfg()
        cfg.set_default("internal")
        assert cfg.default_registry == "internal"

    def test_set_default_nonexistent_raises(self) -> None:
        cfg = self._cfg()
        with pytest.raises(KeyError, match="not found"):
            cfg.set_default("ghost")

    def test_with_public_registry(self) -> None:
        cfg = ForgeConfig.with_public_registry()
        assert cfg.default_registry == DEFAULT_REGISTRY_NAME
        assert len(cfg.registries) == 1
        assert cfg.registries[0].name == DEFAULT_REGISTRY_NAME
