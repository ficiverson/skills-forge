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
- Use scripts for repeatable automation — avoid inline one-liners
- Validate script output before presenting to user
- {{ principle }}

## Workflow

### Step 1 — {{ step_1_name }}

{{ step_1_instructions }}

### Step 2 — {{ step_2_name }}

{{ step_2_instructions }}

### Step 3 — Generate output

```bash
python <skill_path>/scripts/{{ script_name }} --input {{ input_file }} --output {{ output_file }}
```

### Step 4 — Validate output

```bash
python <skill_path>/scripts/validate_output.py --input {{ output_file }}
```

### Step 5 — Present result

Use present_files to surface the output. Give a brief verbal summary.

## Constraints

- Always verify script output before presenting to user
- Keep responses focused on the skill's domain
- {{ constraint }}

## Hints

Conditional guidance — apply only when relevant:

- {{ hint_1 }}
- {{ hint_2 }}

## References

Load these on-demand when the task requires deeper context:

- [{{ ref_purpose }}](references/{{ ref_filename }})

## Examples

Sample outputs showing expected format and quality:

- [{{ example_description }}](examples/{{ example_filename }})

## Assets

Static files bundled with this skill:

- [{{ asset_description }}](assets/{{ asset_filename }})
