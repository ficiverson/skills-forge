"""Adapter: reads and writes ForgeConfig from ~/.skills-forge/config.toml.

Uses Python 3.11+ ``tomllib`` (stdlib) with a fallback to ``tomli`` for 3.10.
Writing uses a hand-rolled serialiser so we don't need an extra ``tomli-w``
dependency.
"""

from __future__ import annotations

import sys
from pathlib import Path

from skill_forge.domain.config_model import (
    DEFAULT_REGISTRY_NAME,
    DEFAULT_TARGET,
    PUBLIC_REGISTRY_URL,
    ForgeConfig,
    RegistryConfig,
)

# ── TOML read ──────────────────────────────────────────────────────────────────

if sys.version_info >= (3, 11):
    import tomllib
    _TOMLLIB_AVAILABLE = True
else:
    try:
        import tomli as tomllib  # third-party fallback for Python 3.10
        _TOMLLIB_AVAILABLE = True
    except ImportError:
        _TOMLLIB_AVAILABLE = False


def _read_toml(text: str) -> dict[str, object]:
    if _TOMLLIB_AVAILABLE:
        raw: dict[str, object] = tomllib.loads(text)
        return raw
    # Minimal fallback: only handles flat [section] tables and key = "value" lines
    parsed: dict[str, object] = {}
    section: dict[str, object] = {}
    current: str = ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            if current:
                parsed[current] = section
            current = line[1:-1]
            section = parsed.setdefault(current, {})  # type: ignore[assignment]
        elif "=" in line:
            k, _, v = line.partition("=")
            v = v.strip().strip('"').strip("'")
            section[k.strip()] = v
    if current:
        parsed[current] = section
    return parsed


# ── TOML write ─────────────────────────────────────────────────────────────────


def _dump_toml(config: ForgeConfig) -> str:
    lines: list[str] = [
        "# skills-forge configuration",
        "# https://skills-forge.io/docs/config",
        "",
        "[defaults]",
        f'registry = "{config.default_registry}"',
        f'target   = "{config.default_target}"',
        "",
        "[registries]",
        f'# {DEFAULT_REGISTRY_NAME} = "{PUBLIC_REGISTRY_URL}"',
        "",
    ]
    for reg in config.registries:
        lines.append(f"[registries.{reg.name}]")
        lines.append(f'url   = "{reg.url}"')
        if reg.token:
            lines.append(f'token = "{reg.token}"')
        lines.append("")
    return "\n".join(lines)


# ── repository ────────────────────────────────────────────────────────────────


class TomlConfigRepository:
    """Read and write ForgeConfig to/from a TOML file.

    The default path is ``~/.skills-forge/config.toml``.  Tests can inject a
    custom path via the constructor.
    """

    DEFAULT_CONFIG_PATH = Path.home() / ".skills-forge" / "config.toml"

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or self.DEFAULT_CONFIG_PATH

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> ForgeConfig:
        """Load config from disk.  Returns a default config if the file is absent."""
        if not self._path.exists():
            return ForgeConfig.with_public_registry()

        try:
            raw = _read_toml(self._path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(
                f"Failed to parse config at {self._path}: {exc}\n"
                "Fix the TOML syntax or delete the file to reset to defaults."
            ) from exc

        return self._parse(raw)

    def save(self, config: ForgeConfig) -> None:
        """Write config to disk, creating parent directories as needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(_dump_toml(config), encoding="utf-8")

    # ── private ───────────────────────────────────────────────────────────────

    def _parse(self, raw: dict) -> ForgeConfig:  # type: ignore[type-arg]
        defaults = raw.get("defaults", {})
        default_registry = defaults.get("registry", DEFAULT_REGISTRY_NAME)
        default_target = defaults.get("target", DEFAULT_TARGET)

        registries: list[RegistryConfig] = []
        raw_regs = raw.get("registries", {})

        for name, val in raw_regs.items():
            if isinstance(val, str):
                # Simple form: public = "https://..."
                registries.append(RegistryConfig(name=name, url=val))
            elif isinstance(val, dict):
                # Table form: [registries.internal] url = "..."  token = "..."
                url = val.get("url", "")
                token = val.get("token", "")
                if url:
                    registries.append(RegistryConfig(name=name, url=url, token=token))

        return ForgeConfig(
            registries=registries,
            default_registry=default_registry,
            default_target=default_target,
        )
