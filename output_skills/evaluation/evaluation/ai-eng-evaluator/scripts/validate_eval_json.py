#!/usr/bin/env python3
"""Validate eval_data.json against the expected schema before PDF generation.

Usage:
    python validate_eval_json.py --input eval_data.json

Exit codes:
    0 — valid
    1 — validation errors found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REQUIRED_TOP_LEVEL = {
    "candidate_name", "project_name", "date", "repo_url",
    "tech_stack", "repo_summary",
    "creation_mastery", "integrity_autonomy",
    "curiosity_evangelism", "collaboration_humanity",
    "engineering_practices",
}

CREATION_MASTERY_KEYS = {
    "code_quality", "documentation", "conv_tooling", "ai_tooling",
    "learning", "shaping", "ways_of_working", "teaching",
}

INTEGRITY_KEYS = {"task_complexity", "ownership", "planning"}
CURIOSITY_KEYS = {"business_impact"}
COLLABORATION_KEYS = {"communication", "company_match", "proactivity"}

CATEGORY_IDS = {
    "clean_architecture", "testing", "static_analysis", "pipeline",
    "ai_frameworks", "security", "dependency_management", "observability",
    "error_handling", "prompt_engineering", "api_design", "configuration",
    "code_complexity",
}

VALID_RATINGS = {"PASS", "WARN", "FAIL"}
VALID_IMPACTS = {-1, 0, 1}
VALID_FINDING_TYPES = {"VIOLATION", "WARNING", "GOOD_PRACTICE"}


def validate(data: dict) -> list[str]:
    """Return a list of error messages. Empty = valid."""
    errors: list[str] = []

    # Top-level keys
    missing = REQUIRED_TOP_LEVEL - set(data.keys())
    if missing:
        errors.append(f"Missing top-level keys: {sorted(missing)}")
        return errors  # Can't continue without structure

    # creation_mastery (9-level)
    cm = data["creation_mastery"]
    cm_missing = CREATION_MASTERY_KEYS - set(cm.keys())
    if cm_missing:
        errors.append(f"Missing creation_mastery competencies: {sorted(cm_missing)}")

    for key in CREATION_MASTERY_KEYS & set(cm.keys()):
        comp = cm[key]
        if "level9" not in comp:
            errors.append(f"creation_mastery.{key}: missing 'level9'")
        elif not (0 <= comp["level9"] <= 8):
            errors.append(f"creation_mastery.{key}: level9={comp['level9']} out of range 0-8")
        if "evidence" not in comp:
            errors.append(f"creation_mastery.{key}: missing 'evidence'")
        elif len(comp["evidence"]) < 20:
            errors.append(f"creation_mastery.{key}: evidence too short ({len(comp['evidence'])} chars)")

    # 3-level sections
    for section_name, expected_keys, section_data in [
        ("integrity_autonomy", INTEGRITY_KEYS, data.get("integrity_autonomy", {})),
        ("curiosity_evangelism", CURIOSITY_KEYS, data.get("curiosity_evangelism", {})),
        ("collaboration_humanity", COLLABORATION_KEYS, data.get("collaboration_humanity", {})),
    ]:
        s_missing = expected_keys - set(section_data.keys())
        if s_missing:
            errors.append(f"Missing {section_name} competencies: {sorted(s_missing)}")
        for key in expected_keys & set(section_data.keys()):
            comp = section_data[key]
            if "level3" not in comp:
                errors.append(f"{section_name}.{key}: missing 'level3'")
            elif not (0 <= comp["level3"] <= 2):
                errors.append(f"{section_name}.{key}: level3={comp['level3']} out of range 0-2")

    # Engineering practices
    ep = data.get("engineering_practices", {})
    if "score_adjustment" not in ep:
        errors.append("engineering_practices: missing 'score_adjustment'")
    elif not (-2 <= ep["score_adjustment"] <= 1):
        errors.append(f"engineering_practices: score_adjustment={ep['score_adjustment']} out of range -2..+1")

    if "categories" not in ep:
        errors.append("engineering_practices: missing 'categories'")
    else:
        found_ids = set()
        for cat in ep["categories"]:
            cat_id = cat.get("id", "UNKNOWN")
            found_ids.add(cat_id)

            if cat_id not in CATEGORY_IDS:
                errors.append(f"engineering_practices: unknown category id '{cat_id}'")

            rating = cat.get("rating")
            if rating not in VALID_RATINGS:
                errors.append(f"category '{cat_id}': invalid rating '{rating}'")

            impact = cat.get("impact")
            if impact not in VALID_IMPACTS:
                errors.append(f"category '{cat_id}': invalid impact '{impact}'")

            for finding in cat.get("findings", []):
                ftype = finding.get("type")
                if ftype not in VALID_FINDING_TYPES:
                    errors.append(f"category '{cat_id}': invalid finding type '{ftype}'")
                if not finding.get("label"):
                    errors.append(f"category '{cat_id}': finding missing 'label'")
                if not finding.get("location"):
                    errors.append(f"category '{cat_id}': finding missing 'location'")

        missing_cats = CATEGORY_IDS - found_ids
        if missing_cats:
            errors.append(f"Missing engineering_practices categories: {sorted(missing_cats)}")

        # Verify impact sum matches score_adjustment
        actual_sum = sum(cat.get("impact", 0) for cat in ep["categories"])
        capped = max(-2, min(1, actual_sum))
        if ep.get("score_adjustment") != capped:
            errors.append(
                f"score_adjustment={ep.get('score_adjustment')} but sum of "
                f"impacts={actual_sum} (capped={capped})"
            )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate eval_data.json")
    parser.add_argument("--input", required=True, help="Path to eval_data.json")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"ERROR: File not found: {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    errors = validate(data)

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s):\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)
    else:
        print("✔ eval_data.json is valid")
        sys.exit(0)


if __name__ == "__main__":
    main()
