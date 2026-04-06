"""CLI entry point for skill-forge."""

from __future__ import annotations

from pathlib import Path

import typer

from skill_forge.cli.factory import (
    build_installer,
    build_lint_use_case,
    build_renderer,
    build_repository,
)

app = typer.Typer(
    name="skill-forge",
    help="A clean-architecture toolkit for crafting Claude Code skills.",
    no_args_is_help=True,
)


@app.command()
def create(
    name: str = typer.Option(..., "--name", "-n", help="Skill name"),
    category: str = typer.Option(..., "--category", "-c", help="Skill category"),
    description: str = typer.Option(..., "--description", "-d", help="Trigger description"),
    emoji: str | None = typer.Option(None, "--emoji", "-e", help="Starter character emoji"),
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
    skill_path: Path = typer.Argument(..., help="Path to the skill directory", exists=True),
    scope: str = typer.Option(
        "global", "--scope", "-s", help="Installation scope: global or project"
    ),
) -> None:
    """Install a skill for Claude Code to discover."""
    from skill_forge.application.use_cases.install_skill import (
        InstallSkill,
        InstallSkillRequest,
    )
    from skill_forge.domain.model import SkillScope

    skill_scope = SkillScope.GLOBAL if scope == "global" else SkillScope.PROJECT
    installer = build_installer()
    use_case = InstallSkill(installer=installer)

    request = InstallSkillRequest(skill_path=skill_path, scope=skill_scope)
    response = use_case.execute(request)

    typer.echo(f"✔ Installed at {response.installed_path} ({response.scope.value})")


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
def init(
    directory: Path = typer.Argument(
        Path("."),
        help="Directory to initialize as a skill-forge workspace",
    ),
) -> None:
    """Initialize a skill-forge workspace with the recommended structure."""
    output_dir = directory / "output_skills"
    output_dir.mkdir(parents=True, exist_ok=True)

    claude_md = directory / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(
            "# Skill Forge Workspace\n\n"
            "This workspace uses skill-forge to create and manage Claude Code skills.\n\n"
            "## Commands\n\n"
            "- `skill-forge create` — scaffold a new skill\n"
            "- `skill-forge lint` — validate skill quality\n"
            "- `skill-forge install` — install a skill for Claude Code\n"
            "- `skill-forge list` — list all skills\n",
            encoding="utf-8",
        )

    typer.echo(f"✔ Initialized skill-forge workspace at {directory.resolve()}")


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
