"""Factory: wires together domain, application, and infrastructure layers.

This is the composition root — the only place that knows about
concrete implementations. Everything else depends on abstractions.
"""

from __future__ import annotations

from pathlib import Path

from skill_forge.application.use_cases.lint_skill import LintSkill
from skill_forge.infrastructure.adapters.filesystem_repository import (
    FilesystemSkillRepository,
)
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer
from skill_forge.infrastructure.adapters.symlink_installer import SymlinkSkillInstaller


def build_parser() -> MarkdownSkillParser:
    return MarkdownSkillParser()


def build_renderer() -> MarkdownSkillRenderer:
    return MarkdownSkillRenderer()


def build_repository(base_path: Path) -> FilesystemSkillRepository:
    return FilesystemSkillRepository(
        base_path=base_path,
        renderer=build_renderer(),
        parser=build_parser(),
    )


def build_installer() -> SymlinkSkillInstaller:
    return SymlinkSkillInstaller()


def build_lint_use_case() -> LintSkill:
    return LintSkill(parser=build_parser())
