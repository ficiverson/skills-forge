"""Ports (interfaces) for the domain layer.

Following the Dependency Inversion Principle, the domain defines
what it needs via abstract interfaces. Infrastructure provides
the concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from skill_forge.domain.model import (
    ExportFormat,
    InstallTarget,
    PublishMetadata,
    PublishResult,
    RegistryIndex,
    Skill,
    SkillPackManifest,
    SkillScope,
)

# Module-level singleton: avoids B008 (function call in argument default).
_DEFAULT_PUBLISH_METADATA = PublishMetadata()


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
    """Port: install/uninstall skills into agent-CLI tool directories.

    All supported tools share the agentskills.io SKILL.md format.
    ``target`` selects which tool's directory receives the skill;
    ``InstallTarget.ALL`` writes to every applicable directory at once.
    ``install`` always returns a list so callers handle both cases uniformly.
    """

    @abstractmethod
    def install(
        self,
        skill_path: Path,
        scope: SkillScope,
        target: InstallTarget = InstallTarget.CLAUDE,
    ) -> list[Path]:
        """Install a skill and return all installation paths created."""

    @abstractmethod
    def uninstall(
        self,
        skill_name: str,
        scope: SkillScope,
        target: InstallTarget = InstallTarget.ALL,
    ) -> list[Path]:
        """Uninstall a skill. Returns the list of paths that were removed."""

    @abstractmethod
    def is_installed(self, skill_name: str, scope: SkillScope) -> bool:
        """Check if a skill is currently installed."""

    @abstractmethod
    def list_installed(self, scope: SkillScope) -> list[Path]:
        """List all installed skill paths for a given scope."""

    @abstractmethod
    def scan_all_targets(self, scope: SkillScope) -> dict[InstallTarget, list[Path]]:
        """Scan every target directory for the given scope.

        Returns a dict mapping each supported target to the list of installed
        skill directories/symlinks found there. Empty targets are included with
        an empty list. VSCODE is excluded at global scope (it has no global dir).
        """


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


class SkillPacker(ABC):
    """Port: bundle skills into a portable .skillpack archive (and back).

    A .skillpack is the unit of distribution for sharing skills across
    teams via Slack, Notion, email, or any other channel that can move
    a single file.
    """

    @abstractmethod
    def pack(
        self,
        skill_dirs: list[Path],
        manifest: SkillPackManifest,
        output_path: Path,
    ) -> Path:
        """Bundle one or more skill directories into a .skillpack file.

        Returns the path to the created pack.
        """

    @abstractmethod
    def unpack(self, pack_path: Path, dest_dir: Path) -> SkillPackManifest:
        """Extract a .skillpack into ``dest_dir`` (typically ``output_skills/``).

        Each skill is written to ``dest_dir/<category>/<name>/``.
        Returns the manifest read from the pack.
        """

    @abstractmethod
    def read_manifest(self, pack_path: Path) -> SkillPackManifest:
        """Read just the manifest from a .skillpack without extracting files."""


class PackPublisher(ABC):
    """Port: publish a .skillpack to a shared registry.

    Implementations decide where the pack physically lands. The git
    registry adapter copies into a local clone, updates ``index.json``,
    commits, and optionally pushes — turning any GitHub repo into a
    free CDN-backed skill registry over ``raw.githubusercontent.com``.
    """

    @abstractmethod
    def publish(
        self,
        pack_path: Path,
        manifest: SkillPackManifest,
        message: str,
        push: bool,
        metadata: PublishMetadata = _DEFAULT_PUBLISH_METADATA,
    ) -> PublishResult:
        """Publish ``pack_path`` and return where it can be downloaded from.

        ``metadata`` enriches the registry index with description, tags,
        owner, release notes, and lifecycle flags. Defaults preserve the
        old behaviour for callers that haven't been updated.
        """

    @abstractmethod
    def read_index(self) -> RegistryIndex:
        """Return the current index of the registry."""

    @abstractmethod
    def update_index(
        self,
        index: RegistryIndex,
        message: str,
        push: bool,
    ) -> bool:
        """Write an updated ``index`` to the registry.

        Commits and optionally pushes when the registry is a git repo and the
        index actually changed on disk.  Returns ``True`` when a commit was made.
        Callers typically read the index via ``read_index()``, apply a mutation
        (yank, deprecate, etc.), then hand the result back here.
        """


class SkillExporter(ABC):
    """Port: render a skill into a platform-native export format.

    Exporters are stateless transformers: they receive the parsed ``Skill``
    domain object, the raw SKILL.md body (frontmatter already stripped), and
    an ``output_dir`` to write into. They return the path of the artifact
    they created (file or directory). The use case remains format-agnostic.
    """

    #: The export format this exporter handles.
    format: ExportFormat

    @abstractmethod
    def export(self, skill: Skill, body: str, output_dir: Path) -> Path:
        """Export ``skill`` and return the path of the created artifact."""


class PackFetcher(ABC):
    """Port: download a .skillpack from a URL into a local file."""

    @abstractmethod
    def fetch(self, url: str, dest: Path) -> Path:
        """Download ``url`` to ``dest`` and return the local path."""

    @abstractmethod
    def fetch_index(self, url: str) -> RegistryIndex:
        """Download a registry ``index.json`` and parse it."""


class ClaudeRunner(ABC):
    """Port: send a prompt to Claude and return the text response.

    The concrete implementation in production shells out to ``claude -p``.
    Tests inject a stub that returns canned strings without any subprocess.
    """

    @abstractmethod
    def run(self, prompt: str, timeout: int = 120) -> str:
        """Send *prompt* to Claude and return the response text."""
