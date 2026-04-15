# CLI Command Reference

All skills-forge commands follow the pattern `skills-forge <command> [options]`.

---

## create

Scaffold a new skill from a template.

```bash
skills-forge create -n <name> -c <category> -d "<description>" -e <emoji> [-v 0.1.0] [-o output_skills]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--name` | `-n` | Kebab-case skill name (e.g. `python-tdd`) |
| `--category` | `-c` | Category directory (e.g. `development`) |
| `--description` | `-d` | Single-sentence description with trigger phrases |
| `--emoji` | `-e` | Starter emoji for the skill |
| `--version` | `-v` | Initial version, default `0.1.0` |
| `--output` | `-o` | Output base directory, default `output_skills` |

---

## lint

Validate a skill directory or a tree of skills.

```bash
skills-forge lint <path>           # single skill directory
skills-forge lint output_skills/   # lint every skill in the tree
```

Exits `0` when all skills are clean, `1` when any errors are found.

---

## install

Install a skill into one or more agent tool directories.

```bash
# Local directory
skills-forge install output_skills/development/python-tdd

# Remote .skillpack from a URL
skills-forge install https://example.com/python-tdd-0.1.0.skillpack --sha256 <hash>

# Project scope (writes to .claude/skills/ in CWD)
skills-forge install output_skills/development/python-tdd --scope project

# All supported tools at once
skills-forge install output_skills/development/python-tdd --target all
```

| Option | Default | Description |
|--------|---------|-------------|
| `--scope` / `-s` | `global` | `global` (home dir) or `project` (CWD) |
| `--target` / `-t` | `claude` | `claude`, `gemini`, `codex`, `vscode`, `agents`, `all` |
| `--sha256` | *(none)* | Expected SHA-256 hash for URL installs |
| `--no-deps` | *(off)* | Skip dependency resolution check |

---

## export

Export a packed skill to a format suitable for another AI platform.

```bash
skills-forge export <path-to.skillpack> -f <format> [-o output_dir]
```

| Format | Description |
|--------|-------------|
| `system-prompt` | Plain system-prompt text (default) |
| `gpt-json` | OpenAI Custom GPT JSON configuration |
| `gem-txt` | Google Gemini Gem instructions text |
| `bedrock-xml` | AWS Bedrock agent prompt XML template |
| `mcp-server` | Self-contained Python MCP server module |
| `mistral-json` | Mistral AI system-prompt JSON |
| `gemini-api` | Gemini Developer API prompt format |
| `openai-assistants` | OpenAI Assistants API JSON |

---

## lint

```bash
skills-forge lint <path>
```

Runs all validators and prints issues with severity, rule ID, and message.

---

## pack / unpack

```bash
skills-forge pack <skill-dir...> [-o output_dir]
skills-forge unpack <pack.skillpack> [-o destination]
```

`pack` bundles one or more skill directories into a `.skillpack` zip archive with a `manifest.json`. `unpack` extracts the archive.

---

## list

```bash
skills-forge list [directory]
```

Lists skills in a directory tree with version, token estimate, and eval count. Defaults to `output_skills/`.

---

## info

```bash
skills-forge info <skill-name> [--scope global|project] [--registry <url>]
```

Displays detailed information about an installed skill: version, install paths, dependencies, eval count, and optionally whether a newer version is available.

---

## update

```bash
skills-forge update [--skill <name>] [--registry <url>] [--scope global|project]
```

Checks all installed skills (or one named skill) against a registry and updates any that have newer versions.

---

## diff

```bash
skills-forge diff <skill-name> --registry <url> [--scope global|project]
```

Shows a unified diff between the installed version and the latest version in the registry.

---

## doctor

```bash
skills-forge doctor [--scope global|project] [--no-registry]
```

Diagnoses installation health: broken symlinks, missing SKILL.md files, dependency gaps, and outdated skills.

---

## registry

```bash
skills-forge registry list
skills-forge registry add <name> <url>
skills-forge registry remove <name>
skills-forge registry set-default <name>
```

Manage named registry entries in `~/.skills-forge/config.toml`.

---

## publish

```bash
skills-forge publish <pack.skillpack> -r <registry-clone> -u <base-url> [--push]
```

Publish a `.skillpack` to a Git-backed registry: copies the pack, updates `index.json`, commits, and optionally pushes.

---

## yank

```bash
skills-forge yank <skill-name> <version> [--registry <name>] [--push]
```

Mark a published version as yanked in the registry. Yanked versions are hidden from update resolution but remain downloadable by exact version.

---

## deprecate

```bash
skills-forge deprecate <skill-name> <version> [--reason "..."] [--registry <name>]
```

Deprecate a skill version with an optional reason message.

---

## test

```bash
skills-forge test <skill-dir> [--eval <name>] [--provider <claude|openai>]
```

Run evals defined in a skill's `evals/` directory.

---

## init

```bash
skills-forge init
```

Initialise a new workspace: creates `output_skills/`, `templates/`, and `CLAUDE.md`.
