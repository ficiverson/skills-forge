# Repository Exploration Guide

## Step 1a — Top-level survey

Run: `find <repo_root> -type f | sort`

Note: language(s), framework(s), top-level structure, presence of tests/docs/CI/Docker.

## Step 1b — Read these files in order (check every item, do not skip)

Always read if present:

1. README.md / README.rst — stated goals, architecture, setup instructions
2. Dockerfile, docker-compose.yml, .dockerignore — containerisation quality
3. .github/workflows/ or .gitlab-ci.yml — CI/CD pipelines
4. Main entry point (app/main.py, src/index.ts, etc.)
5. Core business logic files (agents, services, pipelines)
6. Data models / schemas
7. Test files (tests/, __tests__/, spec/)
8. pyproject.toml / package.json / requirements.txt — dependencies and tooling
9. Configuration files (.env.example, linting configs, pre-commit hooks)

Spec and planning documents — open ALL subdirectories, not just list them:

10. Any specs/, docs/, or design/ top-level folder.
    For each numbered spec folder (e.g. specs/001-feature/), read:
    - spec.md — requirements and user stories
    - plan.md — implementation approach
    - contracts/ — interface definitions
    - research.md — technology decisions
    - quickstart.md — onboarding guide

    Shaping and Teaching scores depend on what is actually inside these files,
    not just that the folders exist.

## Step 1c — Key questions to answer before scoring

- Does the code actually run? Is there a working entry point?
- What AI/ML frameworks are used and how deeply?
- Are tests present? What kind (unit / integration / E2E / performance)?
- Is Docker present and correct?
- Is there a CI/CD pipeline?
- How is state/session managed?
- Are there guardrails, safety layers, or error handling?
- How is the code documented?
- What design patterns are visible (SOLID, Clean Architecture, etc.)?
- Do spec subdirectories contain contracts, research docs, or quickstart guides?
- Is there tool calling? Search for @tool, bind_tools, tool_calls in the codebase.

## AI workflow tooling check (CRITICAL)

Search for any of these patterns: `.specify/`, `.github/agents/`, `CLAUDE.md`,
`copilot-instructions.md`, `.cursor/rules`, `agent-instructions.md`, or any
`agents/` directory inside `.github/` or root.

If found, note it explicitly: "AI workflow tooling detected: [path]"
and carry that flag into the self-consistency check.
