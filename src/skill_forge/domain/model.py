"""Domain models for skills-forge.

These are pure data structures with no dependencies on infrastructure.
They represent the core concepts of a Claude Code skill.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import ClassVar


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class SkillScope(Enum):
    GLOBAL = "global"
    PROJECT = "project"


class ExportFormat(Enum):
    """Target format for the ``export`` command.

    Agent-CLI tools (Claude Code, Gemini CLI, Codex, VS Code Copilot) all read
    SKILL.md natively — use ``install --target`` for those.  These export
    formats target the *chatbot / API* platforms that have no file-system skill
    directory and need the skill rendered into their native config shape.

    SYSTEM_PROMPT — plain Markdown suitable for any chat UI system field.
    GPT_JSON      — OpenAI Custom GPT / Assistants API ``instructions`` JSON.
    GEM_TXT       — Google Gemini Gem custom instructions plain-text file.
    BEDROCK_XML   — AWS Bedrock agent prompt XML template.
    MCP_SERVER    — Self-contained Python MCP Prompts server (single file).
    """

    SYSTEM_PROMPT = "system-prompt"
    GPT_JSON = "gpt-json"
    GEM_TXT = "gem-txt"
    BEDROCK_XML = "bedrock-xml"
    MCP_SERVER = "mcp-server"
    MISTRAL_JSON = "mistral-json"
    GEMINI_API = "gemini-api"
    OPENAI_ASSISTANTS = "openai-assistants"


class InstallTarget(Enum):
    """Which agent-CLI tool's skills directory to install into.

    All targets use the same SKILL.md format (agentskills.io open standard).
    The only difference is the destination path on disk.

    AGENTS is the universal cross-vendor alias (.agents/skills/) supported by
    every conforming tool at project scope.  At global scope each tool still
    has its own home-directory path, so ALL is provided for that case.
    """

    CLAUDE = "claude"    # ~/.claude/skills/  |  .claude/skills/
    GEMINI = "gemini"    # ~/.gemini/skills/  |  .gemini/skills/
    CODEX = "codex"      # ~/.codex/skills/   |  .codex/skills/
    VSCODE = "vscode"    # project-only       |  .github/skills/
    AGENTS = "agents"    # ~/.agents/skills/  |  .agents/skills/  (universal)
    ALL = "all"          # every applicable target for the chosen scope


@dataclass(frozen=True)
class SkillIdentity:
    """Value object: uniquely identifies a skill."""

    name: str
    category: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Skill name cannot be empty")
        if not self.category or not self.category.strip():
            raise ValueError("Skill category cannot be empty")

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "-")

    def __str__(self) -> str:
        return f"{self.category}/{self.slug}"


@dataclass(frozen=True)
class Description:
    """Value object: the trigger description shown to Claude.

    This is the single most important piece of a skill — it determines
    when Claude activates it. Keep it lean, precise, and third-person.
    """

    text: str

    @property
    def token_estimate(self) -> int:
        return len(self.text.split()) * 2

    @property
    def is_within_budget(self) -> bool:
        return self.token_estimate <= 150


@dataclass(frozen=True)
class StarterCharacter:
    """Value object: visual emoji confirming skill activation."""

    emoji: str

    def __str__(self) -> str:
        return self.emoji


@dataclass(frozen=True)
class Reference:
    """A supporting document loaded on-demand to save context."""

    path: PurePosixPath
    purpose: str

    @property
    def filename(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class Script:
    """An executable script bundled with the skill."""

    path: PurePosixPath
    description: str


@dataclass(frozen=True)
class Asset:
    """A static asset bundled with the skill (data files, images, templates)."""

    path: PurePosixPath
    description: str


@dataclass(frozen=True)
class Example:
    """An example output demonstrating the expected result format."""

    path: PurePosixPath
    description: str


@dataclass(frozen=True)
class Dependency:
    """A skill that this skill depends on for composed workflows."""

    skill_name: str
    reason: str

    def __post_init__(self) -> None:
        if not self.skill_name or not self.skill_name.strip():
            raise ValueError("Dependency skill_name cannot be empty")
        if " " in self.skill_name.strip():
            raise ValueError(
                f"Dependency skill_name '{self.skill_name}' must be "
                f"kebab-case (no spaces)"
            )


VALID_ASSERTION_TYPES: frozenset[str] = frozenset(
    {"contains", "not-contains", "regex", "llm-judge"}
)


@dataclass(frozen=True)
class EvalAssertion:
    """A single verifiable claim about a skill's output.

    ``type`` controls how the assertion is evaluated:

    contains      — output must contain ``expected`` as a literal substring.
    not-contains  — output must NOT contain ``expected`` as a literal substring.
    regex         — output must match the ``expected`` regular expression.
    llm-judge     — a secondary LLM call evaluates whether the output satisfies
                    the human-readable criterion in ``text``.  ``expected`` is
                    ignored for this type.
    """

    id: str
    text: str       # human-readable criterion (required for llm-judge, useful docs for all)
    type: str       # "contains" | "not-contains" | "regex" | "llm-judge"
    expected: str = ""  # pattern / substring for contains / not-contains / regex

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("EvalAssertion id cannot be empty")
        if not self.text or not self.text.strip():
            raise ValueError("EvalAssertion text cannot be empty")
        if self.type not in VALID_ASSERTION_TYPES:
            raise ValueError(
                f"EvalAssertion type must be one of "
                f"{sorted(VALID_ASSERTION_TYPES)}, got '{self.type}'"
            )


@dataclass(frozen=True)
class EvalCase:
    """A single test case for a skill.

    ``prompt``          — the user message sent to Claude.
    ``expected_output`` — human-readable summary of the ideal response (used by
                          llm-judge assertions and for documentation).
    ``assertions``      — ordered tuple of :class:`EvalAssertion` objects.
                          All assertions must pass for the case to be graded ✅.
    ``files``           — fixture paths relative to ``evals/fixtures/``.
                          The ``test`` command makes these available as context.
    """

    id: int
    prompt: str
    expected_output: str
    assertions: tuple[EvalAssertion, ...] = ()
    files: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.prompt or not self.prompt.strip():
            raise ValueError("EvalCase prompt cannot be empty")


@dataclass
class SkillContent:
    """The body of a SKILL.md — instructions that Claude follows."""

    principles: list[str] = field(default_factory=list)
    instructions: str = ""
    constraints: list[str] = field(default_factory=list)

    hints: str = ""

    @property
    def estimated_tokens(self) -> int:
        total_words = len(self.instructions.split())
        total_words += sum(len(p.split()) for p in self.principles)
        total_words += sum(len(c.split()) for c in self.constraints)
        if self.hints:
            total_words += len(self.hints.split())
        return total_words * 2


DEFAULT_SKILL_VERSION = "0.1.0"


@dataclass
class Skill:
    """Aggregate root: a complete Claude Code skill."""

    identity: SkillIdentity
    description: Description
    starter_character: StarterCharacter | None = None
    content: SkillContent = field(default_factory=SkillContent)
    references: list[Reference] = field(default_factory=list)
    scripts: list[Script] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    examples: list[Example] = field(default_factory=list)
    depends_on: list[Dependency] = field(default_factory=list)
    evals: list[EvalCase] = field(default_factory=list)
    requires_forge: str | None = None  # PEP 440 version specifier, e.g. ">=0.4.0"
    version: str = DEFAULT_SKILL_VERSION
    allowed_tools: list[str] = field(default_factory=list)  # agentskills.io allowed-tools

    @property
    def total_estimated_tokens(self) -> int:
        return self.description.token_estimate + self.content.estimated_tokens

    @property
    def has_references(self) -> bool:
        return len(self.references) > 0

    @property
    def has_scripts(self) -> bool:
        return len(self.scripts) > 0

    @property
    def has_assets(self) -> bool:
        return len(self.assets) > 0

    @property
    def has_examples(self) -> bool:
        return len(self.examples) > 0

    @property
    def has_dependencies(self) -> bool:
        return len(self.depends_on) > 0

    @property
    def has_evals(self) -> bool:
        return len(self.evals) > 0

    @property
    def has_allowed_tools(self) -> bool:
        return len(self.allowed_tools) > 0


@dataclass(frozen=True)
class SkillRef:
    """A reference to a skill inside a pack — category + name + version."""

    category: str
    name: str
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("SkillRef name cannot be empty")
        if not self.category or not self.category.strip():
            raise ValueError("SkillRef category cannot be empty")
        if not self.version or not self.version.strip():
            raise ValueError("SkillRef version cannot be empty")

    def __str__(self) -> str:
        return f"{self.category}/{self.name}@{self.version}"


@dataclass(frozen=True)
class Owner:
    """Value object: contact info for the maintainer of a published skill."""

    name: str
    email: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Owner name cannot be empty")


@dataclass(frozen=True)
class SkillPackManifest:
    """Metadata describing the contents of a .skillpack archive.

    A .skillpack is a zip file containing one or more skill directories
    plus a ``manifest.json`` at the root with this metadata. New optional
    fields (``tags``, ``owner``, ``deprecated``) let a pack carry the
    same metadata that ends up in a registry index, so ``publish`` can
    default from the manifest instead of asking for everything via CLI
    flags every time. Older packs without these fields keep working —
    the codec fills in safe defaults on read.
    """

    FORMAT_VERSION: ClassVar[str] = "1"

    name: str
    version: str
    author: str
    created_at: str  # ISO 8601 timestamp
    skills: tuple[SkillRef, ...]
    description: str = ""
    tags: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()  # install targets baked at pack time
    export_formats: tuple[str, ...] = ()  # export formats baked at pack time
    owner: Owner | None = None
    deprecated: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("SkillPackManifest name cannot be empty")
        if not self.version or not self.version.strip():
            raise ValueError("SkillPackManifest version cannot be empty")
        if not self.skills:
            raise ValueError("SkillPackManifest must reference at least one skill")

    @property
    def skill_count(self) -> int:
        return len(self.skills)


@dataclass(frozen=True)
class IndexedVersion:
    """One published version of a skill in a registry index.

    The required fields (version, path, sha256) form the minimum needed
    to download and verify a pack. The optional fields are publish-time
    metadata that helps teammates pick a version: when it shipped, how
    big it is, what changed, and whether it's been pulled.
    """

    version: str
    path: str  # repo-relative POSIX path, e.g. "packs/dev/python-tdd-0.2.0.skillpack"
    sha256: str  # hex digest of the .skillpack contents
    published_at: str = ""  # ISO 8601 timestamp; empty for older entries
    size_bytes: int = 0  # 0 means "unknown" (older entries)
    release_notes: str = ""
    yanked: bool = False  # set true when a version is withdrawn but kept for audit
    yank_reason: str = ""  # human-readable reason for yanking (empty when not yanked)
    export_formats: tuple[str, ...] = ()  # e.g. ("system-prompt", "gpt-json", "mcp-server")

    def __post_init__(self) -> None:
        if not self.version or not self.version.strip():
            raise ValueError("IndexedVersion version cannot be empty")
        if not self.path or not self.path.strip():
            raise ValueError("IndexedVersion path cannot be empty")
        if not self.sha256 or len(self.sha256) != 64:
            raise ValueError("IndexedVersion sha256 must be a 64-char hex digest")
        if self.size_bytes < 0:
            raise ValueError("IndexedVersion size_bytes cannot be negative")


@dataclass(frozen=True)
class IndexedSkill:
    """A skill listed in a registry index, with all its published versions.

    The optional metadata (description, tags, owner, deprecated) reflects
    the *current* state of the skill from the latest publish. Pinned older
    versions are still installable via ``versions``, but the skill-level
    metadata always describes the head.
    """

    category: str
    name: str
    latest: str
    versions: tuple[IndexedVersion, ...]
    description: str = ""
    tags: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()  # install targets, e.g. ("claude", "gemini", "vscode")
    owner: Owner | None = None
    deprecated: bool = False
    replaced_by: str = ""  # name of the skill that supersedes this one (when deprecated)
    deprecation_message: str = ""  # human-readable note for deprecated skills

    def __post_init__(self) -> None:
        if not self.category or not self.category.strip():
            raise ValueError("IndexedSkill category cannot be empty")
        if not self.name or not self.name.strip():
            raise ValueError("IndexedSkill name cannot be empty")
        if not self.versions:
            raise ValueError("IndexedSkill must have at least one version")
        known = {v.version for v in self.versions}
        if self.latest not in known:
            raise ValueError(
                f"IndexedSkill latest '{self.latest}' must be one of {sorted(known)}"
            )

    def find(self, version: str) -> IndexedVersion | None:
        for v in self.versions:
            if v.version == version:
                return v
        return None


@dataclass(frozen=True)
class RegistryIndex:
    """The catalog file at the root of a skill registry repo (``index.json``).

    A registry is just a git repo (typically hosted on GitHub) that
    teammates fetch via the raw CDN. The index lets ``install`` resolve
    a ``category/name@version`` to a downloadable URL with a sha256 to
    verify integrity.
    """

    FORMAT_VERSION: ClassVar[str] = "3"

    registry_name: str
    base_url: str
    updated_at: str
    skills: tuple[IndexedSkill, ...]

    def __post_init__(self) -> None:
        if not self.registry_name or not self.registry_name.strip():
            raise ValueError("RegistryIndex registry_name cannot be empty")
        if not self.base_url or not self.base_url.strip():
            raise ValueError("RegistryIndex base_url cannot be empty")

    def find(self, category: str, name: str) -> IndexedSkill | None:
        for s in self.skills:
            if s.category == category and s.name == name:
                return s
        return None

    def yank_version(
        self,
        name: str,
        version: str,
        reason: str = "",
    ) -> RegistryIndex:
        """Return a new index with ``version`` of ``name`` marked yanked.

        Raises ``ValueError`` when the skill or version is not found.
        Also recalculates ``latest`` to skip the newly-yanked version.
        """
        new_skills: list[IndexedSkill] = []
        found = False
        for s in self.skills:
            if s.name == name:
                found = True
                new_versions = tuple(
                    IndexedVersion(
                        version=v.version,
                        path=v.path,
                        sha256=v.sha256,
                        published_at=v.published_at,
                        size_bytes=v.size_bytes,
                        release_notes=v.release_notes,
                        yanked=True if v.version == version else v.yanked,
                        yank_reason=reason if v.version == version else v.yank_reason,
                        export_formats=v.export_formats,
                    )
                    for v in s.versions
                )
                if not any(v.version == version for v in s.versions):
                    raise ValueError(
                        f"Version '{version}' not found for skill '{name}'"
                    )
                non_yanked = [v for v in new_versions if not v.yanked]
                latest = (non_yanked[-1] if non_yanked else new_versions[-1]).version
                new_skills.append(
                    IndexedSkill(
                        category=s.category,
                        name=s.name,
                        latest=latest,
                        versions=new_versions,
                        description=s.description,
                        tags=s.tags,
                        platforms=s.platforms,
                        owner=s.owner,
                        deprecated=s.deprecated,
                        replaced_by=s.replaced_by,
                        deprecation_message=s.deprecation_message,
                    )
                )
            else:
                new_skills.append(s)
        if not found:
            raise ValueError(f"Skill '{name}' not found in registry index")
        return RegistryIndex(
            registry_name=self.registry_name,
            base_url=self.base_url,
            updated_at=self.updated_at,
            skills=tuple(new_skills),
        )

    def set_skill_metadata(
        self,
        name: str,
        *,
        deprecated: bool | None = None,
        replaced_by: str | None = None,
        deprecation_message: str | None = None,
    ) -> RegistryIndex:
        """Return a new index with skill-level metadata updated.

        Only fields passed as non-``None`` are changed; the rest keep their
        current values. Raises ``ValueError`` when ``name`` is not found.
        """
        new_skills: list[IndexedSkill] = []
        found = False
        for s in self.skills:
            if s.name == name:
                found = True
                new_skills.append(
                    IndexedSkill(
                        category=s.category,
                        name=s.name,
                        latest=s.latest,
                        versions=s.versions,
                        description=s.description,
                        tags=s.tags,
                        platforms=s.platforms,
                        owner=s.owner,
                        deprecated=deprecated if deprecated is not None else s.deprecated,
                        replaced_by=(
                            replaced_by if replaced_by is not None else s.replaced_by
                        ),
                        deprecation_message=(
                            deprecation_message
                            if deprecation_message is not None
                            else s.deprecation_message
                        ),
                    )
                )
            else:
                new_skills.append(s)
        if not found:
            raise ValueError(f"Skill '{name}' not found in registry index")
        return RegistryIndex(
            registry_name=self.registry_name,
            base_url=self.base_url,
            updated_at=self.updated_at,
            skills=tuple(new_skills),
        )

    def upsert(
        self,
        category: str,
        name: str,
        version: IndexedVersion,
        *,
        description: str | None = None,
        tags: tuple[str, ...] | None = None,
        platforms: tuple[str, ...] | None = None,
        owner: Owner | None = None,
        deprecated: bool | None = None,
    ) -> RegistryIndex:
        """Return a new index with ``version`` added to the matching skill.

        If the skill is new, it's added. If the version already exists, the
        new entry replaces it (lets you re-publish after fixing a typo).

        Skill-level metadata (description, tags, owner, deprecated) is
        overwritten when supplied; passing ``None`` keeps the existing value
        for skills that already exist, or falls back to defaults for newly
        added skills.
        """
        new_skills: list[IndexedSkill] = []
        found = False
        for s in self.skills:
            if s.category == category and s.name == name:
                found = True
                kept = tuple(v for v in s.versions if v.version != version.version)
                merged = (*kept, version)
                ordered = tuple(sorted(merged, key=lambda v: _version_key(v.version)))
                # latest skips yanked versions if there's any non-yanked option
                non_yanked = [v for v in ordered if not v.yanked]
                latest = (non_yanked[-1] if non_yanked else ordered[-1]).version
                new_skills.append(
                    IndexedSkill(
                        category=category,
                        name=name,
                        latest=latest,
                        versions=ordered,
                        description=(
                            description if description is not None else s.description
                        ),
                        tags=tags if tags is not None else s.tags,
                        platforms=platforms if platforms is not None else s.platforms,
                        owner=owner if owner is not None else s.owner,
                        deprecated=(
                            deprecated if deprecated is not None else s.deprecated
                        ),
                        replaced_by=s.replaced_by,
                        deprecation_message=s.deprecation_message,
                    )
                )
            else:
                new_skills.append(s)
        if not found:
            new_skills.append(
                IndexedSkill(
                    category=category,
                    name=name,
                    latest=version.version,
                    versions=(version,),
                    description=description or "",
                    tags=tags or (),
                    platforms=platforms or (),
                    owner=owner,
                    deprecated=bool(deprecated) if deprecated is not None else False,
                )
            )
        new_skills.sort(key=lambda s: (s.category, s.name))
        return RegistryIndex(
            registry_name=self.registry_name,
            base_url=self.base_url,
            updated_at=self.updated_at,
            skills=tuple(new_skills),
        )


def _version_key(version: str) -> tuple[int, ...]:
    """Best-effort semver sort key. Falls back to lexical for weird strings."""
    parts: list[int] = []
    for chunk in version.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


@dataclass(frozen=True)
class PublishMetadata:
    """Optional publish-time metadata that enriches the registry index.

    Caller assembles this in the application layer (typically reading
    ``description`` from the skill's frontmatter and accepting the rest
    via CLI flags) and passes it to the publisher. All fields default to
    "no opinion" so older callers keep working unchanged.
    """

    description: str = ""
    tags: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    export_formats: tuple[str, ...] = ()
    owner: Owner | None = None
    deprecated: bool = False
    release_notes: str = ""
    yanked: bool = False


@dataclass(frozen=True)
class PublishResult:
    """Outcome of publishing a pack to a registry."""

    pack_name: str
    version: str
    raw_url: str
    repo_relative_path: str
    sha256: str
    committed: bool
    pushed: bool


@dataclass(frozen=True)
class LintIssue:
    """A single issue found during skill validation."""

    rule: str
    message: str
    severity: Severity
    location: str | None = None

    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        loc = f" ({self.location})" if self.location else ""
        return f"{prefix} {self.rule}{loc}: {self.message}"


@dataclass
class LintReport:
    """The result of validating a skill."""

    skill_name: str
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def is_clean(self) -> bool:
        """True when there are no ERROR or WARNING issues (INFO issues are advisory)."""
        return all(i.severity == Severity.INFO for i in self.issues)

    def add(self, issue: LintIssue) -> None:
        self.issues.append(issue)
