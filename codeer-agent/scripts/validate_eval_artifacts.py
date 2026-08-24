#!/usr/bin/env python3
"""Validate persistent query-distribution and input-candidate CSV artifacts."""

from __future__ import annotations

import argparse
import csv
import math
import pathlib
import sys


DISTRIBUTION_COLUMNS = {
    "distribution_cell_id",
    "operating_model",
    "task_family",
    "task_id",
    "task_complication_id",
    "representativeness_band",
    "estimated_real_world_share",
    "eval_target_share",
    "industry_risk_level",
    "risk_type_ids",
    "evidence_tier",
    "evidence_confidence",
    "source_population",
    "adaptation_distance",
    "evidence_window",
    "source_channels",
    "sample_scope",
    "sample_size",
    "exclusions",
    "evidence_basis",
    "source_urls",
    "overweight_reason",
    "open_gap",
    "last_reviewed_at",
}

CANDIDATE_COLUMNS = {
    "candidate_id",
    "distribution_cell_id",
    "input_display",
    "target_user_query",
    "task_id",
    "task_complication_id",
    "industry_risk_level",
    "risk_type_ids",
    "challenge_pattern_ids",
    "channel_pattern_ids",
    "designed_challenge_level",
    "evidence_basis",
    "evidence_confidence",
    "cluster_id",
    "variant_family_id",
    "review_status",
    "source_urls",
}

ENUMS = {
    "representativeness_band": {"core", "common", "occasional", "rare", "unknown"},
    "industry_risk_level": {"normal", "elevated", "high", "critical"},
    "evidence_confidence": {"low", "medium", "high"},
    "designed_challenge_level": {"baseline", "moderate", "stress"},
    "evidence_basis": {
        "observed",
        "adapted",
        "expert_constructed",
        "synthetic_variant",
    },
    "review_status": {
        "generated",
        "evidence_checked",
        "domain_reviewed",
        "approved",
    },
}


def read_csv(path: pathlib.Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def parse_share(value: str, label: str, row_number: int, errors: list[str]) -> float | None:
    if not value.strip():
        return None
    try:
        parsed = float(value)
    except ValueError:
        errors.append(f"{label} row {row_number}: share is not numeric: {value!r}")
        return None
    if parsed < 0 or parsed > 1:
        errors.append(f"{label} row {row_number}: share must be between 0 and 1")
    return parsed


def validate_enum(
    row: dict[str, str],
    field: str,
    row_number: int,
    label: str,
    errors: list[str],
) -> None:
    value = row.get(field, "").strip()
    if value and value not in ENUMS[field]:
        errors.append(f"{label} row {row_number}: invalid {field}={value!r}")


def validate_unique(
    rows: list[dict[str, str]],
    field: str,
    label: str,
    errors: list[str],
) -> set[str]:
    seen: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        value = row.get(field, "").strip()
        if not value:
            errors.append(f"{label} row {row_number}: missing {field}")
        elif value in seen:
            errors.append(f"{label} row {row_number}: duplicate {field}={value!r}")
        seen.add(value)
    return seen


def validate(
    distribution_path: pathlib.Path,
    candidates_path: pathlib.Path,
) -> list[str]:
    errors: list[str] = []
    distribution_headers, distribution_rows = read_csv(distribution_path)
    candidate_headers, candidate_rows = read_csv(candidates_path)

    missing_distribution = DISTRIBUTION_COLUMNS - set(distribution_headers)
    missing_candidates = CANDIDATE_COLUMNS - set(candidate_headers)
    if missing_distribution:
        errors.append(
            "distribution: missing columns " + ", ".join(sorted(missing_distribution))
        )
    if missing_candidates:
        errors.append("candidates: missing columns " + ", ".join(sorted(missing_candidates)))
    if errors:
        return errors

    distribution_ids = validate_unique(
        distribution_rows, "distribution_cell_id", "distribution", errors
    )
    validate_unique(candidate_rows, "candidate_id", "candidates", errors)

    eval_shares: list[float] = []
    for row_number, row in enumerate(distribution_rows, start=2):
        for field in ("representativeness_band", "industry_risk_level", "evidence_confidence"):
            validate_enum(row, field, row_number, "distribution", errors)
        for field in (
            "source_population",
            "evidence_window",
            "sample_scope",
            "evidence_basis",
            "last_reviewed_at",
        ):
            if not row.get(field, "").strip():
                errors.append(f"distribution row {row_number}: missing {field}")
        eval_share = parse_share(
            row.get("eval_target_share", ""),
            "distribution",
            row_number,
            errors,
        )
        if eval_share is None:
            errors.append(f"distribution row {row_number}: missing eval_target_share")
        else:
            eval_shares.append(eval_share)
        parse_share(
            row.get("estimated_real_world_share", ""),
            "distribution",
            row_number,
            errors,
        )
        if row.get("eval_target_share", "").strip() and row.get(
            "estimated_real_world_share", ""
        ).strip():
            try:
                if (
                    float(row["eval_target_share"])
                    > float(row["estimated_real_world_share"]) + 1e-9
                    and not row.get("overweight_reason", "").strip()
                ):
                    errors.append(
                        f"distribution row {row_number}: overweight_reason required"
                    )
            except ValueError:
                pass

    if eval_shares and not math.isclose(sum(eval_shares), 1.0, abs_tol=1e-6):
        errors.append(
            f"distribution: eval_target_share totals {sum(eval_shares):.8f}, expected 1"
        )

    for row_number, row in enumerate(candidate_rows, start=2):
        for field in (
            "industry_risk_level",
            "designed_challenge_level",
            "evidence_basis",
            "evidence_confidence",
            "review_status",
        ):
            validate_enum(row, field, row_number, "candidates", errors)
        parent = row.get("distribution_cell_id", "").strip()
        if parent not in distribution_ids:
            errors.append(
                f"candidates row {row_number}: unknown distribution_cell_id={parent!r}"
            )
        for field in (
            "input_display",
            "target_user_query",
            "task_id",
            "cluster_id",
            "variant_family_id",
        ):
            if not row.get(field, "").strip():
                errors.append(f"candidates row {row_number}: missing {field}")
        if (
            row.get("designed_challenge_level") == "baseline"
            and row.get("challenge_pattern_ids", "").strip()
        ):
            errors.append(
                f"candidates row {row_number}: baseline should not carry challenge_pattern_ids"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution_csv", type=pathlib.Path)
    parser.add_argument("candidates_csv", type=pathlib.Path)
    args = parser.parse_args()

    errors = validate(args.distribution_csv, args.candidates_csv)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Validation failed with {len(errors)} issue(s).")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
