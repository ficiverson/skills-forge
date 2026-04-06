"""Adapter: parses SKILL.md content into a Skill domain object."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from skill_forge.domain.model import (
    DEFAULT_SKILL_VERSION,
    Asset,
    Dependency,
    Description,
    Example,
    Reference,
    Script,
    Skill,
    SkillContent,
    SkillIdentity,
    StarterCharacter,
)
from skill_forge.domain.ports import SkillParser


class MarkdownSkillParser(SkillParser):
    """Parses SKILL.md files into domain Skill objects."""

    def parse(self, content: str, base_path: Path | None = None) -> Skill:
        frontmatter = self._parse_frontmatter(content)
        body = self._strip_frontmatter(content)

        name = frontmatter.get("name", "unknown")
        description_text = frontmatter.get("description", "")
        category = self._infer_category(base_path)
        version = (frontmatter.get("version") or DEFAULT_SKILL_VERSION).strip()

        identity = SkillIdentity(name=name, category=category)
        description = Description(text=description_text.strip())
        starter = self._parse_starter_character(body)
        skill_content = self._parse_content(body)
        references = self._parse_references(body)
        scripts_raw = self._parse_link_section(body, "Scripts")
        examples = self._parse_link_section(body, "Examples")
        assets = self._parse_link_section(body, "Assets")
        depends_on = self._parse_dependencies(frontmatter)

        return Skill(
            identity=identity,
            description=description,
            starter_character=starter,
            content=skill_content,
            references=references,
            scripts=[
                Script(path=PurePosixPath(p), description=d)
                for p, d in scripts_raw
            ],
            examples=[
                Example(path=PurePosixPath(p), description=d)
                for p, d in examples
            ],
            assets=[
                Asset(path=PurePosixPath(p), description=d)
                for p, d in assets
            ],
            depends_on=depends_on,
            version=version,
        )

    def _parse_frontmatter(self, content: str) -> dict[str, str]:
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {}

        frontmatter: dict[str, str] = {}
        current_key = ""
        current_value_lines: list[str] = []

        for line in match.group(1).splitlines():
            # Key-value pair
            kv_match = re.match(r"^(\w+):\s*(.*)", line)
            if kv_match:
                if current_key:
                    frontmatter[current_key] = "\n".join(current_value_lines)
                current_key = kv_match.group(1)
                value = kv_match.group(2).strip()
                current_value_lines = [value] if value and value != "|" else []
            elif current_key and line.startswith("  "):
                current_value_lines.append(line.strip())

        if current_key:
            frontmatter[current_key] = "\n".join(current_value_lines)

        return frontmatter

    def _strip_frontmatter(self, content: str) -> str:
        match = re.match(r"^---\s*\n.*?\n---\s*\n?", content, re.DOTALL)
        if match:
            return content[match.end():]
        return content

    def _infer_category(self, base_path: Path | None) -> str:
        if base_path is None:
            return "uncategorized"
        # Convention: output_skills/<category>/<skill-name>/SKILL.md
        parts = base_path.parts
        for i, part in enumerate(parts):
            if part == "output_skills" and i + 1 < len(parts):
                return parts[i + 1]
        return base_path.name

    def _parse_starter_character(self, body: str) -> StarterCharacter | None:
        match = re.search(r"STARTER_CHARACTER\s*=\s*(\S+)", body)
        if match:
            return StarterCharacter(emoji=match.group(1))
        return None

    def _parse_content(self, body: str) -> SkillContent:
        principles = self._extract_section_list(body, "Principles")
        constraints = self._extract_section_list(body, "Constraints")
        instructions = self._extract_section_text(body, "Instructions")
        hints = self._extract_section_text(body, "Hints")

        return SkillContent(
            principles=principles,
            instructions=instructions,
            constraints=constraints,
            hints=hints,
        )

    def _parse_references(self, body: str) -> list[Reference]:
        references = []
        # Match markdown links: [purpose](path)
        ref_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        in_references = False

        for line in body.splitlines():
            if re.match(r"^##\s+References", line):
                in_references = True
                continue
            if in_references and line.startswith("## "):
                break
            if in_references:
                match = ref_pattern.search(line)
                if match:
                    references.append(Reference(
                        path=PurePosixPath(match.group(2)),
                        purpose=match.group(1),
                    ))

        return references

    def _extract_section_list(self, body: str, heading: str) -> list[str]:
        items = []
        in_section = False
        for line in body.splitlines():
            if re.match(rf"^##\s+{heading}", line):
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section and line.startswith("- "):
                items.append(line[2:].strip())
        return items

    def _extract_section_text(self, body: str, heading: str) -> str:
        lines = []
        in_section = False
        for line in body.splitlines():
            if re.match(rf"^##\s+{heading}", line):
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                lines.append(line)
        return "\n".join(lines).strip()

    def _parse_link_section(
        self, body: str, heading: str,
    ) -> list[tuple[str, str]]:
        """Parse a section containing markdown links into (path, description) pairs."""
        items: list[tuple[str, str]] = []
        ref_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        in_section = False

        for line in body.splitlines():
            if re.match(rf"^##\s+{heading}", line):
                in_section = True
                continue
            if in_section and line.startswith("## "):
                break
            if in_section:
                match = ref_pattern.search(line)
                if match:
                    items.append((match.group(2), match.group(1)))

        return items

    def _parse_dependencies(self, frontmatter: dict[str, str]) -> list[Dependency]:
        """Parse depends_on from frontmatter (comma-separated or multi-line)."""
        raw = frontmatter.get("depends_on", "").strip()
        if not raw:
            return []

        deps: list[Dependency] = []
        for line in raw.replace(",", "\n").splitlines():
            line = line.strip()
            if not line:
                continue
            # Format: "skill-name (reason)" or just "skill-name"
            dep_match = re.match(r"^([\w-]+)\s*(?:\(([^)]+)\))?$", line)
            if dep_match:
                deps.append(Dependency(
                    skill_name=dep_match.group(1),
                    reason=dep_match.group(2) or "",
                ))
        return deps
