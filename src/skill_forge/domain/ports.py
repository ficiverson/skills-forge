"""Ports (interfaces) for the domain layer.

Following the Dependency Inversion Principle, the domain defines
what it needs via abstract interfaces. Infrastructure provides
the concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from skill_forge.domain.model import Skill, SkillScope


class SkillRepository(ABC):
    """Port: read and write skills to storage."""

    @abstractmethod
    def save(self, skill: Skill) -> Path:
        """Persist a skill and return the path where it was saved."""

    @abstractmethod
    def load(self, path: Path) -> Skill:
        """Load a skill from a given path."""

    @abstractmethod
    def exists(self, skill: Skill) -> bool:
        """Check if a skill already exists in the repository."""

    @abstractmethod
    def list_all(self) -> list[Skill]:
        """List all skills in the repository."""


class SkillInstaller(ABC):
    """Port: install/uninstall skills for Claude Code."""

    @abstractmethod
    def install(self, skill_path: Path, scope: SkillScope) -> Path:
        """Install a skill and return the installation path."""

    @abstractmethod
    def uninstall(self, skill_name: str, scope: SkillScope) -> bool:
        """Uninstall a skill. Returns True if it was installed."""

    @abstractmethod
    def is_installed(self, skill_name: str, scope: SkillScope) -> bool:
        """Check if a skill is currently installed."""

    @abstractmethod
    def list_installed(self, scope: SkillScope) -> list[Path]:
        """List all installed skill paths for a given scope."""


class SkillRenderer(ABC):
    """Port: render a Skill domain object into file content."""

    @abstractmethod
    def render_skill_md(self, skill: Skill) -> str:
        """Render the SKILL.md content for a skill."""

    @abstractmethod
    def render_reference(self, content: str, purpose: str) -> str:
        """Render a reference document."""


class SkillParser(ABC):
    """Port: parse file content into a Skill domain object."""

    @abstractmethod
    def parse(self, content: str, base_path: Path | None = None) -> Skill:
        """Parse SKILL.md content into a Skill object."""
