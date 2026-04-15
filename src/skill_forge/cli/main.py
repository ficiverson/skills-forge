"""CLI entry point for skills-forge."""

from __future__ import annotations

from pathlib import Path

import typer

from skill_forge.cli.factory import (
    build_config_repo,
    build_deprecate_use_case,
    build_diff_use_case,
    build_doctor_use_case,
    build_export_use_case,
    build_info_use_case,
    build_install_from_url_use_case,
    build_install_use_case,
    build_installer,
    build_lint_use_case,
    build_pack_use_case,
    build_parser,
    build_publish_use_case,
    build_renderer,
    build_repository,
    build_test_use_case,
    build_unpack_use_case,
    build_update_use_case,
    build_yank_use_case,
    load_config,
)

app = typer.Typer(
    name="skills-forge",
    help="A clean-architecture toolkit for crafting Claude Code skills.",
    no_args_is_help=True,
)


@app.command()
def create(
    name: str = typer.Option(..., "--name", "-n", help="Skill name"),
    category: str = typer.Option(..., "--category", "-c", help="Skill category"),
    description: str = typer.Option(..., "--description", "-d", help="Trigger description"),
    emoji: str | None = typer.Option(None, "--emoji", "-e", help="Starter character emoji"),
    skill_version: str = typer.Option(
        "0.1.0",
        "--version",
        "-v",
        help="Initial skill version (semver, written into frontmatter)",
    ),
    output: Path = typer.Option(
        Path("output_skills"),
        "--output",
        "-o",
        help="Base directory for generated skills",
    ),
) -> None:
    """Create a new skill scaffold."""
    from skill_forge.application.use_cases.create_skill import (
        CreateSkill,
        CreateSkillRequest,
    )

    repo = build_repository(output)
    renderer = build_renderer()
    use_case = CreateSkill(repository=repo, renderer=renderer)

    request = CreateSkillRequest(
        name=name,
        category=category,
        description=description,
        starter_emoji=emoji,
        version=skill_version,
    )
    response = use_case.execute(request)

    if response.already_existed:
        typer.echo(f"⚠ Skill '{name}' already exists.")
        raise typer.Exit(code=1)

    typer.echo(f"✔ Created skill at {response.path}")


@app.command()
def lint(
    path: Path = typer.Argument(
        ...,
        help="Path to a SKILL.md file or a directory containing skills",
        exists=True,
    ),
) -> None:
    """Lint a skill or directory of skills for quality issues."""
    lint_use_case = build_lint_use_case()

    paths = _collect_skill_paths(path)
    if not paths:
        typer.echo("No SKILL.md files found.")
        raise typer.Exit(code=1)

    exit_code = 0
    for skill_path in paths:
        from skill_forge.application.use_cases.lint_skill import LintSkillRequest

        request = LintSkillRequest(path=skill_path)
        response = lint_use_case.execute(request)
        report = response.report

        if report.is_clean:
            typer.echo(f"✔ {report.skill_name}: clean")
        else:
            typer.echo(f"\n⚠ {report.skill_name}:")
            for issue in report.issues:
                typer.echo(f"  {issue}")
            if report.has_errors:
                exit_code = 1

    if exit_code:
        raise typer.Exit(code=exit_code)


def _do_list_skills(
    directory: Path,
    filter_str: str = "",
    tag: str = "",
    category: str = "",
) -> None:
    """Shared implementation for list-skills and list commands."""
    repo = build_repository(directory)
    skills = repo.list_all()

    if not skills:
        typer.echo("No skills found.")
        return

    # Apply filters
    if category:
        skills = [s for s in skills if s.identity.category.lower() == category.lower()]
    if tag:
        # Tags live on the registry index, not on the skill object directly.
        # Here we do a lightweight filter on skill name/description containing the tag.
        tag_lower = tag.lower()
        skills = [
            s
            for s in skills
            if tag_lower in s.identity.name.lower() or tag_lower in s.description.text.lower()
        ]
    if filter_str:
        f_lower = filter_str.lower()
        skills = [
            s
            for s in skills
            if f_lower in s.identity.name.lower()
            or f_lower in s.identity.category.lower()
            or f_lower in s.description.text.lower()
        ]

    if not skills:
        typer.echo("No skills match the given filters.")
        return

    for skill in skills:
        tokens = skill.total_estimated_tokens
        marker = "✔" if tokens <= 1200 else "⚠"
        eval_tag = f"[evals: {len(skill.evals)}]" if skill.has_evals else "[no evals]"
        version_tag = f"v{skill.version}"
        deps_tag = (
            f"[deps: {', '.join(d.skill_name for d in skill.depends_on)}]"
            if skill.has_dependencies
            else ""
        )
        parts = [
            f"  {marker} {skill.identity}",
            version_tag,
            f"(~{tokens} tokens)",
            eval_tag,
        ]
        if deps_tag:
            parts.append(deps_tag)
        typer.echo("  ".join(parts))


@app.command()
def list_skills(
    directory: Path = typer.Argument(
        Path("output_skills"),
        help="Base directory containing skills",
    ),
    filter_str: str = typer.Option(
        "",
        "--filter",
        "-f",
        help="Filter skills by name, category, or description (case-insensitive substring)",
    ),
    tag: str = typer.Option(
        "",
        "--tag",
        "-t",
        help="Filter skills whose name or description contains this tag",
    ),
    category: str = typer.Option(
        "",
        "--category",
        "-c",
        help="Show only skills in this category",
    ),
) -> None:
    """List all skills in a directory."""
    _do_list_skills(directory, filter_str=filter_str, tag=tag, category=category)


@app.command(name="list")
def list_skills_alias(
    directory: Path = typer.Argument(
        Path("output_skills"),
        help="Base directory containing skills",
    ),
    filter_str: str = typer.Option(
        "",
        "--filter",
        "-f",
        help="Filter skills by name, category, or description (case-insensitive substring)",
    ),
    tag: str = typer.Option(
        "",
        "--tag",
        "-t",
        help="Filter skills whose name or description contains this tag",
    ),
    category: str = typer.Option(
        "",
        "--category",
        "-c",
        help="Show only skills in this category (e.g. productivity, evaluation)",
    ),
) -> None:
    """Alias for list-skills. List all skills in a directory."""
    _do_list_skills(directory, filter_str=filter_str, tag=tag, category=category)


@app.command()
def install(
    source: str = typer.Argument(
        ...,
        help=(
            "Local skill directory path, or an https:// URL pointing to a "
            ".skillpack (e.g. raw.githubusercontent.com)"
        ),
    ),
    scope: str = typer.Option(
        "global",
        "--scope",
        "-s",
        help="Installation scope: global (user home) or project (current directory)",
    ),
    target: str = typer.Option(
        "claude",
        "--target",
        "-t",
        help=(
            "Agent tool to install into: claude, gemini, codex, vscode, agents, all. "
            "'agents' writes to .agents/skills/ — the universal cross-vendor path "
            "supported by every agentskills.io-conforming tool at project scope. "
            "'all' writes to every applicable directory for the chosen scope."
        ),
    ),
    output: Path = typer.Option(
        Path("output_skills"),
        "--output",
        "-o",
        help="Where to unpack remote packs (only used for URL installs)",
    ),
    sha256: str = typer.Option(
        "",
        "--sha256",
        help="Expected sha256 of a remote .skillpack (verified before install)",
    ),
    no_deps: bool = typer.Option(
        False,
        "--no-deps",
        help="Skip dependency resolution check",
    ),
) -> None:
    """Install a skill from a local path or a remote .skillpack URL.

    If the skill declares ``depends_on`` in its frontmatter, skills-forge checks
    whether those skills are already installed and warns about any that are missing.
    Use --no-deps to skip this check.

    Examples:

      # default: install into ~/.claude/skills/ (global, Claude Code)
      skills-forge install output_skills/development/python-tdd

      # universal project path — works with Gemini CLI, Codex, VS Code Copilot, etc.
      skills-forge install output_skills/development/python-tdd --target agents --scope project

      # install into every supported tool at once (global scope)
      skills-forge install output_skills/development/python-tdd --target all

      # install from a remote registry into Gemini CLI
      skills-forge install https://raw.githubusercontent.com/.../pack.skillpack --target gemini
    """
    from skill_forge.domain.model import InstallTarget, SkillScope

    skill_scope = SkillScope.GLOBAL if scope == "global" else SkillScope.PROJECT

    try:
        skill_target = InstallTarget(target.lower())
    except ValueError:
        valid = ", ".join(t.value for t in InstallTarget)
        typer.echo(f"⚠ Unknown target '{target}'. Valid values: {valid}")
        raise typer.Exit(code=1) from None

    if source.startswith(("http://", "https://")):
        from skill_forge.application.use_cases.publish_skill import (
            InstallFromUrlRequest,
        )

        if not sha256:
            typer.echo(
                "⚠  Installing without SHA256 verification — supply the digest "
                "with --sha256 <hex> for secure installs",
                err=True,
            )

        use_case = build_install_from_url_use_case(url=source)
        request = InstallFromUrlRequest(
            url=source,
            dest_dir=output,
            scope=skill_scope,
            target=skill_target,
            expected_sha256=sha256,
        )
        response = use_case.execute(request)
        typer.echo(
            f"✔ Fetched '{response.manifest.name}' v{response.manifest.version} "
            f"({response.sha256[:12]}…)"
        )
        for _ref, extracted, installed in zip(
            response.manifest.skills,
            response.extracted_paths,
            response.installed_paths,
            strict=True,
        ):
            typer.echo(f"  → {extracted}")
            typer.echo(f"    installed at {installed} ({skill_scope.value}, {skill_target.value})")
        return

    skill_path = Path(source)
    if not skill_path.exists():
        typer.echo(f"⚠ Path does not exist: {skill_path}")
        raise typer.Exit(code=1)

    from skill_forge.application.use_cases.install_skill import (
        InstallSkillRequest,
    )

    local_use_case = build_install_use_case()
    local_request = InstallSkillRequest(
        skill_path=skill_path,
        scope=skill_scope,
        target=skill_target,
        skip_deps=no_deps,
    )
    try:
        local_response = local_use_case.execute(local_request)
    except ValueError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc

    for path in local_response.installed_paths:
        typer.echo(f"✔ Installed at {path} ({skill_scope.value}, {skill_target.value})")

    if local_response.missing_dependencies:
        typer.echo("")
        typer.echo("  ⚠ Missing dependencies (install these first):")
        for dep in local_response.missing_dependencies:
            typer.echo(f"    · {dep}  →  skills-forge install <path-to-{dep}>")
        typer.echo("")


@app.command()
def export(
    source: Path = typer.Argument(
        ...,
        help=".skillpack archive to export",
        exists=True,
    ),
    fmt: str = typer.Option(
        "system-prompt",
        "--format",
        "-f",
        help=(
            "Export format: system-prompt, gpt-json, gem-txt, bedrock-xml, mcp-server, "
            "mistral-json, gemini-api, openai-assistants. "
            "system-prompt      — plain Markdown for any chat UI system field. "
            "gpt-json           — OpenAI Custom GPT / Assistants API config JSON. "
            "gem-txt            — Google Gemini Gem instructions plain-text file. "
            "bedrock-xml        — AWS Bedrock agent prompt XML template. "
            "mcp-server         — Self-contained Python MCP Prompts server. "
            "mistral-json       — Mistral Agents API configuration JSON. "
            "gemini-api         — Vertex AI / Gemini API system_instruction JSON. "
            "openai-assistants  — OpenAI Assistants API CreateAssistant JSON."
        ),
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help=("Directory to write the exported artifact into. Defaults to the skill directory."),
    ),
    only_skill: bool = typer.Option(
        False,
        "--only-skill",
        help="Export only the SKILL.md content, skipping references/assets.",
    ),
) -> None:
    """Export a skill to a platform-native format for chatbot / API platforms.

    For agent-CLI tools that natively support SKILL.md (Claude Code, Gemini CLI,
    OpenAI Codex, VS Code Copilot) use ``skills-forge install --target`` instead.

    Examples:

      # Plain system prompt — paste into any chat UI
      skills-forge export ./packs/productivity-1.0.0.skillpack

      # OpenAI Custom GPT JSON config
      skills-forge export ./packs/productivity-1.0.0.skillpack --format gpt-json

      # Gemini Gem instructions
      skills-forge export ./packs/productivity-1.0.0.skillpack --format gem-txt

      # AWS Bedrock XML prompt template
      skills-forge export ./packs/productivity-1.0.0.skillpack --format bedrock-xml

      # Self-contained Python MCP server
      skills-forge export ./packs/productivity-1.0.0.skillpack \\
          --format mcp-server -o ./exports/

      # Mistral Agents API JSON
      skills-forge export ./packs/productivity-1.0.0.skillpack --format mistral-json

      # Vertex AI / Gemini API JSON
      skills-forge export ./packs/productivity-1.0.0.skillpack --format gemini-api

      # OpenAI Assistants API JSON
      skills-forge export ./packs/productivity-1.0.0.skillpack --format openai-assistants
    """
    from skill_forge.application.use_cases.export_skill import ExportSkillRequest
    from skill_forge.domain.model import ExportFormat

    try:
        export_fmt = ExportFormat(fmt.lower())
    except ValueError:
        valid = ", ".join(f.value for f in ExportFormat)
        typer.echo(f"⚠ Unknown format '{fmt}'. Valid values: {valid}")
        raise typer.Exit(code=1) from None

    use_case = build_export_use_case(export_fmt)
    request = ExportSkillRequest(
        skill_path=source,
        format=export_fmt,
        output=output,
        bundle=not only_skill,
    )

    try:
        response = use_case.execute(request)
    except FileNotFoundError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc

    for path in response.output_paths:
        typer.echo(f"✔ Exported [{export_fmt.value}] → {path}")

    # Print a contextual next-step hint per format.
    if export_fmt == ExportFormat.SYSTEM_PROMPT:
        typer.echo(
            "  Paste the file contents into the system-prompt / custom-instructions "
            "field of any chat UI."
        )
    elif export_fmt == ExportFormat.GPT_JSON:
        typer.echo(
            "  Open https://chatgpt.com/gpts/editor → Configure tab and paste "
            "the 'instructions' value into the Instructions textarea."
        )
    elif export_fmt == ExportFormat.GEM_TXT:
        typer.echo(
            "  Open https://gemini.google.com/gems → New Gem and paste "
            "the file contents into the Instructions field."
        )
    elif export_fmt == ExportFormat.BEDROCK_XML:
        typer.echo(
            "  AWS Console → Amazon Bedrock → Prompt management → Create prompt "
            "and paste the <system> block into the System prompt field."
        )
    elif export_fmt == ExportFormat.MCP_SERVER:
        for path in response.output_paths:
            typer.echo(f"  Run with: python {path}")
            typer.echo(f'  Or: uvx --from "mcp[cli]" mcp run {path}')
        typer.echo("  Or add to your MCP host config -- see the file header for details.")
    elif export_fmt == ExportFormat.MISTRAL_JSON:
        typer.echo(
            "  POST https://api.mistral.ai/v1/agents with the JSON body "
            "(requires MISTRAL_API_KEY)."
        )
    elif export_fmt == ExportFormat.GEMINI_API:
        typer.echo(
            "  Use the 'system_instruction' field with the Gemini Developer API "
            "or Vertex AI generateContent endpoint."
        )
    elif export_fmt == ExportFormat.OPENAI_ASSISTANTS:
        typer.echo(
            "  POST https://api.openai.com/v1/assistants with 'assistant_config' "
            "as the request body (requires OpenAI-Beta: assistants=v2 header)."
        )


@app.command()
def uninstall(
    skill_name: str = typer.Argument(..., help="Name of the skill to uninstall"),
    scope: str = typer.Option(
        "global",
        "--scope",
        "-s",
        help="Installation scope: global or project",
    ),
    target: str = typer.Option(
        "all",
        "--target",
        "-t",
        help=(
            "Which tool target(s) to remove from: "
            "claude, gemini, codex, vscode, agents, all (default: all)"
        ),
    ),
) -> None:
    """Uninstall a previously installed skill.

    Removes the symlink(s) created by ``install`` for the given skill name.
    Use --target to limit removal to a specific tool; defaults to all targets.
    Idempotent: safe to run even if the skill is not currently installed.
    """
    from skill_forge.application.use_cases.install_skill import (
        UninstallSkill,
        UninstallSkillRequest,
    )
    from skill_forge.domain.model import InstallTarget, SkillScope

    skill_scope = SkillScope.GLOBAL if scope == "global" else SkillScope.PROJECT

    try:
        install_target = InstallTarget(target)
    except ValueError:
        valid = ", ".join(t.value for t in InstallTarget)
        typer.echo(f"⚠ Unknown target '{target}'. Valid values: {valid}")
        raise typer.Exit(code=1) from None

    installer = build_installer()
    use_case = UninstallSkill(installer=installer)

    request = UninstallSkillRequest(
        skill_name=skill_name,
        scope=skill_scope,
        target=install_target,
    )
    response = use_case.execute(request)

    if response.was_installed:
        for path in response.removed_paths:
            typer.echo(f"✔ Removed {path}")
    else:
        typer.echo(
            f"⚠ '{skill_name}' was not found in any {skill_scope.value} "
            f"target directory — nothing to remove."
        )


@app.command()
def pack(
    skill_paths: list[Path] = typer.Argument(
        ...,
        help="One or more skill directories to bundle into a .skillpack",
        exists=True,
    ),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        help="Output file or directory. If a directory, the filename is "
        "auto-derived as <pack-name>-<version>.skillpack",
    ),
    version: str = typer.Option(
        "",
        "--version",
        "-v",
        help="Pack version (defaults to the skill's own version from frontmatter)",
    ),
    author: str = typer.Option("", "--author", "-a", help="Pack author"),
    name: str = typer.Option(
        "",
        "--name",
        "-n",
        help="Pack name (defaults to the first skill's name)",
    ),
    description: str = typer.Option(
        "", "--description", "-d", help="Short description of the pack"
    ),
    tags: list[str] = typer.Option(
        [],
        "--tag",
        "-t",
        help="Tag for the pack (repeatable). Travels in the manifest and "
        "becomes the default when publishing to a registry.",
    ),
    platforms: list[str] = typer.Option(
        [],
        "--platform",
        "-p",
        help=(
            "Install target (repeatable): claude, gemini, codex, agents, vscode. "
            "Baked into the manifest and used as the default when publishing."
        ),
    ),
    export_formats: list[str] = typer.Option(
        [],
        "--export-format",
        "-f",
        help=(
            "Supported export format (repeatable): system-prompt, gpt-json, "
            "gem-txt, bedrock-xml, mcp-server, mistral-json, gemini-api, openai-assistants. "
            "Baked into the manifest and used as the default when publishing."
        ),
    ),
    owner_name: str = typer.Option(
        "",
        "--owner-name",
        help="Maintainer name baked into the manifest",
    ),
    owner_email: str = typer.Option(
        "",
        "--owner-email",
        help="Maintainer email baked into the manifest",
    ),
    deprecated: bool = typer.Option(
        False,
        "--deprecated",
        help="Flag the pack as deprecated in its manifest",
    ),
) -> None:
    """Bundle one or more skills into a portable .skillpack archive."""
    from skill_forge.application.use_cases.pack_skill import PackSkillRequest

    use_case = build_pack_use_case()

    for skill_path in skill_paths:
        if not (skill_path / "SKILL.md").exists():
            typer.echo(f"⚠ Not a skill directory (no SKILL.md): {skill_path}")
            raise typer.Exit(code=1)

    request = PackSkillRequest(
        skill_dirs=list(skill_paths),
        output_path=output,
        version=version,
        author=author,
        pack_name=name,
        description=description,
        tags=tuple(tags),
        platforms=tuple(platforms),
        export_formats=tuple(export_formats),
        owner_name=owner_name,
        owner_email=owner_email,
        deprecated=deprecated,
    )
    response = use_case.execute(request)

    typer.echo(f"✔ Packed {response.manifest.skill_count} skill(s) into {response.pack_path}")
    typer.echo(f"  name:    {response.manifest.name}")
    typer.echo(f"  version: {response.manifest.version}")
    if response.manifest.author:
        typer.echo(f"  author:  {response.manifest.author}")
    for ref in response.manifest.skills:
        typer.echo(f"  - {ref.category}/{ref.name} @ {ref.version}")


@app.command()
def unpack(
    pack_path: Path = typer.Argument(..., help="Path to a .skillpack file", exists=True),
    output: Path = typer.Option(
        Path("output_skills"),
        "--output",
        "-o",
        help="Destination directory (defaults to output_skills/)",
    ),
) -> None:
    """Extract a .skillpack into a destination directory."""
    from skill_forge.application.use_cases.pack_skill import UnpackSkillRequest

    use_case = build_unpack_use_case()
    request = UnpackSkillRequest(pack_path=pack_path, dest_dir=output)
    response = use_case.execute(request)

    typer.echo(
        f"✔ Unpacked {response.manifest.skill_count} skill(s) "
        f"from '{response.manifest.name}' v{response.manifest.version}"
    )
    for ref, path in zip(response.manifest.skills, response.extracted_paths, strict=True):
        typer.echo(f"  → {path}  (v{ref.version})")
    typer.echo(
        "\nNext: lint the unpacked skills with `skills-forge lint`, then install "
        "with `skills-forge install`."
    )


@app.command()
def publish(
    pack_path: Path = typer.Argument(
        ...,
        help="Path to a .skillpack file produced by `skills-forge pack`",
        exists=True,
    ),
    registry: Path = typer.Option(
        ...,
        "--registry",
        "-r",
        help="Local clone of the registry git repo",
    ),
    base_url: str = typer.Option(
        ...,
        "--base-url",
        "-u",
        help=(
            "Public base URL for the registry, e.g. "
            "https://raw.githubusercontent.com/<owner>/<repo>/main"
        ),
    ),
    registry_name: str = typer.Option(
        "",
        "--registry-name",
        "-N",
        help="Display name for the registry (defaults to the repo dir name)",
    ),
    message: str = typer.Option("", "--message", "-m", help="Git commit message"),
    push: bool = typer.Option(
        False,
        "--push/--no-push",
        help="Push the commit to the remote after writing the index",
    ),
    tags: list[str] = typer.Option(
        [],
        "--tag",
        "-t",
        help="Tag for the skill (repeatable). Surfaces in the registry index for discovery.",
    ),
    platforms: list[str] = typer.Option(
        [],
        "--platform",
        "-p",
        help=(
            "Install target (repeatable): claude, gemini, codex, agents, vscode. "
            "Defaults to the value baked into the manifest at pack time."
        ),
    ),
    export_formats: list[str] = typer.Option(
        [],
        "--export-format",
        help=(
            "Supported export format (repeatable): system-prompt, gpt-json, "
            "gem-txt, bedrock-xml, mcp-server, mistral-json, gemini-api, openai-assistants. "
            "Defaults to the value baked into the manifest at pack time."
        ),
    ),
    owner_name: str = typer.Option(
        "",
        "--owner-name",
        help="Name of the skill maintainer (recorded in index.json)",
    ),
    owner_email: str = typer.Option(
        "",
        "--owner-email",
        help="Email of the skill maintainer (recorded in index.json)",
    ),
    deprecated: bool = typer.Option(
        False,
        "--deprecated",
        help="Mark the skill as deprecated in the index",
    ),
    release_notes: str = typer.Option(
        "",
        "--release-notes",
        help="Release notes for this version (recorded with the version entry)",
    ),
    yanked: bool = typer.Option(
        False,
        "--yanked",
        help="Mark this version as yanked (kept for audit but excluded from 'latest')",
    ),
) -> None:
    """Publish a .skillpack to a git-backed registry repo.

    The pack is copied into ``packs/<category>/<name>-<version>.skillpack``,
    ``index.json`` is updated, and the change is committed. Pass --push to
    also push the commit. Once pushed to GitHub, the pack is downloadable
    via the raw CDN — share the printed URL with your team.
    """
    from skill_forge.application.use_cases.publish_skill import PublishPackRequest

    use_case = build_publish_use_case(
        registry_root=registry,
        registry_name=registry_name or registry.name,
        base_url=base_url,
    )
    request = PublishPackRequest(
        pack_path=pack_path,
        message=message,
        push=push,
        tags=tuple(tags),
        platforms=tuple(platforms),
        export_formats=tuple(export_formats),
        owner_name=owner_name,
        owner_email=owner_email,
        deprecated=deprecated,
        release_notes=release_notes,
        yanked=yanked,
    )
    response = use_case.execute(request)
    result = response.result

    typer.echo(f"✔ Published {result.pack_name} v{result.version}")
    typer.echo(f"  path:    {result.repo_relative_path}")
    typer.echo(f"  sha256:  {result.sha256[:12]}…")
    if result.committed:
        typer.echo("  git:     committed")
    if result.pushed:
        typer.echo("  git:     pushed")
    elif result.committed:
        typer.echo("  git:     run `git push` (or rerun with --push)")
    typer.echo("")
    typer.echo("  Install URL:")
    typer.echo(f"  {result.raw_url}")
    typer.echo("")
    typer.echo("  Teammates can install with:")
    typer.echo(f"    skills-forge install {result.raw_url} --sha256 {result.sha256}")


@app.command()
def init(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to initialize as a skills-forge workspace",
    ),
) -> None:
    """Initialize a skills-forge workspace with the recommended structure.

    Detects which agent-CLI tools (Claude Code, Gemini CLI, Codex, VS Code
    Copilot) are installed on this machine and notes them in the workspace
    CLAUDE.md so install commands default to the right targets.
    """
    import shutil

    output_dir = directory / "output_skills"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Detect installed agent tools
    tool_detection = {
        "claude": shutil.which("claude") is not None,
        "gemini": shutil.which("gemini") is not None,
        "codex": shutil.which("codex") is not None,
        "vscode": shutil.which("code") is not None,
    }
    detected = [t for t, found in tool_detection.items() if found]

    claude_md = directory / "CLAUDE.md"
    if not claude_md.exists():
        targets_note = (
            f"Detected agent tools: {', '.join(detected)}\n"
            if detected
            else "No agent-CLI tools detected yet. Install one and re-run `skills-forge init`.\n"
        )
        install_hint = (
            f"  skills-forge install <path> --target {detected[0]}\n"
            if detected
            else "  skills-forge install <path>  # defaults to --target claude\n"
        )
        claude_md.write_text(
            "# Skill Forge Workspace\n\n"
            "This workspace uses skills-forge to create and manage Claude Code skills.\n\n"
            f"## Detected tools\n\n{targets_note}\n"
            "## Commands\n\n"
            "- `skills-forge create` — scaffold a new skill\n"
            "- `skills-forge lint` — validate skill quality\n"
            f"- {install_hint}"
            "- `skills-forge list` — list all skills\n"
            "- `skills-forge doctor` — health-check installed skills\n"
            "- `skills-forge info <skill-name>` — show skill details\n"
            "- `skills-forge update` — update installed skills from registry\n",
            encoding="utf-8",
        )

    # Seed the global config with the public registry on first init
    cfg_repo = build_config_repo()
    if not cfg_repo.path.exists():
        from skill_forge.domain.config_model import ForgeConfig

        cfg_repo.save(ForgeConfig.with_public_registry())
        typer.echo(f"  Config created at {cfg_repo.path}")

    typer.echo(f"✔ Initialized skills-forge workspace at {directory.resolve()}")

    if detected:
        typer.echo(f"  Detected agent tools: {', '.join(detected)}")
        if len(detected) > 1:
            typer.echo(
                "  Tip: use `skills-forge install <path> --target all` to install "
                "into every detected tool at once."
            )
    else:
        typer.echo(
            "  No agent-CLI tools found on PATH. "
            "Install Claude Code, Gemini CLI, or Codex, then re-run `skills-forge init`."
        )


# ── info ─────────────────────────────────────────────────────────────────────


@app.command(name="info")
def info(
    skill_name: str = typer.Argument(..., help="Name of the skill to inspect"),
    scope: str = typer.Option(
        "global",
        "--scope",
        "-s",
        help="Installation scope: global or project",
    ),
    registry: str = typer.Option(
        "",
        "--registry",
        "-r",
        help="Registry base URL to compare installed version against",
    ),
) -> None:
    """Show details about an installed skill.

    Reports the installed version, which target directories contain it,
    its dependencies, eval count, and (optionally) whether a newer version
    is available in a registry.

    Examples:

      skills-forge info my-skill
      skills-forge info my-skill --registry https://raw.githubusercontent.com/…/main
    """
    from skill_forge.application.use_cases.info_skill import InfoRequest
    from skill_forge.domain.model import SkillScope

    skill_scope = SkillScope.GLOBAL if scope == "global" else SkillScope.PROJECT

    # Fall back to configured default registry URL when --registry is omitted
    if not registry:
        cfg = load_config()
        default_reg = next((r for r in cfg.registries if r.name == cfg.default_registry), None)
        if default_reg:
            registry = default_reg.url

    use_case = build_info_use_case(registry_url=registry)
    request = InfoRequest(
        skill_name=skill_name,
        scope=skill_scope,
        registry_url=registry,
    )
    response = use_case.execute(request)

    if not response.is_installed:
        typer.echo(f"⚠ '{skill_name}' is not installed at {skill_scope.value} scope.")
        raise typer.Exit(code=1)

    skill = response.skill
    typer.echo(f"\n  Skill: {skill_name}")
    if skill:
        typer.echo(f"  Version:   {skill.version}")
        typer.echo(f"  Category:  {skill.identity.category}")
        typer.echo(f"  Tokens:    ~{skill.total_estimated_tokens}")
        typer.echo(f"  Evals:     {len(skill.evals) if skill.has_evals else 0}")
        if skill.has_dependencies:
            deps = ", ".join(d.skill_name for d in skill.depends_on)
            typer.echo(f"  Depends:   {deps}")
        if skill.requires_forge:
            typer.echo(f"  Requires:  skills-forge {skill.requires_forge}")

    typer.echo("\n  Install locations:")
    for loc in response.install_locations:
        status = "  ✘ broken" if loc.is_broken else ""
        typer.echo(f"    [{loc.target.value}] {loc.path}{status}")

    if response.registry_latest:
        if response.is_up_to_date:
            typer.echo(f"\n  Registry:  v{response.registry_latest} (up to date ✔)")
        else:
            typer.echo(
                f"\n  Registry:  v{response.registry_latest} available "
                f"(run `skills-forge update {skill_name}` to upgrade)"
            )
    if response.registry_deprecated:
        typer.echo("  [DEPRECATED]")
        if response.registry_replaced_by:
            typer.echo(f"  Replaced by: {response.registry_replaced_by}")
        if response.registry_deprecation_message:
            typer.echo(f"  Note: {response.registry_deprecation_message}")


# ── doctor ────────────────────────────────────────────────────────────────────


@app.command(name="doctor")
def doctor(
    scope: str = typer.Option(
        "global",
        "--scope",
        "-s",
        help="Installation scope: global or project",
    ),
    registry: str = typer.Option(
        "",
        "--registry",
        "-r",
        help="Registry base URL to check for stale versions",
    ),
    no_registry: bool = typer.Option(
        False,
        "--no-registry",
        help="Skip the registry stale-version check (faster, offline-safe)",
    ),
) -> None:
    """Health-check all installed skills.

    Checks for broken symlinks, unresolved dependencies, and stale versions.
    Exits non-zero if any ERROR-severity issues are found.

    Examples:

      skills-forge doctor
      skills-forge doctor --no-registry
      skills-forge doctor --registry https://raw.githubusercontent.com/…/main
    """
    from skill_forge.domain.model import Severity, SkillScope

    skill_scope = SkillScope.GLOBAL if scope == "global" else SkillScope.PROJECT

    # Auto-resolve registry URL from config unless explicitly suppressed
    registry_url = ""
    if not no_registry:
        if registry:
            registry_url = registry
        else:
            cfg = load_config()
            default_reg = next((r for r in cfg.registries if r.name == cfg.default_registry), None)
            if default_reg:
                registry_url = default_reg.url

    use_case = build_doctor_use_case(registry_url=registry_url)
    response = use_case.execute(scope=skill_scope, registry_url=registry_url)

    if response.checked_count == 0:
        typer.echo(f"No skills installed at {skill_scope.value} scope — nothing to check.")
        return

    typer.echo(f"\n  Checked {response.checked_count} skill(s):")

    if response.is_healthy:
        typer.echo("  ✔ All skills are healthy.")
        return

    for issue in response.issues:
        icon = "✘" if issue.severity == Severity.ERROR else "⚠"
        typer.echo(f"  {icon} {issue}")

    typer.echo(f"\n  {response.failure_count} error(s), {response.warning_count} warning(s).")

    if response.failure_count:
        raise typer.Exit(code=1)


# ── update ────────────────────────────────────────────────────────────────────


@app.command(name="update")
def update(
    skill_name: str | None = typer.Argument(
        None,
        help="Skill to update. Omit to update all installed skills.",
    ),
    scope: str = typer.Option(
        "global",
        "--scope",
        "-s",
        help="Installation scope: global or project",
    ),
    target: str = typer.Option(
        "claude",
        "--target",
        "-t",
        help="Agent-CLI target directory to install into: claude, gemini, codex, agents, all",
    ),
    registry: str = typer.Option(
        "",
        "--registry",
        "-r",
        help="Registry base URL (falls back to configured default)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show available updates without installing",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Apply all updates without prompting for confirmation",
    ),
    pin: str = typer.Option(
        "",
        "--pin",
        help="Pin to a specific version instead of registry latest",
    ),
) -> None:
    """Update installed skills to the latest version from the registry.

    Compares each installed skill's version against the registry latest,
    then downloads and installs any newer packs found.

    Examples:

      # Update all installed skills (with confirmation prompts)
      skills-forge update

      # Update a specific skill
      skills-forge update my-skill

      # Dry-run: see what would be updated without installing
      skills-forge update --dry-run

      # Update everything without prompts
      skills-forge update --yes
    """
    from skill_forge.application.use_cases.update_skill import UpdateRequest
    from skill_forge.domain.model import InstallTarget, SkillScope

    skill_scope = SkillScope.GLOBAL if scope == "global" else SkillScope.PROJECT
    try:
        skill_target = InstallTarget(target.lower())
    except ValueError:
        valid = ", ".join(t.value for t in InstallTarget)
        typer.echo(f"⚠ Unknown target '{target}'. Valid values: {valid}")
        raise typer.Exit(code=1) from None

    # Resolve registry URL from config when not explicitly provided
    registry_url = registry
    if not registry_url:
        cfg = load_config()
        default_reg = next((r for r in cfg.registries if r.name == cfg.default_registry), None)
        if default_reg:
            registry_url = default_reg.url

    if not registry_url:
        typer.echo(
            "⚠ No registry configured. "
            "Run `skills-forge registry add <name> <url>` first, or pass --registry."
        )
        raise typer.Exit(code=1)

    use_case = build_update_use_case(registry_url=registry_url)
    request = UpdateRequest(
        scope=skill_scope,
        target=skill_target,
        skill_name=skill_name,
        dry_run=dry_run,
        registry_url=registry_url,
        pin_version=pin,
    )

    try:
        response = use_case.execute(request)
    except ValueError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc
    except (RuntimeError, OSError) as exc:
        typer.echo(f"⚠ Could not reach registry: {exc}")
        raise typer.Exit(code=1) from exc

    if not response.records:
        typer.echo("No matching skills found in the registry.")
        return

    available = [r for r in response.records if r.would_update]
    if not available:
        typer.echo("✔ All installed skills are up to date.")
        return

    if dry_run:
        typer.echo(f"\n  {len(available)} update(s) available (dry-run):")
        for r in available:
            typer.echo(f"    {r.skill_name}  v{r.old_version} → v{r.new_version}")
        return

    # Show the update plan and ask for confirmation (unless --yes)
    typer.echo(f"\n  {len(available)} update(s) available:")
    for r in available:
        typer.echo(f"    {r.skill_name}  v{r.old_version} → v{r.new_version}")

    if not yes:
        confirmed = typer.confirm("\n  Proceed with update?", default=True)
        if not confirmed:
            typer.echo("  Aborted.")
            raise typer.Exit(code=0)

    for r in response.records:
        if r.updated:
            typer.echo(f"  ✔ Updated {r.skill_name} v{r.old_version} → v{r.new_version}")

    typer.echo(f"\n  ✔ Updated {response.updated_count}/{len(available)} skill(s).")


# ── registry subcommand group ─────────────────────────────────────────────────

registry_app = typer.Typer(
    name="registry",
    help="Manage named registry entries in ~/.skills-forge/config.toml.",
    no_args_is_help=True,
)
app.add_typer(registry_app, name="registry")


@registry_app.command(name="list")
def registry_list() -> None:
    """List all configured registries."""
    cfg = load_config()
    if not cfg.registries:
        typer.echo("No registries configured.")
        typer.echo("  Add one with: skills-forge registry add <name> <url>")
        return
    for reg in cfg.registries:
        default_tag = " (default)" if reg.name == cfg.default_registry else ""
        auth_tag = " [auth]" if reg.token else ""
        typer.echo(f"  {reg.name}{default_tag}{auth_tag}")
        typer.echo(f"    {reg.url}")


@registry_app.command(name="add")
def registry_add(
    name: str = typer.Argument(..., help="Short identifier for the registry"),
    url: str = typer.Argument(..., help="Base URL of the registry"),
    token: str = typer.Option(
        "",
        "--token",
        "-t",
        help=(
            "Auth token for private registries. "
            "Supports env-var expansion: '${SKILLS_FORGE_TOKEN}'"
        ),
    ),
    set_default: bool = typer.Option(
        False,
        "--set-default",
        help="Make this the default registry after adding",
    ),
) -> None:
    """Add a named registry to the config."""
    repo = build_config_repo()
    cfg = repo.load()
    try:
        cfg.add_registry(name=name, url=url, token=token)
    except ValueError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc
    if set_default:
        cfg.set_default(name)
    repo.save(cfg)
    typer.echo(f"✔ Added registry '{name}' → {url}")
    if set_default:
        typer.echo("  Set as default registry.")
    typer.echo(f"  Config saved to {repo.path}")


@registry_app.command(name="remove")
def registry_remove(
    name: str = typer.Argument(..., help="Name of the registry to remove"),
) -> None:
    """Remove a registry from the config."""
    repo = build_config_repo()
    cfg = repo.load()
    try:
        cfg.remove_registry(name)
    except KeyError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc
    repo.save(cfg)
    typer.echo(f"✔ Removed registry '{name}'")


@registry_app.command(name="set-default")
def registry_set_default(
    name: str = typer.Argument(..., help="Name of the registry to set as default"),
) -> None:
    """Set the default registry used when --registry / --base-url are omitted."""
    repo = build_config_repo()
    cfg = repo.load()
    try:
        cfg.set_default(name)
    except KeyError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc
    repo.save(cfg)
    typer.echo(f"✔ Default registry set to '{name}'")


# ── yank command ─────────────────────────────────────────────────────────────


@app.command(name="yank")
def yank(
    skill_ref: str = typer.Argument(
        ...,
        help="Skill to yank in '<name>@<version>' format (e.g. python-tdd@1.0.0)",
    ),
    registry: Path = typer.Option(
        ...,
        "--registry",
        "-r",
        help="Path to local clone of the registry repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    base_url: str = typer.Option(
        ...,
        "--url",
        "-u",
        help="Base URL of the registry (e.g. https://raw.githubusercontent.com/org/registry/main)",
    ),
    reason: str = typer.Option(
        "",
        "--reason",
        help="Human-readable explanation for yanking this version",
    ),
    push: bool = typer.Option(
        False,
        "--push",
        help="Push the commit to the remote repository after yanking",
    ),
    registry_name: str = typer.Option(
        "registry",
        "--name",
        "-n",
        help="Registry name (used in index metadata)",
    ),
) -> None:
    """Yank a published skill version from the registry.

    The version is hidden from update resolution and install-latest but
    remains downloadable by pinning the exact version.  The pack file is
    never deleted — only the index is updated.

    Examples:

      skills-forge yank python-tdd@1.0.0 \\
          -r ./skill-registry -u https://raw.githubusercontent.com/org/registry/main \\
          --reason "Security: prompt injection vector"

      # Yank and push the commit immediately
      skills-forge yank my-skill@0.2.0 -r ./registry -u https://… --push
    """
    from skill_forge.application.use_cases.yank_skill import YankRequest

    # Parse "name@version"
    if "@" not in skill_ref:
        typer.echo(f"⚠ skill_ref must be in '<name>@<version>' format, got: {skill_ref!r}")
        raise typer.Exit(code=1)
    skill_name, version = skill_ref.rsplit("@", 1)

    use_case = build_yank_use_case(
        registry_root=registry,
        registry_name=registry_name,
        base_url=base_url,
    )
    request = YankRequest(
        skill_name=skill_name,
        version=version,
        reason=reason,
        push=push,
    )

    try:
        response = use_case.execute(request)
    except ValueError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc

    if response.was_already_yanked:
        typer.echo(f"⚠ {response.skill_name}@{response.version} was already yanked.")
    else:
        reason_note = f" — {response.yank_reason}" if response.yank_reason else ""
        typer.echo(f"✔ Yanked {response.skill_name}@{response.version}{reason_note}")
    if response.committed:
        typer.echo("  ✔ Committed to registry")
        if push:
            typer.echo("  ✔ Pushed to remote")


# ── deprecate command ─────────────────────────────────────────────────────────


@app.command(name="deprecate")
def deprecate(
    skill_name: str = typer.Argument(..., help="Name of the skill to deprecate"),
    registry: Path = typer.Option(
        ...,
        "--registry",
        "-r",
        help="Path to local clone of the registry repo",
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    base_url: str = typer.Option(
        ...,
        "--url",
        "-u",
        help="Base URL of the registry",
    ),
    replaced_by: str = typer.Option(
        "",
        "--replaced-by",
        help="Name of the skill that supersedes this one",
    ),
    message: str = typer.Option(
        "",
        "--message",
        "-m",
        help="Human-readable migration note shown to users",
    ),
    push: bool = typer.Option(
        False,
        "--push",
        help="Push the commit to the remote repository after deprecating",
    ),
    registry_name: str = typer.Option(
        "registry",
        "--name",
        "-n",
        help="Registry name (used in index metadata)",
    ),
) -> None:
    """Mark a skill as deprecated in the registry.

    Deprecated skills remain installable and visible in listings but show
    a notice directing users to the replacement.  All existing versions are
    retained; only the skill-level ``deprecated`` flag is set.

    Examples:

      skills-forge deprecate old-skill \\
          -r ./skill-registry -u https://raw.githubusercontent.com/org/registry/main \\
          --replaced-by new-skill --message "Replaced by new-skill which adds X"

      # Deprecate without a specific replacement
      skills-forge deprecate legacy-helper -r ./registry -u https://… \\
          --message "No longer maintained — use built-in helpers instead"
    """
    from skill_forge.application.use_cases.deprecate_skill import DeprecateRequest

    use_case = build_deprecate_use_case(
        registry_root=registry,
        registry_name=registry_name,
        base_url=base_url,
    )
    request = DeprecateRequest(
        skill_name=skill_name,
        replaced_by=replaced_by,
        message=message,
        push=push,
    )

    try:
        response = use_case.execute(request)
    except ValueError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc

    if response.was_already_deprecated:
        typer.echo(f"⚠ '{response.skill_name}' was already marked deprecated.")
    else:
        typer.echo(f"✔ Deprecated '{response.skill_name}'")
    if response.replaced_by:
        typer.echo(f"  Replaced by: {response.replaced_by}")
    if response.deprecation_message:
        typer.echo(f"  Note: {response.deprecation_message}")
    if response.committed:
        typer.echo("  ✔ Committed to registry")
        if push:
            typer.echo("  ✔ Pushed to remote")


# ── diff command ──────────────────────────────────────────────────────────────


@app.command(name="diff")
def diff(
    skill_name: str = typer.Argument(..., help="Name of the installed skill to diff"),
    scope: str = typer.Option(
        "global",
        "--scope",
        "-s",
        help="Installation scope: global or project",
    ),
    registry_url: str = typer.Option(
        "",
        "--registry",
        "-r",
        help=(
            "Base URL of a registry to diff against "
            "(e.g. https://raw.githubusercontent.com/org/registry/main). "
            "Required — use 'skills-forge config set-default-registry' if unset."
        ),
    ),
    context_lines: int = typer.Option(
        3,
        "--context",
        "-C",
        help="Number of context lines in the unified diff (default: 3)",
    ),
) -> None:
    """Show a unified diff of an installed skill vs the registry latest.

    Compares the local SKILL.md against the SKILL.md inside the latest
    pack in the registry.  Exits 0 when the skill is up-to-date, exits 1
    when a diff is found.

    Examples:

      skills-forge diff python-tdd \\
          --registry https://raw.githubusercontent.com/org/skill-registry/main

      # Narrower context for a quick change summary
      skills-forge diff python-tdd --context 1 -r https://…/registry/main
    """
    from skill_forge.domain.model import SkillScope

    _scope = SkillScope.PROJECT if scope == "project" else SkillScope.GLOBAL

    # Resolve registry URL from config when not provided on CLI
    _registry_url = registry_url
    if not _registry_url:
        try:
            cfg = load_config()
            default_reg = cfg.default_registry
            if default_reg:
                for reg in cfg.registries:
                    if reg.name == default_reg:
                        _registry_url = reg.url
                        break
        except Exception:
            pass

    if not _registry_url:
        typer.echo(
            "⚠ --registry is required (or set a default with "
            "'skills-forge config set-default-registry')."
        )
        raise typer.Exit(code=1)

    from skill_forge.application.use_cases.diff_skill import DiffRequest

    use_case = build_diff_use_case(registry_url=_registry_url)
    request = DiffRequest(
        skill_name=skill_name,
        scope=_scope,
        registry_url=_registry_url,
        context_lines=context_lines,
    )

    try:
        response = use_case.execute(request)
    except ValueError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1) from exc
    except (RuntimeError, OSError) as exc:
        typer.echo(f"⚠ Could not reach registry: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"  skill:     {response.skill_name}\n"
        f"  installed: {response.installed_version}\n"
        f"  registry:  {response.registry_version or '(not found)'}"
    )

    if not response.registry_version:
        typer.echo("  i Skill not found in registry -- nothing to diff.")
        return

    if not response.has_diff:
        typer.echo("  ✔ SKILL.md is identical to the registry version.")
        return

    typer.echo("")
    for line in response.diff_lines:
        typer.echo(line, nl=False)

    typer.echo("")
    typer.echo(f"  ↑ diff found — registry has {response.registry_version}")
    raise typer.Exit(code=1)


# ── test command ──────────────────────────────────────────────────────────────


@app.command(name="test")
def test_skill(
    path: Path = typer.Argument(
        ...,
        help="Path to a skill directory or a directory containing skills",
        exists=True,
    ),
    filter_ids: list[int] = typer.Option(
        [],
        "--id",
        "-i",
        help="Run only specific eval case IDs (repeatable). Default: all.",
    ),
    timeout: int = typer.Option(
        120,
        "--timeout",
        "-T",
        help="Seconds to wait for each Claude call (default: 120).",
    ),
) -> None:
    """Run evals for a skill and grade each assertion.

    Requires the Claude CLI (claude) to be installed and on PATH.
    Exits non-zero if any assertion fails.

    Examples:

      # Run all evals for a single skill
      skills-forge test output_skills/evaluation/ai-eng-evaluator/

      # Run only eval cases 1 and 3
      skills-forge test output_skills/evaluation/ai-eng-evaluator/ --id 1 --id 3

      # Run evals for every skill in a category
      skills-forge test output_skills/evaluation/
    """
    from skill_forge.application.use_cases.test_skill import AssessSkillRequest

    skill_paths = _collect_skill_paths(path)
    if not skill_paths:
        typer.echo("No SKILL.md files found.")
        raise typer.Exit(code=1)

    parser = build_parser()
    use_case = build_test_use_case()
    request = AssessSkillRequest(
        skill_path=str(path),
        filter_ids=list(filter_ids),
        timeout=timeout,
    )

    overall_exit = 0

    for skill_path in skill_paths:
        raw = skill_path.read_text(encoding="utf-8")
        skill = parser.parse(raw, base_path=skill_path.parent)

        if not skill.has_evals:
            typer.echo(f"  ⚠ {skill.identity.slug}: no evals — skipping")
            continue

        typer.echo(f"\nRunning {len(skill.evals)} eval(s) for {skill.identity.slug}…")
        response = use_case.execute(request, skill)

        for cr in response.case_results:
            status_icon = "✅" if cr.passed else "❌"
            if cr.error:
                typer.echo(f"  {status_icon} eval-{cr.case.id}  ERROR: {cr.error}")
                overall_exit = 1
                continue

            typer.echo(
                f"  {status_icon} eval-{cr.case.id}  {cr.pass_count}/{cr.total_count} assertions"
            )
            for ar in cr.assertion_results:
                if not ar.passed:
                    typer.echo(f"       ✘ {ar.assertion.id}: {ar.reason}")

        pct = int(response.pass_rate * 100)
        typer.echo(
            f"\n  Pass rate: {pct}%  "
            f"({response.passed_assertions}/{response.total_assertions} assertions)"
        )

        if not response.all_passed:
            overall_exit = 1

    if overall_exit:
        raise typer.Exit(code=1)


def _collect_skill_paths(path: Path) -> list[Path]:
    if path.is_file() and path.name == "SKILL.md":
        return [path]
    if path.is_dir():
        return sorted(path.rglob("SKILL.md"))
    return []


def main() -> None:
    app()


if __name__ == "__main__":
    main()
