# Evaluation JSON Schema

Create `/sessions/<session>/eval_data.json` with the 14 scored competencies
PLUS the `engineering_practices` section.

Do not add the 7 skipped competencies — the PDF generator handles them automatically.

```json
{
  "candidate_name": "Anonymous Candidate",
  "project_name": "Project Name",
  "date": "Month YYYY",
  "repo_url": "https://github.com/... or local",
  "tech_stack": "Python, FastAPI, LangGraph, ...",
  "repo_summary": "One paragraph describing what the project does.",
  "creation_mastery": {
    "code_quality":    {"level9": 4, "evidence": "...", "strengths": ["..."], "gaps": ["..."]},
    "documentation":   {"level9": 5, "evidence": "...", "strengths": ["..."], "gaps": ["..."]},
    "conv_tooling":    {"level9": 4, "evidence": "...", "strengths": ["..."], "gaps": ["..."]},
    "ai_tooling":      {"level9": 5, "evidence": "...", "strengths": ["..."], "gaps": ["..."]},
    "learning":        {"level9": 4, "evidence": "...", "strengths": ["..."], "gaps": ["..."]},
    "shaping":         {"level9": 3, "evidence": "...", "strengths": ["..."], "gaps": ["..."]},
    "ways_of_working": {"level9": 3, "evidence": "...", "strengths": ["..."], "gaps": ["..."]},
    "teaching":        {"level9": 3, "evidence": "...", "strengths": ["..."], "gaps": ["..."]}
  },
  "integrity_autonomy": {
    "task_complexity": {"level3": 1, "evidence": "..."},
    "ownership":       {"level3": 1, "evidence": "..."},
    "planning":        {"level3": 1, "evidence": "..."}
  },
  "curiosity_evangelism": {
    "business_impact": {"level3": 1, "evidence": "..."}
  },
  "collaboration_humanity": {
    "communication":   {"level3": 1, "evidence": "..."},
    "company_match":   {"level3": 1, "evidence": "..."},
    "proactivity":     {"level3": 1, "evidence": "..."}
  },
  "engineering_practices": {
    "summary": "Brief summary of category results and net adjustment.",
    "score_adjustment": -1,
    "adjustment_reason": "One-sentence explanation of the net adjustment.",
    "categories": [
      {
        "id": "clean_architecture",
        "name": "Clean Architecture & Code Quality",
        "rating": "WARN",
        "impact": 0,
        "summary": "Brief summary of findings.",
        "findings": [
          {
            "type": "VIOLATION",
            "label": "SRP — God Function",
            "location": "app/agents/specialist.py:337-502",
            "description": "Detailed description of the finding.",
            "suggestion": "Actionable improvement suggestion."
          },
          {
            "type": "GOOD_PRACTICE",
            "label": "Layered module structure",
            "location": "app/agents/, app/graph/",
            "description": "Description of what was done well.",
            "suggestion": ""
          }
        ]
      }
    ]
  }
}
```

## Category IDs

Use these exact IDs in the `categories` array:
clean_architecture, testing, static_analysis, pipeline, ai_frameworks,
security, dependency_management, observability, error_handling,
prompt_engineering, api_design, configuration, code_complexity

## Finding types

- `VIOLATION` — something that needs fixing
- `WARNING` — something that could be improved
- `GOOD_PRACTICE` — something done well (suggestion can be empty)

## Rating values

Each category: `"PASS"`, `"WARN"`, or `"FAIL"`

## Impact values

Each category: `-1`, `0`, or `1`
Net `score_adjustment`: sum of all impacts, capped to range -2 … +1

## Overall level thresholds (weighted average, 0-10 scale)

```
9.3-10.0 → Senior-3    8.7-9.2 → Senior-2    8.0-8.6 → Senior-1
7.3-7.9  → Medior-3    6.5-7.2 → Medior-2    5.7-6.4 → Medior-1
4.8-5.6  → Junior-3    3.8-4.7 → Junior-2    0-3.7   → Junior-1
```
