"""Adapter: file-system-based skill repository."""

from __future__ import annotations

from pathlib import Path

from skill_forge.domain.model import Skill
from skill_forge.domain.ports import SkillParser, SkillRenderer, SkillRepository


class FilesystemSkillRepository(SkillRepository):
    """Stores skills as directories on the local filesystem.

    Layout:
        base_path/
            <category>/
                <skill-slug>/
                    SKILL.md
                    references/
                    scripts/
                    assets/
    """

    SKILL_FILENAME = "SKILL.md"

    def __init__(
        self,
        base_path: Path,
        renderer: SkillRenderer,
        parser: SkillParser,
    ) -> None:
        self._base_path = base_path
        self._renderer = renderer
        self._parser = parser

    # Template eval case scaffolded for every new skill
    _EVALS_TEMPLATE = """\
[
  {
    "id": 1,
    "prompt": "Describe what this skill does in one sentence.",
    "expected_output": "A concise one-sentence description of the skill's purpose.",
    "assertions": [
      {
        "id": "response-not-empty",
        "text": "The response is not empty",
        "type": "not-contains",
        "expected": ""
      },
      {
        "id": "quality-check",
        "text": "The response is a coherent, complete sentence describing the skill",
        "type": "llm-judge"
      }
    ],
    "files": []
  }
]
"""

    def save(self, skill: Skill) -> Path:
        skill_dir = self._skill_dir(skill)
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = skill_dir / self.SKILL_FILENAME
        content = self._renderer.render_skill_md(skill)
        skill_md.write_text(content, encoding="utf-8")

        if skill.references:
            (skill_dir / "references").mkdir(exist_ok=True)

        if skill.scripts:
            (skill_dir / "scripts").mkdir(exist_ok=True)

        if skill.assets:
            (skill_dir / "assets").mkdir(exist_ok=True)

        if skill.examples:
            (skill_dir / "examples").mkdir(exist_ok=True)

        # Always scaffold evals/ with a starter eval case
        evals_dir = skill_dir / "evals"
        evals_dir.mkdir(exist_ok=True)
        (evals_dir / "fixtures").mkdir(exist_ok=True)
        evals_json = evals_dir / "evals.json"
        if not evals_json.exists():
            evals_json.write_text(self._EVALS_TEMPLATE, encoding="utf-8")

        return skill_dir

    def load(self, path: Path) -> Skill:
        skill_md = path if path.name == self.SKILL_FILENAME else path / self.SKILL_FILENAME
        if not skill_md.exists():
            raise FileNotFoundError(f"No SKILL.md found at {path}")
        content = skill_md.read_text(encoding="utf-8")
        return self._parser.parse(content, base_path=skill_md.parent)

    def exists(self, skill: Skill) -> bool:
        return (self._skill_dir(skill) / self.SKILL_FILENAME).exists()

    def list_all(self) -> list[Skill]:
        skills: list[Skill] = []
        if not self._base_path.exists():
            return skills

        for skill_md in self._base_path.rglob(self.SKILL_FILENAME):
            try:
                skill = self.load(skill_md)
                skills.append(skill)
            except Exception as exc:
                import sys

                print(
                    f"Warning: failed to load {skill_md}: {exc}",
                    file=sys.stderr,
                )
                continue
        return skills

    def _skill_dir(self, skill: Skill) -> Path:
        return self._base_path / skill.identity.category / skill.identity.slug
