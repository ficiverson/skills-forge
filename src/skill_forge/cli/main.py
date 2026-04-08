"""CLI entry point for skills-forge."""

from __future__ import annotations

from pathlib import Path

import typer

from skill_forge.cli.factory import (
    build_install_from_url_use_case,
    build_installer,
    build_lint_use_case,
    build_pack_use_case,
    build_publish_use_case,
    build_renderer,
    build_repository,
    build_unpack_use_case,
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
        "--output", "-o",
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


@app.command()
def list_skills(
    directory: Path = typer.Argument(
        Path("output_skills"),
        help="Base directory containing skills",
    ),
) -> None:
    """List all skills in a directory."""
    repo = build_repository(directory)
    skills = repo.list_all()

    if not skills:
        typer.echo("No skills found.")
        return

    for skill in skills:
        tokens = skill.total_estimated_tokens
        marker = "✔" if tokens <= 1200 else "⚠"
        typer.echo(f"  {marker} {skill.identity} (~{tokens} tokens)")


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
        "global", "--scope", "-s",
        help="Installation scope: global (user home) or project (current directory)",
    ),
    target: str = typer.Option(
        "claude", "--target", "-t",
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
) -> None:
    """Install a skill from a local path or a remote .skillpack URL.

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
        raise typer.Exit(code=1)

    if source.startswith(("http://", "https://")):
        from skill_forge.application.use_cases.publish_skill import (
            InstallFromUrlRequest,
        )

        use_case = build_install_from_url_use_case()
        request = InstallFromUrlRequest(
            url=source,
            dest_dir=output,
            scope=skill_scope,
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
        InstallSkill,
        InstallSkillRequest,
    )

    installer = build_installer()
    local_use_case = InstallSkill(installer=installer)
    local_request = InstallSkillRequest(
        skill_path=skill_path,
        scope=skill_scope,
        target=skill_target,
    )
    try:
        local_response = local_use_case.execute(local_request)
    except ValueError as exc:
        typer.echo(f"⚠ {exc}")
        raise typer.Exit(code=1)

    for path in local_response.installed_paths:
        typer.echo(f"✔ Installed at {path} ({skill_scope.value}, {skill_target.value})")


@app.command()
def uninstall(
    skill_name: str = typer.Argument(..., help="Name of the skill to uninstall"),
    scope: str = typer.Option(
        "global", "--scope", "-s", help="Installation scope: global or project"
    ),
) -> None:
    """Uninstall a previously installed skill."""
    from skill_forge.application.use_cases.install_skill import (
        UninstallSkill,
        UninstallSkillRequest,
    )
    from skill_forge.domain.model import SkillScope

    skill_scope = SkillScope.GLOBAL if scope == "global" else SkillScope.PROJECT
    installer = build_installer()
    use_case = UninstallSkill(installer=installer)

    request = UninstallSkillRequest(skill_name=skill_name, scope=skill_scope)
    response = use_case.execute(request)

    if response.was_installed:
        typer.echo(f"✔ Uninstalled '{skill_name}' ({response.scope.value})")
    else:
        typer.echo(f"⚠ Skill '{skill_name}' was not installed ({response.scope.value})")
        raise typer.Exit(code=1)


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
        owner_name=owner_name,
        owner_email=owner_email,
        deprecated=deprecated,
    )
    response = use_case.execute(request)

    typer.echo(
        f"✔ Packed {response.manifest.skill_count} skill(s) into {response.pack_path}"
    )
    typer.echo(f"  name:    {response.manifest.name}")
    typer.echo(f"  version: {response.manifest.version}")
    if response.manifest.author:
        typer.echo(f"  author:  {response.manifest.author}")
    for ref in response.manifest.skills:
        typer.echo(f"  - {ref.category}/{ref.name} @ {ref.version}")


@app.command()
def unpack(
    pack_path: Path = typer.Argument(
        ..., help="Path to a .skillpack file", exists=True
    ),
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
    for ref, path in zip(
        response.manifest.skills, response.extracted_paths, strict=True
    ):
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
    message: str = typer.Option(
        "", "--message", "-m", help="Git commit message"
    ),
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
    """Initialize a skills-forge workspace with the recommended structure."""
    output_dir = directory / "output_skills"
    output_dir.mkdir(parents=True, exist_ok=True)

    claude_md = directory / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(
            "# Skill Forge Workspace\n\n"
            "This workspace uses skills-forge to create and manage Claude Code skills.\n\n"
            "## Commands\n\n"
            "- `skills-forge create` — scaffold a new skill\n"
            "- `skills-forge lint` — validate skill quality\n"
            "- `skills-forge install` — install a skill for Claude Code\n"
            "- `skills-forge list` — list all skills\n",
            encoding="utf-8",
        )

    typer.echo(f"✔ Initialized skills-forge workspace at {directory.resolve()}")


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
