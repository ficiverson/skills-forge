---
name: ai-eng-evaluator
description: |
  Evaluates AI engineering code challenge submissions (GitHub repos, zip files, or local folders)
  against a structured competency matrix and produces a professional PDF report.
  Triggers on: evaluate repo, score candidate, grade challenge, review submission,
  competency levels (Junior/Medior/Senior), growth framework, engineering rubric.
  Works for any language or stack, not just Python/LangChain.
depends_on: pdf (PDF generation for the final evaluation report)
---

STARTER_CHARACTER = ⚖️

## Principles

- Evidence over impression: every score must cite specific files and lines
- Read actual code, not just structure — a well-named folder tree means nothing without content
- Only score what is directly verifiable from code and documentation artifacts
- Principles and tool calling are the decisive signals — always search before scoring
- AI-generated artifacts are infrastructure scaffolding, not personal innovation
- A PASS impact is 0, not +1 — only concrete features exceeding the candidate's level justify +1

## Workflow

Follow these five steps in strict order. Load references on-demand as each step requires.

### Step 0 — Understand inputs

Confirm repo location (zip in uploads/, local path, or GitHub URL) and candidate name.
If the repo is a zip, extract it. Defaults: "Anonymous Candidate" and the repo name.

### Step 1 — Systematic repository exploration

Read [repo-exploration guide](references/repo-exploration.md) for the full file checklist.

Work through the repo methodically: top-level survey, read key files in order,
answer the key questions before scoring. Flag AI workflow tooling if detected.

### Step 2 — Score competencies

Read [scoring-anchors](references/scoring-anchors.md) for the 14 scored competencies,
their level indices, anchors, and cap conditions.

Score each competency with evidence. Run the self-consistency check.
Seven competencies are permanently skipped (shown as N/A in the PDF).

### Step 2b — Engineering Practices Audit

Read [engineering-audit](references/engineering-audit.md) for the 13 practice categories,
their check tables, rating rules, and anti-inflation rules.

Complete the evidence checklist before assigning impacts. Cross-reference audit
results against competency scores (Step 2c in the reference).

### Step 3 — Build evaluation JSON

Read [json-schema](references/json-schema.md) for the exact JSON structure.

Create eval_data.json with the 14 scored competencies plus the engineering_practices section.
Then validate it:

```bash
python <skill_path>/scripts/validate_eval_json.py --input eval_data.json
```

### Step 4 — Generate PDF

```bash
pip install reportlab --break-system-packages -q
python <skill_path>/scripts/generate_eval_pdf.py \
  --input  /sessions/<session>/eval_data.json \
  --output /sessions/<session>/mnt/outputs/<candidate_name>_evaluation.pdf
```

### Step 5 — Present result

Use present_files to surface the PDF. Give a brief verbal summary:
overall level and score, top 2 strengths, top 2 growth areas, hiring recommendation.

## Constraints

- Do not hallucinate evidence — if a file does not exist, do not assume it does
- Do not conflate "no CI" with "bad engineer" — note it as a gap, not a disqualifier
- Language-agnostic scoring — the matrix applies to any stack
- Do not credit AI-generated spec artifacts as personal learning or shaping
- Open spec subdirectories before scoring Shaping and Teaching

## Hints

Conditional guidance — apply only when relevant:

- If the repo has no tests directory at all, score code_quality ≤ 4 and teaching ≤ 3
- If AI workflow tooling is detected (.specify/, CLAUDE.md, .cursor/), apply the
  AI-generated artifact inflation rule from scoring-anchors before scoring learning,
  shaping, and teaching
- If the candidate uses a non-Python stack, adapt the scoring anchors accordingly —
  e.g. for TypeScript, look for tsconfig.json instead of mypy, eslint instead of ruff
- If the repo is a monorepo with multiple services, evaluate each service separately
  and then synthesize an overall score

## References

Load these on-demand when each step requires deeper context:

- [Full competency matrix](references/competency_matrix.md)
- [Repository exploration guide](references/repo-exploration.md)
- [Scoring anchors and cap conditions](references/scoring-anchors.md)
- [Engineering practices audit](references/engineering-audit.md)
- [JSON output schema](references/json-schema.md)

## Examples

Sample outputs showing expected format and quality:

- [Example evaluation JSON](examples/example-eval.json)

## Assets

Static files bundled with this skill:

- [Level thresholds CSV](assets/level-thresholds.csv)
