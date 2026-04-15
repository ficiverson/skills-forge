# Skill Anatomy

A skill is a directory containing `SKILL.md` — a Markdown file with YAML frontmatter and a structured body.

```
my-skill/
├── SKILL.md          # Required: frontmatter + instructions
├── references/       # Optional: supplementary docs
│   └── guide.md
├── scripts/          # Optional: helper scripts
│   └── setup.sh
├── examples/         # Optional: usage examples
│   └── sample.json
├── assets/           # Optional: data files
│   └── thresholds.csv
└── evals/            # Optional: evaluation assertions
    └── evals.json
```

---

## Frontmatter

```yaml
---
name: python-tdd           # kebab-case, must match directory name
version: 0.1.0             # semantic version
description: |
  Use this skill when writing Python code using Test-Driven Development.
  Triggers on: pytest, test-first, red-green-refactor, unit test.
emoji: 🔴                  # optional starter emoji
depends_on: pdf-skill      # optional dependency reference
---
```

### Required fields

| Field | Description |
|-------|-------------|
| `name` | Kebab-case skill name matching the directory name |
| `description` | Multi-sentence description. **Must include "Triggers on:" with at least one trigger phrase.** |

### Optional fields

| Field | Description |
|-------|-------------|
| `version` | Semantic version, defaults to `0.1.0` |
| `emoji` | Single emoji shown in Claude Code's skill picker |
| `depends_on` | Comma-separated list of skill names this skill requires |
| `tags` | Comma-separated tags for discovery |
| `owner` | Skill author or team |

---

## Body structure

The body follows a conventional Markdown structure:

```markdown
## Instructions

Core instructions for Claude to follow when this skill is active.
Keep this under ~1 000 tokens — it's loaded every time.

## Principles

- Principle one: short imperative statement
- Principle two: explains a constraint or value
- Principle three: defines a quality bar

## Constraints

- Never do X
- Always do Y before Z

## References

- [Rest conventions](references/rest-conventions.md): HTTP naming guide
- [Status codes](references/http-status-codes.md): when to use 4xx vs 5xx

## Scripts

- [setup](scripts/setup.sh): Initialise the environment

## Examples

- [sample eval](examples/sample-eval.json): Demonstrates expected output format
```

---

## Description guidelines

The description is the most important field — it determines when Claude activates the skill.

**Good description:**
```
Use this skill when reviewing REST API designs for consistency, naming, and HTTP semantics.
Triggers on: API review, endpoint design, REST conventions, OpenAPI .yaml .json.
```

**Bad description:**
```
Helps with API stuff.
```

Requirements enforced by `skills-forge lint`:

- Minimum length: ~50 characters
- Must contain "Triggers on:" with at least one phrase
- No vague filler words ("helps with", "various things", "stuff")
- Maximum ~150 tokens to avoid bloating context

---

## Progressive disclosure

Skills use progressive disclosure to stay lean:

1. **Description** (~100 tokens) — loaded on every message to decide activation
2. **Body** (~1 000 tokens) — loaded when the skill is active
3. **References** (on-demand) — fetched only when Claude needs the detail

Keep your `## Instructions` section focused. Push supporting material to `references/`. Use `## Scripts` for runnable helpers that Claude can invoke.

---

## Token budgets

| Section | Recommended |
|---------|-------------|
| Description | 50–150 tokens |
| Instructions | 200–800 tokens |
| Principles | 50–200 tokens |
| Constraints | 50–150 tokens |
| Total body | ≤ 1 500 tokens |

`skills-forge list` shows a token estimate for each skill.
