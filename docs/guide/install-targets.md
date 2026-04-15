# Install Targets

skills-forge can install a skill into multiple AI coding assistants simultaneously. Each target maps to a standard directory path.

---

## Supported targets

| Target | Global path | Project path | Tool |
|--------|-------------|--------------|------|
| `claude` (default) | `~/.claude/skills/` | `.claude/skills/` | Claude Code |
| `gemini` | `~/.gemini/skills/` | `.gemini/skills/` | Gemini CLI |
| `codex` | `~/.codex/skills/` | `.codex/skills/` | OpenAI Codex |
| `vscode` | *(not supported)* | `.github/skills/` | VS Code Copilot |
| `agents` | `~/.agents/skills/` | `.agents/skills/` | Universal (agentskills.io) |
| `all` | all of the above | all of the above | Every tool at once |

---

## Scopes

**Global scope** (default) — installs into your home directory. The skill is available to all projects.

```bash
skills-forge install output_skills/development/python-tdd
# → ~/.claude/skills/python-tdd → /path/to/output_skills/development/python-tdd
```

**Project scope** — installs into the current directory. The skill is available only to this project and is committed to source control.

```bash
cd my-project
skills-forge install /path/to/python-tdd --scope project
# → .claude/skills/python-tdd → /path/to/python-tdd
```

---

## Examples

```bash
# Install globally for Claude Code (default)
skills-forge install output_skills/development/python-tdd

# Install into a project for Gemini CLI
skills-forge install output_skills/development/python-tdd --target gemini --scope project

# Install for VS Code Copilot (project scope only)
skills-forge install output_skills/development/python-tdd --target vscode --scope project

# Install for every supported tool, globally
skills-forge install output_skills/development/python-tdd --target all

# Install for every supported tool in the current project
skills-forge install output_skills/development/python-tdd --target all --scope project
```

---

## The `agents` target

`.agents/skills/` is the universal cross-vendor path standardised by [agentskills.io](https://agentskills.io). Every conforming tool automatically scans this directory. It's the recommended target for **project-level** installs on teams that mix editors:

```bash
skills-forge install output_skills/development/python-tdd --target agents --scope project
```

---

## How install works

`skills-forge install` creates a **symbolic link** from the target skills directory to the source skill directory. This means:

- Editing the source SKILL.md immediately affects all tools
- No duplication of files
- `git status` in the source repo shows actual changes

When installing from a URL, the pack is first extracted to `output_skills/` (or `--output` directory), then a symlink is created.

---

## Uninstalling

Remove the symlink from the target directory:

```bash
rm ~/.claude/skills/python-tdd
rm .claude/skills/python-tdd
```

---

## Doctor check

Use `skills-forge doctor` to verify your installation is healthy:

```bash
skills-forge doctor
skills-forge doctor --scope project
```

This checks for broken symlinks, missing SKILL.md files, dependency gaps, and optionally compares versions against a registry.
