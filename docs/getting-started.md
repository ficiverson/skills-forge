# Getting Started with skills-forge

This guide walks you through the full lifecycle: installing skills-forge, creating your first skill, validating it, and making it available to Claude Code.

## 1. Install skills-forge

Clone the repository and install in editable mode:

```bash
git clone https://github.com/<your-org>/skills-forge.git
cd skills-forge
pip install -e ".[dev]"
```

Verify:

```bash
skills-forge --help
```

## 2. Initialize a workspace

If you're starting from scratch (not using this repository directly):

```bash
mkdir my-skills && cd my-skills
skills-forge init
```

This creates an `output_skills/` directory and a `CLAUDE.md` file. If you cloned this repo, the workspace is already initialized — skills live in `output_skills/<category>/<skill-name>/`.

## 3. Create a skill

### Option A: Use the CLI scaffold

```bash
skills-forge create \
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
skills-forge lint output_skills/development/python-tdd/SKILL.md

# Lint all skills in a directory
skills-forge lint output_skills/
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
skills-forge install output_skills/development/python-tdd
```

This symlinks into `~/.claude/skills/python-tdd`. Every Claude Code session on your machine will see it.

### Project-scoped install

```bash
skills-forge install output_skills/development/python-tdd --scope project
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
2. **Is the description precise enough?** Run `skills-forge lint` and check for `description-missing-triggers`
3. **Does the description match your prompt?** The description is what Claude uses to decide whether to activate

## 8. Iterate

The typical workflow:

```
edit SKILL.md  →  skills-forge lint  →  test with Claude  →  repeat
```

Because of the symlink, you never need to reinstall after editing. Just lint to validate your changes, then test in a Claude session.

## 9. Bundle the skill into a .skillpack

Once a skill is good, bundle it into a single portable file you can share. A `.skillpack` is a zip containing one or more skill directories plus a JSON manifest.

```bash
# Bundle a single skill — version is auto-derived from frontmatter
skills-forge pack output_skills/development/python-tdd
# → ./python-tdd-0.2.0.skillpack

# Bundle multiple skills into a named bundle, baking metadata into the manifest
skills-forge pack \
  output_skills/development/python-tdd \
  output_skills/security/owasp-review \
  --name backend-team-bundle \
  --version 1.2.0 \
  --description "Backend defaults: TDD + OWASP review" \
  --tag backend --tag tdd --tag security \
  --owner-name "Fer Souto" --owner-email fer@example.com \
  --output backend-team-bundle.skillpack
```

The pack command reads `version:` from each skill's frontmatter. Bump that field whenever you ship a change so each release lands as its own versioned `.skillpack`.

The optional `--description`, `--tag`, `--owner-*`, and `--deprecated` flags travel inside the manifest so the same pack carries its own discoverability metadata. When you later run `skills-forge publish`, the registry index defaults to those values — passing the same flags on `publish` overrides them.

A teammate who receives the file extracts it with:

```bash
skills-forge unpack backend-team-bundle.skillpack --output output_skills/
```

Then lints and installs the unpacked skills with the usual commands.

## 10. Publish to a git-backed registry

`skills-forge publish` turns any git repo into a free, CDN-backed skill registry — no GitHub Actions, no releases server, no Slack uploads. It copies the pack into `packs/<category>/<name>-<version>.skillpack` inside a local clone, regenerates `index.json`, and commits. Once pushed to GitHub, every pack is reachable via `raw.githubusercontent.com`.

**One-time setup** — clone the registry repo locally:

```bash
git clone git@github.com:ficiverson/skill-registry.git
```

**Publish a pack:**

```bash
skills-forge publish ./python-tdd-0.2.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --message "python-tdd 0.2.0" \
  --push
```

Output:

```
✔ Published python-tdd v0.2.0
  path:    packs/development/python-tdd-0.2.0.skillpack
  sha256:  9c4f2a1b…
  git:     committed
  git:     pushed

  Install URL:
  https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.2.0.skillpack
```

Drop `--push` if you'd rather review the diff first; the commit is already on your local branch waiting for `git push`.

## 11. Install from a remote URL

`skills-forge install` accepts an `https://` URL alongside the existing local-path form, so teammates install published skills with a single command:

```bash
# Direct URL
skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.2.0.skillpack

# With sha256 verification (recommended — copy the digest from publish output)
skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.2.0.skillpack \
  --sha256 9c4f2a1b...

# Local install still works the same as before
skills-forge install output_skills/development/python-tdd
```

Behind the scenes the URL form fetches the pack to a temp file, verifies the sha256 if you supplied one, unpacks it via the regular `unpack` flow, and installs each contained skill into `~/.claude/skills/` (or `.claude/skills/` with `--scope project`).

For private GitHub repos, set `GITHUB_TOKEN` in your environment and the fetcher will pass it as a `token` Authorization header on `raw.githubusercontent.com` requests.

## Full CLI reference

| Command | Description |
|---------|-------------|
| `skills-forge init` | Initialize a workspace with `output_skills/` and `CLAUDE.md` |
| `skills-forge create` | Scaffold a new skill from options |
| `skills-forge lint <path>` | Validate a skill or directory of skills |
| `skills-forge list [directory]` | List all skills with token estimates |
| `skills-forge install <path-or-url>` | Install a skill from a local directory or remote `.skillpack` URL |
| `skills-forge uninstall <name>` | Remove an installed symlink |
| `skills-forge pack <skill-dir...>` | Bundle one or more skill directories into a `.skillpack` archive |
| `skills-forge unpack <pack>` | Extract a `.skillpack` into a destination directory |
| `skills-forge publish <pack>` | Publish a `.skillpack` to a git-backed registry |

### create options

| Flag | Required | Description |
|------|----------|-------------|
| `--name, -n` | yes | Skill name (kebab-case) |
| `--category, -c` | yes | Category bucket (e.g., development, testing) |
| `--description, -d` | yes | Trigger description (30-150 tokens) |
| `--emoji, -e` | no | STARTER_CHARACTER emoji |
| `--version, -v` | no | Initial semver written to frontmatter (default: `0.1.0`) |
| `--output, -o` | no | Base directory (default: `output_skills`) |

### install options

| Flag | Required | Description |
|------|----------|-------------|
| `--scope, -s` | no | `global` (default) or `project` |
| `--output, -o` | no | Where to unpack remote packs (default: `output_skills`). Only used for URL installs. |
| `--sha256` | no | Expected sha256 of a remote `.skillpack`. Verified before unpack. |

### pack options

| Flag | Required | Description |
|------|----------|-------------|
| `--output, -o` | no | Output file or directory (default: current dir; auto-named `<name>-<version>.skillpack` if a directory) |
| `--version, -v` | no | Pack version (defaults to the skill's own version from frontmatter for single-skill packs) |
| `--name, -n` | no | Pack name (defaults to the first skill's name) |
| `--author, -a` | no | Pack author |
| `--description, -d` | no | Short description for the manifest |

### publish options

| Flag | Required | Description |
|------|----------|-------------|
| `--registry, -r` | yes | Local clone of the registry git repo |
| `--base-url, -u` | yes | Public base URL, e.g. `https://raw.githubusercontent.com/<owner>/<repo>/main` |
| `--registry-name, -N` | no | Display name (defaults to the repo dir name) |
| `--message, -m` | no | Git commit message |
| `--push/--no-push` | no | Push the commit to the remote after writing the index (default: no-push) |
| `--tag, -t` | no | Tag for the skill (repeatable). Surfaces in the registry index for discovery. |
| `--owner-name` | no | Maintainer name recorded in `index.json` |
| `--owner-email` | no | Maintainer email recorded in `index.json` |
| `--deprecated` | no | Mark the skill as deprecated in the index |
| `--release-notes` | no | Release notes recorded with this version's index entry |
| `--yanked` | no | Mark this version as yanked (kept for audit, excluded from `latest`) |

The publisher also writes `published_at` and `size_bytes` for each version automatically, and mirrors the skill's frontmatter `description` into the index so teammates can browse without unzipping anything.
