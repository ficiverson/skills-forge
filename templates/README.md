# Skill Templates

Copy the template that fits your use case into `output_skills/<category>/<skill-name>/`, then replace the `{{ placeholders }}` with your actual content.

```bash
cp -r templates/with-references output_skills/my-category/my-skill
```

## Choosing a template

| Template | Use when | Directories included |
|----------|----------|---------------------|
| **minimal** | Simple skill with just principles and instructions. No external files needed. | — |
| **with-references** | Skill that loads detailed docs on-demand during specific workflow steps. | `references/`, `examples/` |
| **with-scripts** | Skill that runs automation scripts and produces structured output. | `references/`, `scripts/`, `examples/`, `assets/` |
| **full-featured** | Complex multi-step skill using all features: workflow steps, validation, generation scripts, references, examples, and assets. | `references/`, `scripts/`, `examples/`, `assets/` |

## What each section does

| Section | Purpose | When to use |
|---------|---------|-------------|
| **Principles** | Guiding rules Claude always follows | Always — every skill needs at least 2-3 |
| **Workflow / Instructions** | Step-by-step procedure | Workflow for multi-step; Instructions for simple skills |
| **Constraints** | Hard rules and boundaries | Always — prevents Claude from going off-track |
| **Hints** | Conditional guidance applied only when relevant | When behavior should vary by context (language, project structure, etc.) |
| **References** | On-demand docs loaded during specific steps | When detailed guidance would bloat the SKILL.md body |
| **Examples** | Sample outputs showing expected format | When the skill produces structured output (JSON, reports, etc.) |
| **Assets** | Static data files (CSVs, configs, images) | When scripts or Claude need bundled data at runtime |

## Frontmatter fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Skill name in kebab-case |
| `version` | no | Semver string (defaults to `0.1.0`). Bump this when shipping a change so `skill-forge pack`/`publish` produce a new versioned `.skillpack`. |
| `description` | yes | Trigger description (aim for 30-150 tokens). Include trigger keywords and file extensions. |
| `depends_on` | no | Other skills this one depends on. Format: `skill-name (reason)` |

## Progressive disclosure budget

Keep these targets in mind while filling in placeholders:

| Layer | Loaded when | Token budget |
|-------|------------|-------------|
| Description (frontmatter) | Always at startup | ~100 tokens |
| SKILL.md body | On activation | ~500-1200 tokens |
| references/ | On demand per step | Unlimited |

If your SKILL.md body exceeds ~1200 tokens, move details into `references/`.

## Placeholder conventions

All placeholders use `{{ double_braces }}`. Replace every one — the linter will catch broken links if you forget to create the referenced files.

Common patterns:

- `{{ name }}` — kebab-case skill name (e.g., `python-tdd`)
- `{{ emoji }}` — single emoji for STARTER_CHARACTER (e.g., `🔴`)
- `{{ trigger_1 }}` — specific keyword or file extension (e.g., `.py`, `pytest`)
- `{{ ref_1_filename }}` — filename inside `references/` (e.g., `scoring-guide.md`)
- `{{ hint_1 }}` — conditional statement starting with "If" (e.g., `If the project uses TypeScript, check tsconfig.json`)
