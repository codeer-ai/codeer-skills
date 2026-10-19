#!/usr/bin/env python3
"""Validate the lean Query Distribution and query-example CSV artifacts."""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys


DISTRIBUTION_COLUMNS = {
    "query_type_id",
    "customer_task",
    "journey_state",
    "demand_band",
    "risk_level",
    "target_cases",
}

EXAMPLE_COLUMNS = {
    "example_id",
    "query_type_id",
    "input",
    "provenance",
    "purpose",
}

ENUMS = {
    "demand_band": {"core", "common", "occasional", "rare", "unknown"},
    "risk_level": {"normal", "elevated", "high", "critical"},
    "provenance": {"observed", "adapted", "constructed"},
    "purpose": {"representative", "boundary", "risk"},
}


def read_csv(path: pathlib.Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


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
        if value:
            seen.add(value)
    return seen


def parse_target_cases(value: str, row_number: int, errors: list[str]) -> int | None:
    try:
        parsed = int(value)
    except ValueError:
        errors.append(
            f"distribution row {row_number}: target_cases must be a non-negative integer"
        )
        return None
    if parsed < 0:
        errors.append(
            f"distribution row {row_number}: target_cases must be a non-negative integer"
        )
        return None
    return parsed


def validate(
    distribution_path: pathlib.Path,
    examples_path: pathlib.Path,
) -> list[str]:
    errors: list[str] = []
    distribution_headers, distribution_rows = read_csv(distribution_path)
    example_headers, example_rows = read_csv(examples_path)

    missing_distribution = DISTRIBUTION_COLUMNS - set(distribution_headers)
    missing_examples = EXAMPLE_COLUMNS - set(example_headers)
    if missing_distribution:
        errors.append(
            "distribution: missing columns " + ", ".join(sorted(missing_distribution))
        )
    if missing_examples:
        errors.append("examples: missing columns " + ", ".join(sorted(missing_examples)))
    if errors:
        return errors

    if not distribution_rows:
        errors.append("distribution: must contain at least one query type")
    if not example_rows:
        errors.append("examples: must contain at least one example")

    query_type_ids = validate_unique(
        distribution_rows, "query_type_id", "distribution", errors
    )
    validate_unique(example_rows, "example_id", "examples", errors)

    targets: dict[str, int] = {}
    total_target_cases = 0
    for row_number, row in enumerate(distribution_rows, start=2):
        query_type_id = row.get("query_type_id", "").strip()
        for field in ("customer_task", "demand_band", "risk_level", "target_cases"):
            if not row.get(field, "").strip():
                errors.append(f"distribution row {row_number}: missing {field}")
        validate_enum(row, "demand_band", row_number, "distribution", errors)
        validate_enum(row, "risk_level", row_number, "distribution", errors)
        target_raw = row.get("target_cases", "").strip()
        if target_raw:
            target_cases = parse_target_cases(target_raw, row_number, errors)
            if target_cases is not None:
                targets[query_type_id] = target_cases
                total_target_cases += target_cases

    if distribution_rows and total_target_cases == 0:
        errors.append("distribution: target_cases total must be greater than zero")

    linked_types: set[str] = set()
    representative_types: set[str] = set()
    seen_inputs: set[tuple[str, str]] = set()
    for row_number, row in enumerate(example_rows, start=2):
        parent = row.get("query_type_id", "").strip()
        customer_input = row.get("input", "").strip()
        for field in ("query_type_id", "input", "provenance", "purpose"):
            if not row.get(field, "").strip():
                errors.append(f"examples row {row_number}: missing {field}")
        validate_enum(row, "provenance", row_number, "examples", errors)
        validate_enum(row, "purpose", row_number, "examples", errors)

        if parent and parent not in query_type_ids:
            errors.append(
                f"examples row {row_number}: unknown query_type_id={parent!r}"
            )
        elif customer_input:
            linked_types.add(parent)
            if row.get("purpose", "").strip() == "representative":
                representative_types.add(parent)

        duplicate_key = (parent, customer_input)
        if customer_input and duplicate_key in seen_inputs:
            errors.append(
                f"examples row {row_number}: duplicate input for query_type_id={parent!r}"
            )
        if customer_input:
            seen_inputs.add(duplicate_key)

    for query_type_id in sorted(query_type_ids):
        if query_type_id not in linked_types:
            errors.append(
                f"examples: query_type_id={query_type_id!r} has no linked example"
            )
        if targets.get(query_type_id, 0) > 0 and query_type_id not in representative_types:
            errors.append(
                f"examples: query_type_id={query_type_id!r} needs a representative example"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("distribution_csv", type=pathlib.Path)
    parser.add_argument("examples_csv", type=pathlib.Path)
    args = parser.parse_args()

    errors = validate(args.distribution_csv, args.examples_csv)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Validation failed with {len(errors)} issue(s).")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
