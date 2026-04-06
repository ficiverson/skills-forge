# Clean Principles Applied to Claude Code Skills

This guide maps well-known software design principles to skill authoring.
The goal: skills that trigger reliably, consume minimal context, and are
easy to maintain and share.

---

## Single Responsibility Principle (SRP)

A skill should have **one reason to change**.

**Bad:** A "Python Helper" skill that covers testing, linting, packaging,
deployment, and documentation. It triggers on everything Python and loads
a wall of instructions.

**Good:** Separate skills for "Python TDD", "Python Packaging", "Python
Linting". Each has a sharp description, focused principles, and small
context footprint.

**Heuristic:** If your SKILL.md has more than 3-4 sections under
Instructions, you probably need to split.

---

## Open/Closed Principle (OCP)

A skill should be **open for extension** (via references/) but **closed
for modification** of its core instructions.

The SKILL.md body defines stable principles. When you need to cover a new
sub-topic, add a reference document instead of bloating the main file.
Claude loads references on-demand, so extending a skill doesn't increase
its baseline context cost.

---

## Interface Segregation Principle (ISP)

The description (frontmatter) is your skill's **interface** — it's what
Claude sees at startup to decide whether to activate.

Keep it **lean and specific**. Don't pack every capability into the
description. Focus on the primary trigger scenarios. If a skill serves
multiple distinct user intents, that's a sign you need separate skills
(see SRP).

**Budget:** Aim for 30-150 tokens in the description.

---

## Dependency Inversion Principle (DIP)

Skills should depend on **principles**, not on specific tools or commands.

**Bad:** "Always run `pytest -xvs` then `ruff check --fix`."

**Good:** "Verify correctness with the project's test suite before
declaring done. Apply the project's configured linter."

This way the skill works across projects with different toolchains.
The principle is stable; the concrete tool is a detail that Claude
resolves at runtime.

---

## Progressive Disclosure (Context Layering)

This is the most important pattern for skills:

| Layer | Loaded when | Budget |
|-------|------------|--------|
| Description (frontmatter) | Always (startup) | ~100 tokens |
| SKILL.md body | On activation | ~500-1200 tokens |
| references/ | On demand | Unlimited |

**Rule of thumb:** If information is only needed for a specific sub-task,
it belongs in references/. If it's needed every time the skill activates,
it belongs in the body. If it helps Claude decide *whether* to activate,
it belongs in the description.

---

## Don't Repeat Yourself (DRY)

If two skills share logic, extract it:

- **Shared references:** Symlink a common reference file.
- **Shared scripts:** Put utility scripts in a shared location.
- **Composition:** One skill can reference another via instructions
  ("If the user also needs X, suggest activating the X skill").

---

## Naming Conventions

- **Skill name:** Noun or noun-phrase (`python-tdd`, `api-reviewer`)
- **Category:** Domain bucket (`development`, `documentation`, `devops`)
- **STARTER_CHARACTER:** Unique per skill, visually confirms activation
- **Description:** Third person, present tense, starts with action verb

---

## The Seven-Lens Description Review

Before finalizing a description, evaluate it through these lenses:

1. **Gist:** Does a 2-second scan tell you what the skill does?
2. **Name + Description pairing:** Do they complement without repeating?
3. **False positives:** Will this trigger on unrelated requests?
4. **False negatives:** Will it fail to trigger on valid requests?
5. **Overfocus:** Is it too narrow, missing common variations?
6. **Human scannability:** Could a teammate understand it instantly?
7. **Word necessity:** Can you remove any word without losing meaning?

---

## Context Budget Checklist

Before shipping a skill:

- [ ] Description < 150 tokens
- [ ] SKILL.md body < 1200 tokens
- [ ] Heavy details moved to references/
- [ ] No duplicate information across sections
- [ ] Principles guide behavior; instructions are minimal
- [ ] References are one level deep (no index chains)
