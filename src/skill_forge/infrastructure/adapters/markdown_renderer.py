"""Adapter: renders a Skill into SKILL.md markdown content."""

from __future__ import annotations

from skill_forge.domain.model import Skill
from skill_forge.domain.ports import SkillRenderer


class MarkdownSkillRenderer(SkillRenderer):
    """Renders skills as markdown following Claude Code conventions."""

    def render_skill_md(self, skill: Skill) -> str:
        sections: list[str] = []
        sections.append(self._render_frontmatter(skill))
        sections.append(self._render_body(skill))
        return "\n".join(sections)

    def render_reference(self, content: str, purpose: str) -> str:
        return f"# {purpose}\n\n{content}\n"

    def _render_frontmatter(self, skill: Skill) -> str:
        lines = [
            "---",
            f"name: {skill.identity.name}",
            f"version: {skill.version}",
            "description: |",
        ]
        for line in skill.description.text.strip().splitlines():
            lines.append(f"  {line}")
        if skill.depends_on:
            deps = ", ".join(
                f"{d.skill_name} ({d.reason})" if d.reason else d.skill_name
                for d in skill.depends_on
            )
            lines.append(f"depends_on: {deps}")
        lines.append("---")
        return "\n".join(lines)

    def _render_body(self, skill: Skill) -> str:
        parts: list[str] = []

        if skill.starter_character:
            parts.append(
                f"STARTER_CHARACTER = {skill.starter_character}\n"
            )

        if skill.content.principles:
            parts.append("## Principles\n")
            for principle in skill.content.principles:
                parts.append(f"- {principle}")
            parts.append("")

        if skill.content.instructions:
            parts.append("## Instructions\n")
            parts.append(skill.content.instructions)
            parts.append("")

        if skill.content.constraints:
            parts.append("## Constraints\n")
            for constraint in skill.content.constraints:
                parts.append(f"- {constraint}")
            parts.append("")

        if skill.content.hints:
            parts.append("## Hints\n")
            parts.append(skill.content.hints)
            parts.append("")

        if skill.scripts:
            parts.append("## Scripts\n")
            for script in skill.scripts:
                parts.append(f"- [{script.description}]({script.path})")
            parts.append("")

        if skill.references:
            parts.append("## References\n")
            parts.append(
                "Load these on-demand when the task requires deeper context:\n"
            )
            for ref in skill.references:
                parts.append(f"- [{ref.purpose}]({ref.path})")
            parts.append("")

        if skill.examples:
            parts.append("## Examples\n")
            parts.append(
                "Sample outputs showing expected format and quality:\n"
            )
            for example in skill.examples:
                parts.append(f"- [{example.description}]({example.path})")
            parts.append("")

        if skill.assets:
            parts.append("## Assets\n")
            parts.append(
                "Static files bundled with this skill:\n"
            )
            for asset in skill.assets:
                parts.append(f"- [{asset.description}]({asset.path})")
            parts.append("")

        return "\n".join(parts)
