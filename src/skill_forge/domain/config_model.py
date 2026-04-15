"""Domain model for skills-forge configuration (~/.skills-forge/config.toml).

The config is intentionally simple: a list of named registries, each with a
URL and an optional auth token.  The default registry and default install target
can be set globally so CLI flags can be omitted in everyday use.

All I/O lives in the infrastructure layer (``TomlConfigRepository``).  This
module is zero-dependency pure Python.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

DEFAULT_REGISTRY_NAME = "public"
DEFAULT_TARGET = "claude"

# The public registry shipped with skills-forge
PUBLIC_REGISTRY_URL = (
    "https://raw.githubusercontent.com/ficiverson/skill-registry/main"
)


@dataclass
class RegistryConfig:
    """Configuration for a single named registry."""

    name: str
    url: str
    token: str = ""  # raw value; may contain ${ENV_VAR} placeholders

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("RegistryConfig name cannot be empty")
        if not self.url or not self.url.strip():
            raise ValueError("RegistryConfig url cannot be empty")

    @property
    def resolved_token(self) -> str:
        """Return the token with ``${VAR}`` / ``$VAR`` env-var placeholders expanded.

        Unknown variables are left as-is (not replaced with empty string) so
        mis-configured tokens surface an obvious placeholder rather than silently
        authenticating as anonymous.
        """
        return _expand_env(self.token)


@dataclass
class ForgeConfig:
    """Top-level config for the skills-forge CLI.

    ``registries``  — named registry definitions (order preserved)
    ``default_registry`` — name of the registry used when ``-r``/``-u`` are omitted
    ``default_target``   — install target used when ``--target`` is omitted
    """

    registries: list[RegistryConfig] = field(default_factory=list)
    default_registry: str = DEFAULT_REGISTRY_NAME
    default_target: str = DEFAULT_TARGET

    # ── convenience accessors ─────────────────────────────────────────────────

    def get_registry(self, name: str) -> RegistryConfig | None:
        for reg in self.registries:
            if reg.name == name:
                return reg
        return None

    def get_default_registry(self) -> RegistryConfig | None:
        return self.get_registry(self.default_registry)

    def add_registry(self, name: str, url: str, token: str = "") -> None:
        if self.get_registry(name) is not None:
            raise ValueError(f"Registry '{name}' already exists. Remove it first.")
        self.registries.append(RegistryConfig(name=name, url=url, token=token))

    def remove_registry(self, name: str) -> None:
        before = len(self.registries)
        self.registries = [r for r in self.registries if r.name != name]
        if len(self.registries) == before:
            raise KeyError(f"Registry '{name}' not found.")

    def set_default(self, name: str) -> None:
        if self.get_registry(name) is None:
            raise KeyError(
                f"Registry '{name}' not found. "
                f"Add it first with: skills-forge registry add {name} <url>"
            )
        self.default_registry = name

    @classmethod
    def with_public_registry(cls) -> ForgeConfig:
        """Return a minimal config pre-seeded with the public registry."""
        return cls(
            registries=[
                RegistryConfig(
                    name=DEFAULT_REGISTRY_NAME,
                    url=PUBLIC_REGISTRY_URL,
                )
            ],
            default_registry=DEFAULT_REGISTRY_NAME,
            default_target=DEFAULT_TARGET,
        )


# ── helpers ───────────────────────────────────────────────────────────────────


def _expand_env(value: str) -> str:
    """Expand ``${VAR}`` and ``$VAR`` patterns using environment variables.

    Unknown variables are left as-is to surface mis-configurations clearly.
    """
    def replacer(m: re.Match[str]) -> str:
        var = m.group(1) or m.group(2)
        return os.environ.get(var, m.group(0))

    return re.sub(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)", replacer, value)
