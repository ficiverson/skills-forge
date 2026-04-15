"""Factory: wires together domain, application, and infrastructure layers.

This is the composition root — the only place that knows about
concrete implementations. Everything else depends on abstractions.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skill_forge.application.use_cases.deprecate_skill import DeprecateSkill
    from skill_forge.application.use_cases.diff_skill import DiffSkill
    from skill_forge.application.use_cases.doctor_skill import DoctorSkill
    from skill_forge.application.use_cases.info_skill import GetSkillInfo
    from skill_forge.application.use_cases.test_skill import AssessSkill
    from skill_forge.application.use_cases.update_skill import UpdateSkill
    from skill_forge.application.use_cases.yank_skill import YankSkill
    from skill_forge.domain.config_model import ForgeConfig
    from skill_forge.infrastructure.adapters.toml_config_repository import (
        TomlConfigRepository,
    )

from skill_forge.application.use_cases.export_skill import ExportSkill
from skill_forge.application.use_cases.install_skill import InstallSkill
from skill_forge.application.use_cases.lint_skill import LintSkill
from skill_forge.application.use_cases.pack_skill import PackSkill, UnpackSkill
from skill_forge.application.use_cases.publish_skill import (
    InstallFromUrl,
    PublishPack,
)
from skill_forge.domain.model import ExportFormat
from skill_forge.domain.ports import SkillExporter
from skill_forge.infrastructure.adapters.exporters.bedrock_xml_exporter import (
    BedrockXmlExporter,
)
from skill_forge.infrastructure.adapters.exporters.gem_txt_exporter import (
    GemTxtExporter,
)
from skill_forge.infrastructure.adapters.exporters.gemini_api_exporter import (
    GeminiApiExporter,
)
from skill_forge.infrastructure.adapters.exporters.gpt_json_exporter import (
    GptJsonExporter,
)
from skill_forge.infrastructure.adapters.exporters.mcp_server_exporter import (
    McpServerExporter,
)
from skill_forge.infrastructure.adapters.exporters.mistral_json_exporter import (
    MistralJsonExporter,
)
from skill_forge.infrastructure.adapters.exporters.openai_assistants_exporter import (
    OpenAIAssistantsExporter,
)
from skill_forge.infrastructure.adapters.exporters.system_prompt_exporter import (
    SystemPromptExporter,
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
from skill_forge.infrastructure.adapters.subprocess_claude_runner import (
    SubprocessClaudeRunner,
)
from skill_forge.infrastructure.adapters.symlink_installer import SymlinkSkillInstaller
from skill_forge.infrastructure.adapters.zip_skill_packer import ZipSkillPacker

# Registry: maps each ExportFormat to its concrete exporter class.
_EXPORTERS: dict[ExportFormat, type[SkillExporter]] = {
    ExportFormat.SYSTEM_PROMPT: SystemPromptExporter,
    ExportFormat.GPT_JSON: GptJsonExporter,
    ExportFormat.GEM_TXT: GemTxtExporter,
    ExportFormat.BEDROCK_XML: BedrockXmlExporter,
    ExportFormat.MCP_SERVER: McpServerExporter,
    ExportFormat.MISTRAL_JSON: MistralJsonExporter,
    ExportFormat.GEMINI_API: GeminiApiExporter,
    ExportFormat.OPENAI_ASSISTANTS: OpenAIAssistantsExporter,
}


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


def build_install_use_case() -> InstallSkill:
    return InstallSkill(installer=build_installer(), parser=build_parser())


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


def build_config_repo() -> TomlConfigRepository:
    from skill_forge.infrastructure.adapters.toml_config_repository import (
        TomlConfigRepository as _TomlConfigRepository,
    )

    return _TomlConfigRepository()


def load_config() -> ForgeConfig:
    from skill_forge.domain.config_model import ForgeConfig as _ForgeConfig

    try:
        return build_config_repo().load()
    except Exception:  # pragma: no cover — config errors surface in registry cmds
        return _ForgeConfig.with_public_registry()


def build_fetcher(url: str = "") -> HttpPackFetcher:
    """Build a fetcher, resolving per-registry auth token from config when possible."""
    token = ""
    if url:
        try:
            cfg = load_config()
            # Find a registry whose URL is a prefix of the target URL
            for reg in cfg.registries:
                if url.startswith(reg.url):
                    token = reg.resolved_token
                    break
        except Exception:  # pragma: no cover
            pass
    return HttpPackFetcher(token=token)


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
    return PublishPack(
        publisher=publisher,
        packer=build_packer(),
        parser=build_parser(),
    )


def build_install_from_url_use_case(url: str = "") -> InstallFromUrl:
    return InstallFromUrl(
        fetcher=build_fetcher(url=url),
        unpacker=build_unpack_use_case(),
        installer=build_installer(),
    )


def build_exporter(fmt: ExportFormat) -> SkillExporter:
    """Return the concrete exporter for ``fmt``."""
    exporter_cls = _EXPORTERS.get(fmt)
    if exporter_cls is None:
        raise ValueError(f"No exporter registered for format '{fmt.value}'")
    return exporter_cls()


def build_test_use_case() -> AssessSkill:
    from skill_forge.application.use_cases.test_skill import AssessSkill as _AssessSkill

    return _AssessSkill(
        parser=build_parser(),
        runner=SubprocessClaudeRunner(),
    )


def build_export_use_case(fmt: ExportFormat) -> ExportSkill:
    """Wire and return the ExportSkill use case for the given format."""
    return ExportSkill(
        parser=build_parser(),
        exporter=build_exporter(fmt),
        packer=build_packer(),
    )


def build_info_use_case(registry_url: str = "") -> GetSkillInfo:
    from skill_forge.application.use_cases.info_skill import GetSkillInfo as _GetSkillInfo

    return _GetSkillInfo(
        installer=build_installer(),
        parser=build_parser(),
        fetcher=build_fetcher(url=registry_url) if registry_url else None,
    )


def build_doctor_use_case(registry_url: str = "") -> DoctorSkill:
    from skill_forge.application.use_cases.doctor_skill import DoctorSkill as _DoctorSkill

    return _DoctorSkill(
        installer=build_installer(),
        parser=build_parser(),
        fetcher=build_fetcher(url=registry_url) if registry_url else None,
    )


def build_yank_use_case(
    registry_root: Path,
    registry_name: str,
    base_url: str,
) -> YankSkill:
    from skill_forge.application.use_cases.yank_skill import YankSkill as _YankSkill

    return _YankSkill(
        publisher=build_git_publisher(
            registry_root=registry_root,
            registry_name=registry_name,
            base_url=base_url,
        )
    )


def build_deprecate_use_case(
    registry_root: Path,
    registry_name: str,
    base_url: str,
) -> DeprecateSkill:
    from skill_forge.application.use_cases.deprecate_skill import (
        DeprecateSkill as _DeprecateSkill,
    )

    return _DeprecateSkill(
        publisher=build_git_publisher(
            registry_root=registry_root,
            registry_name=registry_name,
            base_url=base_url,
        )
    )


def build_diff_use_case(registry_url: str = "") -> DiffSkill:
    from skill_forge.application.use_cases.diff_skill import DiffSkill as _DiffSkill

    return _DiffSkill(
        installer=build_installer(),
        parser=build_parser(),
        fetcher=build_fetcher(url=registry_url),
    )


def build_update_use_case(registry_url: str = "") -> UpdateSkill:
    from skill_forge.application.use_cases.update_skill import UpdateSkill as _UpdateSkill

    fetcher = build_fetcher(url=registry_url)
    return _UpdateSkill(
        installer=build_installer(),
        parser=build_parser(),
        fetcher=fetcher,
        install_from_url=InstallFromUrl(
            fetcher=fetcher,
            unpacker=build_unpack_use_case(),
            installer=build_installer(),
        ),
    )
