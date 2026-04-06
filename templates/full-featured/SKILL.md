---
name: {{ name }}
version: 0.1.0
description: |
  {{ description }}
  Triggers on: {{ trigger_1 }}, {{ trigger_2 }}, {{ trigger_3 }}.
  {{ mandatory_triggers_note }}
depends_on: {{ dependency_skill }} ({{ dependency_reason }})
---

STARTER_CHARACTER = {{ emoji }}

## Principles

- {{ principle_1 }}
- {{ principle_2 }}
- {{ principle_3 }}

## Workflow

Follow these steps in strict order. Load references on-demand as each step requires.

### Step 0 — Understand inputs

{{ step_0_instructions }}

### Step 1 — {{ step_1_name }}

Read [{{ ref_1_purpose }}](references/{{ ref_1_filename }}) for the full checklist.

{{ step_1_instructions }}

### Step 2 — {{ step_2_name }}

Read [{{ ref_2_purpose }}](references/{{ ref_2_filename }}) for detailed guidance.

{{ step_2_instructions }}

### Step 3 — {{ step_3_name }}

{{ step_3_instructions }}

Validate the output before proceeding:

```bash
python <skill_path>/scripts/validate_output.py --input {{ output_file }}
```

### Step 4 — Generate final artifact

```bash
python <skill_path>/scripts/{{ generate_script }} \
  --input  {{ output_file }} \
  --output {{ final_artifact }}
```

### Step 5 — Present result

Use present_files to surface the artifact. Give a brief verbal summary:
{{ summary_format }}.

## Constraints

- {{ constraint_1 }}
- {{ constraint_2 }}
- {{ constraint_3 }}

## Hints

Conditional guidance — apply only when relevant:

- {{ hint_1 }}
- {{ hint_2 }}
- {{ hint_3 }}

## References

Load these on-demand when each step requires deeper context:

- [{{ ref_1_purpose }}](references/{{ ref_1_filename }})
- [{{ ref_2_purpose }}](references/{{ ref_2_filename }})
- [{{ ref_3_purpose }}](references/{{ ref_3_filename }})

## Examples

Sample outputs showing expected format and quality:

- [{{ example_1_description }}](examples/{{ example_1_filename }})
- [{{ example_2_description }}](examples/{{ example_2_filename }})

## Assets

Static files bundled with this skill:

- [{{ asset_1_description }}](assets/{{ asset_1_filename }})
- [{{ asset_2_description }}](assets/{{ asset_2_filename }})
