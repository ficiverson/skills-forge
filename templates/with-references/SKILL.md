---
name: {{ name }}
description: |
  {{ description }}
  Triggers on: {{ trigger_1 }}, {{ trigger_2 }}, {{ trigger_3 }}.
depends_on: {{ dependency_skill }} ({{ dependency_reason }})
---

STARTER_CHARACTER = {{ emoji }}

## Principles

- One clear responsibility: this skill does one thing well
- Load references on-demand, not upfront — keep the body lean
- Prefer principles over step-by-step recipes
- {{ principle }}

## Workflow

### Step 1 — {{ step_1_name }}

{{ step_1_instructions }}

### Step 2 — {{ step_2_name }}

Read [{{ ref_1_purpose }}](references/{{ ref_1_filename }}) for detailed guidance.

{{ step_2_instructions }}

### Step 3 — Present result

Summarize findings and surface any output files.

## Constraints

- Keep responses focused on the skill's domain
- Always check references/ before giving detailed guidance
- {{ constraint }}

## Hints

Conditional guidance — apply only when relevant:

- {{ hint_1 }}
- {{ hint_2 }}

## References

Load these on-demand when the task requires deeper context:

- [{{ ref_1_purpose }}](references/{{ ref_1_filename }})
- [{{ ref_2_purpose }}](references/{{ ref_2_filename }})

## Examples

Sample outputs showing expected format and quality:

- [{{ example_description }}](examples/{{ example_filename }})
