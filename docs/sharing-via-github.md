# Sharing skills via raw.githubusercontent.com

This guide walks through a complete end-to-end example of distributing skills-forge skills using a plain GitHub repo as a free, CDN-backed registry. No GitHub Actions, no Releases, no S3, no extra services. Once your registry is set up, publishing a new skill version is one command, and teammates install it with one command.

> **Live example:** Every URL in this guide points at a real, working registry built with skills-forge: [github.com/ficiverson/skill-registry](https://github.com/ficiverson/skill-registry). You can `curl` the index, install one of the published packs, and use it as a reference layout for your own.
>
> ```bash
> curl https://raw.githubusercontent.com/ficiverson/skill-registry/main/index.json | jq
> ```

## Why this works

Every file in a public GitHub repo is reachable via the raw CDN at:

```
https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>
```

That URL is a stable, cacheable, anonymous-readable file endpoint. So if you commit a `.skillpack` to a repo, every teammate can `curl` it without any auth. `skills-forge publish` just automates the "commit a `.skillpack` to a repo, update an index, and print the URL" part. `skills-forge install <url>` automates the "fetch, verify, unpack, install" part.

The whole story is two commands plus a normal `git push`.

## The end state

By the end of this guide you'll have:

- A GitHub repo `ficiverson/skill-registry` with this layout:
  ```
  skill-registry/
  ├── README.md
  ├── index.json                                       ← machine catalog
  └── packs/
      └── development/
          ├── python-tdd-0.1.0.skillpack
          └── python-tdd-0.2.0.skillpack
  ```
- A teammate able to install any version with:
  ```bash
  skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.2.0.skillpack \
    --sha256 9c4f2a1b...
  ```

Let's build it.

## Step 1 — Create the registry repo on GitHub

Create a new empty repo on GitHub. For this example I'll use `ficiverson/skill-registry`. It can be public or private — the only difference is whether you'll need a `GITHUB_TOKEN` later.

```bash
# On github.com: create a new empty repo named "skill-registry"
# Then clone it locally:

git clone git@github.com:ficiverson/skill-registry.git
cd skill-registry

# Optional: write a tiny human-facing README so the repo isn't empty
cat > README.md <<'EOF'
# Skill Registry

A skills-forge registry. Install any skill below with:

```bash
skills-forge install <url> --sha256 <digest>
```

See `index.json` for the full catalog.
EOF

git add README.md
git commit -m "init registry"
git push -u origin main
```

That's the entire registry setup. No workflows, no settings, no protected branches. Just a normal repo.

> **Tip**: pin the default branch name. The publish command's `--base-url` includes the branch (`/main`), so if you ever rename the branch, every published URL changes. Stick with `main` (or whatever you pick) and don't rename.

## Step 2 — Author and pack a skill

In your normal skills-forge workspace (separate from the registry clone), create a skill:

```bash
cd ~/code/my-skills-forge-workspace

skills-forge create \
  --name python-tdd \
  --category development \
  --description "Use this skill when writing Python with a TDD workflow. Triggers on: pytest, unittest, test-first, red-green-refactor, .py files." \
  --emoji 🔴 \
  --version 0.1.0
```

Edit the generated `output_skills/development/python-tdd/SKILL.md` to fill in principles, workflow, constraints, and hints. Then lint until clean:

```bash
skills-forge lint output_skills/development/python-tdd
# ✔ development/python-tdd: clean
```

Pack it. The pack command auto-derives its version from the `version:` field in frontmatter, so you don't pass `--version`:

```bash
skills-forge pack output_skills/development/python-tdd
```

Output:

```
✔ Packed 1 skill(s) into ./python-tdd-0.1.0.skillpack
  name:    python-tdd
  version: 0.1.0
  - development/python-tdd @ 0.1.0
```

You now have `./python-tdd-0.1.0.skillpack` ready to publish.

## Step 3 — Publish to the registry

Point `publish` at your local clone of the registry repo and the public base URL of the raw CDN:

```bash
skills-forge publish ./python-tdd-0.1.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --message "python-tdd 0.1.0" \
  --tag tdd --tag python \
  --owner-name "Fer Souto" \
  --owner-email ficiverson@example.com \
  --release-notes "First public release" \
  --push
```

The `--tag`, `--owner-*`, and `--release-notes` flags are optional metadata that lands in `index.json` so teammates can browse the registry without downloading anything. Pass `--deprecated` later to flag a skill as superseded, or `--yanked` on a future publish to withdraw a bad version while keeping the audit trail.

The `--base-url` is the URL prefix that, combined with a repo-relative path, gives you a downloadable file. For a GitHub repo at `https://github.com/ficiverson/skill-registry` with default branch `main`, the formula is always:

```
https://raw.githubusercontent.com/<owner>/<repo>/<branch>
```

Output:

```
✔ Published python-tdd v0.1.0
  path:    packs/development/python-tdd-0.1.0.skillpack
  sha256:  9c4f2a1b8e6d3742fa87b9d1e205c4f8a2b6e9d1c7f4a8b3e2d5c9f1a6b7e8d2
  git:     committed
  git:     pushed

  Install URL:
  https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.1.0.skillpack

  Teammates can install with:
    skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.1.0.skillpack --sha256 9c4f2a1b8e6d3742fa87b9d1e205c4f8a2b6e9d1c7f4a8b3e2d5c9f1a6b7e8d2
```

Behind the scenes, `publish`:

1. Copies `python-tdd-0.1.0.skillpack` into `~/code/skill-registry/packs/development/`
2. Computes its sha256
3. Reads or creates `~/code/skill-registry/index.json`
4. Adds an entry for `development/python-tdd@0.1.0` with the sha256
5. Runs `git add packs/development/python-tdd-0.1.0.skillpack index.json`
6. Runs `git commit -m "python-tdd 0.1.0"`
7. Runs `git push` (because we passed `--push`)

If you'd rather review the diff before pushing, drop `--push`. The commit is already on your local branch — just `cd ~/code/skill-registry && git diff HEAD~1 && git push`.

After this command finishes, the install URL printed in the output is **live**. Anyone with access to the repo can download it.

## Step 4 — Inspect what got published

Take a look at the registry repo to see exactly what was added:

```bash
cd ~/code/skill-registry
git log --oneline -3
# d07d603 python-tdd 0.1.0
# a1b2c3d init registry

ls packs/development/
# python-tdd-0.1.0.skillpack

cat index.json
```

`index.json` looks like this:

```json
{
  "format_version": "1",
  "registry_name": "skill-registry",
  "base_url": "https://raw.githubusercontent.com/ficiverson/skill-registry/main",
  "updated_at": "2026-04-06T10:45:47+00:00",
  "skills": [
    {
      "category": "development",
      "name": "python-tdd",
      "latest": "0.1.0",
      "description": "Use this skill when writing Python with a TDD workflow.",
      "tags": ["tdd", "python"],
      "owner": {"name": "Fer Souto", "email": "ficiverson@example.com"},
      "versions": [
        {
          "version": "0.1.0",
          "path": "packs/development/python-tdd-0.1.0.skillpack",
          "sha256": "9c4f2a1b8e6d3742fa87b9d1e205c4f8a2b6e9d1c7f4a8b3e2d5c9f1a6b7e8d2",
          "published_at": "2026-04-06T10:45:47+00:00",
          "size_bytes": 4218,
          "release_notes": "First public release"
        }
      ]
    }
  ]
}
```

This file is the catalog. It records every published version, the path inside the repo, and a sha256 fingerprint, plus optional discoverability metadata so teammates can browse without unzipping anything. Tools and humans alike can read it with `curl https://raw.githubusercontent.com/ficiverson/skill-registry/main/index.json | jq`.

### Index schema reference

| Field | Level | Purpose |
|-------|-------|---------|
| `description` | skill | Mirrored from the skill's frontmatter so the index doubles as a searchable catalog |
| `tags` | skill | Free-form keywords passed via repeated `--tag` flags at publish time |
| `owner.name` / `owner.email` | skill | Maintainer contact, set with `--owner-name` / `--owner-email` |
| `deprecated` | skill | Set with `--deprecated` to flag a skill that should no longer be used |
| `published_at` | version | ISO 8601 timestamp written automatically by the publisher |
| `size_bytes` | version | Pack size on disk, written automatically |
| `release_notes` | version | Set with `--release-notes` to record what changed in this version |
| `yanked` | version | Set with `--yanked` to withdraw a version while keeping it in the audit trail (yanked versions are excluded when computing `latest`) |

All metadata fields are optional. Older `index.json` files that predate them keep installing fine — the codec fills in safe defaults on read.

## Step 5 — Install on a teammate's machine

A teammate (or your own laptop in a fresh shell) installs the skill in one command:

```bash
skills-forge install \
  https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.1.0.skillpack \
  --sha256 9c4f2a1b8e6d3742fa87b9d1e205c4f8a2b6e9d1c7f4a8b3e2d5c9f1a6b7e8d2
```

Output:

```
✔ Fetched 'python-tdd' v0.1.0 (9c4f2a1b8e6d…)
  → output_skills/development/python-tdd
    installed at /home/teammate/.claude/skills/python-tdd (global)
```

What just happened:

1. The fetcher downloaded the `.skillpack` from `raw.githubusercontent.com` to a temp file
2. It computed the sha256 of the download and compared it against `--sha256`. If it didn't match, the install would have aborted.
3. The pack was unpacked into `./output_skills/development/python-tdd/` (or whatever you pass via `--output`)
4. The unpacked skill was symlinked into `~/.claude/skills/python-tdd`
5. Claude Code picks it up the next time it scans skills

If you trust the source and don't want to copy-paste a sha256, you can omit `--sha256`. But for any team registry, including the digest is cheap insurance against accidental file corruption or someone replacing the file in-repo.

## Step 6 — Ship a new version

This is where per-skill versioning pays off. Bump the `version:` field in the skill's frontmatter:

```yaml
---
name: python-tdd
version: 0.2.0      # ← bumped from 0.1.0
description: |
  ...
---
```

Re-pack and re-publish. No flags need to change:

```bash
cd ~/code/my-skills-forge-workspace

skills-forge pack output_skills/development/python-tdd
# → ./python-tdd-0.2.0.skillpack

skills-forge publish ./python-tdd-0.2.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --message "python-tdd 0.2.0" \
  --push
```

Now the registry has both versions side by side:

```
skill-registry/
├── index.json
└── packs/
    └── development/
        ├── python-tdd-0.1.0.skillpack    ← still there
        └── python-tdd-0.2.0.skillpack    ← new
```

`index.json` is automatically updated to:

```json
{
  "skills": [
    {
      "category": "development",
      "name": "python-tdd",
      "latest": "0.2.0",
      "versions": [
        {"version": "0.1.0", "path": "packs/development/python-tdd-0.1.0.skillpack", "sha256": "9c4f2a1b..."},
        {"version": "0.2.0", "path": "packs/development/python-tdd-0.2.0.skillpack", "sha256": "f3e8b1c2..."}
      ]
    }
  ]
}
```

`latest` is recomputed using a semver-aware sort. Old versions stay reachable forever — teammates who pinned to `0.1.0` keep working, while teammates who want the new behavior install `0.2.0`.

## Step 7 — Discoverability via the index

Teammates who don't have an exact URL can browse the registry by fetching `index.json`:

```bash
curl -s https://raw.githubusercontent.com/ficiverson/skill-registry/main/index.json | jq '.skills[] | "\(.category)/\(.name) latest=\(.latest)"'
```

Output:

```
"development/python-tdd latest=0.2.0"
```

Or use the lower-level API directly from a Python script:

```python
from skill_forge.cli.factory import build_fetcher

fetcher = build_fetcher()
index = fetcher.fetch_index(
    "https://raw.githubusercontent.com/ficiverson/skill-registry/main/index.json"
)

for skill in index.skills:
    latest = skill.find(skill.latest)
    print(f"{skill.category}/{skill.name}@{skill.latest}")
    print(f"  install: {index.base_url}/{latest.path}")
    print(f"  sha256:  {latest.sha256}")
```

This is enough to build a tiny `skills-forge search` or `skills-forge upgrade` script tailored to your team's conventions.

## Private repos

Everything above works identically for a private GitHub repo. The only difference: teammates need a token to read raw URLs.

Set `GITHUB_TOKEN` in the environment before running `install`:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
skills-forge install https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.2.0.skillpack \
  --sha256 9c4f2a1b...
```

The HTTP fetcher detects the `raw.githubusercontent.com` host and adds an `Authorization: token <GITHUB_TOKEN>` header automatically. No other configuration needed. The token only needs `repo` scope for read access.

A practical pattern: put the token in your shell rc file so it's always present:

```bash
# In ~/.zshrc or ~/.bashrc
export GITHUB_TOKEN=$(security find-generic-password -s skills-forge-github-token -w)  # macOS Keychain
```

Or use a `.envrc` (with [direnv](https://direnv.net/)) so the token is only loaded inside your skills workspace.

## Picking a pinning strategy

You have three options for how teammates pin versions:

1. **Pin exact versions, manual upgrades.** Teammates install `python-tdd-0.2.0.skillpack` explicitly and only upgrade when they choose. Best for stability — nobody gets a surprise behavior change. Worst for staying current — you have to socialize new releases.

2. **Always install latest.** Teammates fetch `index.json`, look up `latest`, and install that URL. Pair with a team chat post when you publish a major change. Best for staying current. Worst when a release introduces a regression.

3. **Lockfile per project.** Commit a small `skills.lock` JSON in each project recording the exact versions it depends on. Re-running install reads the lockfile. Best for reproducibility but requires a wrapper script today (skills-forge doesn't ship a lockfile feature yet).

For most teams, option 1 with sha256 verification is the right starting point. Add option 2 once you have a half-dozen skills and people are getting tired of typing URLs.

## What goes in the registry repo's README

A human-readable index helps teammates discover what's available without writing jq queries. Generate a list from `index.json`:

```bash
cd ~/code/skill-registry
python - <<'PY' >> README.md
import json
data = json.load(open("index.json"))
print("\n## Available skills\n")
print("| Skill | Latest | Install |")
print("|-------|--------|---------|")
for s in data["skills"]:
    latest = next(v for v in s["versions"] if v["version"] == s["latest"])
    url = f'{data["base_url"]}/{latest["path"]}'
    print(f'| `{s["category"]}/{s["name"]}` | `{s["latest"]}` | `skills-forge install {url} --sha256 {latest["sha256"][:12]}...` |')
PY
git add README.md && git commit -m "refresh README" && git push
```

Or wire that as a git pre-push hook on the registry clone so it stays in sync automatically.

## Summary

The whole workflow in one screen:

```bash
# --- Maintainer ---
# 1. One-time: clone the registry repo
git clone git@github.com:ficiverson/skill-registry.git ~/code/skill-registry

# 2. Each release: bump version: in frontmatter, then:
skills-forge pack output_skills/development/python-tdd
skills-forge publish ./python-tdd-0.2.0.skillpack \
  --registry ~/code/skill-registry \
  --base-url https://raw.githubusercontent.com/ficiverson/skill-registry/main \
  --message "python-tdd 0.2.0" --push

# --- Teammate ---
skills-forge install \
  https://raw.githubusercontent.com/ficiverson/skill-registry/main/packs/development/python-tdd-0.2.0.skillpack \
  --sha256 9c4f2a1b...
```

That's it. No CI, no release tags, no S3 bucket, no Slack uploads, no registry server. Every published skill is a plain file in a plain git repo, served by a free CDN, verifiable by sha256, and reachable by one command.

## Troubleshooting

**`HTTP 404 fetching ...`** — The branch in your `--base-url` doesn't match the repo's default branch, or the file hasn't been pushed yet. Check `git status` in the registry clone and verify the URL in a browser.

**`HTTP 401 fetching ...`** — Private repo without a token. Set `GITHUB_TOKEN` in the environment and retry.

**`sha256 mismatch for downloaded pack`** — The file at the URL doesn't match the digest you passed. Either the digest is wrong (copy-paste issue) or the file was modified after publish. Re-derive the digest from `index.json`.

**`Download exceeded 50000000 bytes`** — Default size cap is 50 MB. Real skill packs are usually well under 1 MB. If you're hitting this, something is wrong (corrupted file, wrong URL pointing at a binary blob, etc.).

**`fatal: not a git repository`** during publish — `--registry` must point at a directory that contains a `.git/` folder. If you're publishing into a fresh directory for the first time, run `git init -b main` inside it before publishing.

**Publish committed but didn't push** — You forgot `--push`, or `git push` failed silently. Run `git -C <registry> log` and `git -C <registry> push` manually.
