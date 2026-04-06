# Getting Started with skill-forge

This guide walks you through the full lifecycle: installing skill-forge, creating your first skill, validating it, and making it available to Claude Code.

## 1. Install skill-forge

Clone the repository and install in editable mode:

```bash
git clone https://github.com/<your-org>/skills-forge.git
cd skills-forge
pip install -e ".[dev]"
```

Verify:

```bash
skill-forge --help
```

## 2. Initialize a workspace

If you're starting from scratch (not using this repository directly):

```bash
mkdir my-skills && cd my-skills
skill-forge init
```

This creates an `output_skills/` directory and a `CLAUDE.md` file. If you cloned this repo, the workspace is already initialized — skills live in `output_skills/<category>/<skill-name>/`.

## 3. Create a skill

### Option A: Use the CLI scaffold

```bash
skill-forge create \
  --name python-tdd \
  --category development \
  --description "Use for TDD with Python. Triggers: pytest, test-first, red-green-refactor, .py files." \
  --emoji 🔴
```

This generates:

```
output_skills/development/python-tdd/
├── SKILL.md
└── references/     # (created if you add references)
```

### Option B: Copy a template

Templates are in `templates/`. Pick the one that fits your use case:

| Template | When to use |
|----------|-------------|
| `minimal` | Simple skill with just principles and instructions |
| `with-references` | Skill that needs on-demand reference docs |
| `with-scripts` | Skill that runs automation scripts |
| `full-featured` | Complex skill using all features |

```bash
cp -r templates/full-featured output_skills/my-category/my-skill
# Then edit output_skills/my-category/my-skill/SKILL.md
```

### Option C: Write from scratch

Create the directory and SKILL.md manually. At minimum you need:

```yaml
---
name: my-skill
description: |
  What this skill does and when Claude should activate it.
  Triggers on: keyword1, keyword2, .extension.
---
```

## 4. Add supporting files

Depending on your skill's complexity, add these directories:

```
my-skill/
├── SKILL.md              # Required: core skill definition
├── references/           # Optional: on-demand docs for specific steps
│   ├── guide.md
│   └── schema.md
├── scripts/              # Optional: automation scripts
│   ├── generate.py
│   └── validate_output.py
├── examples/             # Optional: sample outputs for calibration
│   └── example-output.json
└── assets/               # Optional: static data files
    └── thresholds.csv
```

Then link them in SKILL.md:

```markdown
## References

- [Detailed guide](references/guide.md)
- [Output schema](references/schema.md)

## Examples

- [Sample output](examples/example-output.json)

## Assets

- [Threshold data](assets/thresholds.csv)
```

### Why examples matter

An example output is the single most effective way to calibrate Claude's behavior. Instead of describing the expected format in words, show a complete example. Claude will match the tone, structure, and level of detail.

### Why validation scripts matter

If your skill generates structured output (JSON, CSV, etc.), add a validation script that checks the output before the final step. This catches malformed data before it reaches the user:

```markdown
### Step 3 — Validate output

```bash
python <skill_path>/scripts/validate_output.py --input result.json
```
```

## 5. Validate your skill

Run the linter to catch common problems:

```bash
# Lint a single skill
skill-forge lint output_skills/development/python-tdd/SKILL.md

# Lint all skills in a directory
skill-forge lint output_skills/
```

The linter runs two types of checks:

**Pure validators** check the skill's structure: description length, vague language, missing principles, context budget, etc.

**Path-aware validators** check the filesystem: every reference, example, asset, and script link in SKILL.md must resolve to a real file. If you link to `references/guide.md` but the file doesn't exist, you'll get a `broken-reference-link` error.

A clean lint looks like:

```
✔ development/python-tdd: clean
```

A failing lint shows each issue:

```
⚠ development/python-tdd:
  [ERROR] broken-reference-link (references/guide.md): Reference "references/guide.md" does not exist
  [WARNING] missing-starter-character (SKILL.md body): No STARTER_CHARACTER defined
```

Fix errors before installing. Warnings are recommendations. Info items are suggestions.

## 6. Install the skill

Install makes your skill visible to Claude Code. It creates a symlink from your source directory into Claude's skill discovery path.

### Global install (all projects)

```bash
skill-forge install output_skills/development/python-tdd
```

This symlinks into `~/.claude/skills/python-tdd`. Every Claude Code session on your machine will see it.

### Project-scoped install

```bash
skill-forge install output_skills/development/python-tdd --scope project
```

This symlinks into `.claude/skills/python-tdd` in the current directory. Only Claude Code sessions in this project will see it.

### What the symlink means

Because install uses symlinks, your installed skill always points back to the source in `output_skills/`. Edit the source, and the installed version updates instantly — no reinstall needed.

To verify:

```bash
ls -la ~/.claude/skills/
# python-tdd -> /path/to/skills-forge/output_skills/development/python-tdd
```

### Uninstalling

Currently, remove the symlink manually:

```bash
rm ~/.claude/skills/python-tdd
```

## 7. Test the skill

After installing, open a new Claude Code session and try a prompt that should trigger the skill. Look for the STARTER_CHARACTER emoji in the response — that confirms the skill activated.

If the skill doesn't trigger, check:

1. **Is the symlink valid?** `ls -la ~/.claude/skills/python-tdd/SKILL.md`
2. **Is the description precise enough?** Run `skill-forge lint` and check for `description-missing-triggers`
3. **Does the description match your prompt?** The description is what Claude uses to decide whether to activate

## 8. Iterate

The typical workflow:

```
edit SKILL.md  →  skill-forge lint  →  test with Claude  →  repeat
```

Because of the symlink, you never need to reinstall after editing. Just lint to validate your changes, then test in a Claude session.

## Full CLI reference

| Command | Description |
|---------|-------------|
| `skill-forge init` | Initialize a workspace with `output_skills/` and `CLAUDE.md` |
| `skill-forge create` | Scaffold a new skill from options |
| `skill-forge lint <path>` | Validate a skill or directory of skills |
| `skill-forge list [directory]` | List all skills with token estimates |
| `skill-forge install <path>` | Install a skill via symlink (default: global) |

### create options

| Flag | Required | Description |
|------|----------|-------------|
| `--name, -n` | yes | Skill name (kebab-case) |
| `--category, -c` | yes | Category bucket (e.g., development, testing) |
| `--description, -d` | yes | Trigger description (30-150 tokens) |
| `--emoji, -e` | no | STARTER_CHARACTER emoji |
| `--output, -o` | no | Base directory (default: `output_skills`) |

### install options

| Flag | Required | Description |
|------|----------|-------------|
| `--scope, -s` | no | `global` (default) or `project` |
