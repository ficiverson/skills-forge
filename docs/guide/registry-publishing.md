# Registry & Publishing

skills-forge supports a Git-backed registry model. A registry is a Git repository with a standardised layout that stores `.skillpack` archives and an `index.json` catalog.

---

## Registry layout

```
skill-registry/
├── index.json        # Machine-readable catalog of all published skills
└── packs/
    ├── development/
    │   └── python-tdd-0.1.0.skillpack
    └── productivity/
        └── daily-standup-0.2.0.skillpack
```

---

## Configuring registries

```bash
# Add a registry
skills-forge registry add public https://raw.githubusercontent.com/ficiverson/skill-registry/main

# Set as default
skills-forge registry set-default public

# List configured registries
skills-forge registry list

# Remove a registry
skills-forge registry remove old-registry
```

Registry configuration is stored in `~/.skills-forge/config.toml`.

---

## Publishing a skill

```bash
# 1. Pack the skill
skills-forge pack output_skills/development/python-tdd -o packs/

# 2. Publish to a registry clone
skills-forge publish packs/python-tdd-0.1.0.skillpack \
  --registry-clone /path/to/registry-clone \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --push
```

The `publish` command:

1. Validates pack metadata (name, version, description, tags, owner)
2. Copies the pack to `packs/<category>/` in the registry clone
3. Updates `index.json` with the new version
4. Creates a git commit
5. Optionally pushes to the remote (with `--push`)

### Required metadata

Skills must have these frontmatter fields before publishing:

| Field | Example |
|-------|---------|
| `description` | Full description with trigger phrases |
| `tags` | `python, tdd, testing` |
| `owner` | `@myteam` or `myname` |

---

## Installing from registry

```bash
# Install the latest version of a skill
skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.1.0.skillpack

# With SHA256 verification (recommended)
skills-forge install https://... --sha256 <hash>
```

---

## Updating skills

```bash
# Check and update all installed skills
skills-forge update --registry https://raw.githubusercontent.com/ficiverson/skill-registry/main

# Update a specific skill
skills-forge update --skill python-tdd --registry https://...

# Dry-run: see what would be updated without applying
skills-forge update --dry-run --registry https://...
```

---

## Yanking versions

If a published version has a bug or security issue, yank it:

```bash
skills-forge yank python-tdd 0.1.0 --registry public --push
```

Yanked versions:

- Are hidden from `update` resolution (users won't auto-update to them)
- Remain downloadable by exact version (preserving reproducibility)
- Are marked in `index.json` with `"yanked": true`

---

## Deprecating skills

```bash
skills-forge deprecate python-tdd 0.1.0 --reason "Use python-tdd-v2 instead" --registry public
```

---

## Hosting your own registry

Any Git repository with the required layout works as a registry. GitHub Actions can automate publishing on push:

```yaml
# .github/workflows/publish-skill.yml
on:
  push:
    paths:
      - 'output_skills/**'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install skills-forge
      - run: |
          skills-forge pack output_skills/development/python-tdd
          skills-forge publish packs/python-tdd-*.skillpack \
            --registry-clone . \
            --base-url ${{ vars.REGISTRY_BASE_URL }} \
            --push
```
