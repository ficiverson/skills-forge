"""Factory: wires together domain, application, and infrastructure layers.

This is the composition root — the only place that knows about
concrete implementations. Everything else depends on abstractions.
"""

from __future__ import annotations

from pathlib import Path

from skill_forge.application.use_cases.lint_skill import LintSkill
from skill_forge.application.use_cases.pack_skill import PackSkill, UnpackSkill
from skill_forge.application.use_cases.publish_skill import (
    InstallFromUrl,
    PublishPack,
)
from skill_forge.infrastructure.adapters.filesystem_repository import (
    FilesystemSkillRepository,
)
from skill_forge.infrastructure.adapters.git_registry_publisher import (
    GitRegistryPublisher,
)
from skill_forge.infrastructure.adapters.http_pack_fetcher import HttpPackFetcher
from skill_forge.infrastructure.adapters.markdown_parser import MarkdownSkillParser
from skill_forge.infrastructure.adapters.markdown_renderer import MarkdownSkillRenderer
from skill_forge.infrastructure.adapters.symlink_installer import SymlinkSkillInstaller
from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker


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


def build_packer() -> ZipSkillPacker:
    return ZipSkillPacker()


def build_pack_use_case() -> PackSkill:
    return PackSkill(packer=build_packer(), parser=build_parser())


def build_unpack_use_case() -> UnpackSkill:
    return UnpackSkill(packer=build_packer())


def build_git_publisher(
    registry_root: Path,
    registry_name: str,
    base_url: str,
) -> GitRegistryPublisher:
    return GitRegistryPublisher(
        registry_root=registry_root,
        registry_name=registry_name,
        base_url=base_url,
    )


def build_fetcher() -> HttpPackFetcher:
    return HttpPackFetcher()


def build_publish_use_case(
    registry_root: Path,
    registry_name: str,
    base_url: str,
) -> PublishPack:
    publisher = build_git_publisher(
        registry_root=registry_root,
        registry_name=registry_name,
        base_url=base_url,
    )
    return PublishPack(publisher=publisher, packer=build_packer())


def build_install_from_url_use_case() -> InstallFromUrl:
    return InstallFromUrl(
        fetcher=build_fetcher(),
        unpacker=build_unpack_use_case(),
        installer=build_installer(),
    )
