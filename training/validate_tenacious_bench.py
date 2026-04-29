#!/usr/bin/env python3
"""Validate the Week 11 Tenacious-Bench seed dataset."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "task_id",
    "task_version",
    "source_type",
    "source_file_or_artifact",
    "split",
    "task_type",
    "risk_focus",
    "prospect_context",
    "hiring_signal_brief",
    "competitor_gap_brief",
    "agent_output",
    "judge_instruction",
    "expected_verdict",
    "expected_reason",
    "rubric",
    "chosen",
    "rejected",
    "label_confidence",
    "requires_manual_review",
}

ALLOWED_VERDICTS = {"pass", "fail", "needs_human_review"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
PAPER_SOURCE_MARKERS = (
    ".pdf",
    "docs/commen-papers/",
    "docs/optionB-papers/",
)


def parse_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    if not path.exists():
        return rows, [f"dataset file does not exist: {path}"]

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                errors.append(f"line {line_number}: blank lines are not allowed")
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_number}: invalid JSON: {exc}")
                continue
            if not isinstance(row, dict):
                errors.append(f"line {line_number}: row must be a JSON object")
                continue
            row["_line_number"] = line_number
            rows.append(row)

    return rows, errors


def parse_expected_distribution(raw: str | None) -> dict[str, int] | None:
    if not raw:
        return None
    parsed: dict[str, int] = {}
    for item in raw.split(","):
        if not item.strip():
            continue
        if "=" not in item:
            raise ValueError(
                "expected risk distribution entries must use key=value format"
            )
        key, value = item.split("=", 1)
        parsed[key.strip()] = int(value.strip())
    return parsed


def validate_rows(
    rows: list[dict[str, Any]],
    expected_count: int | None = None,
    expected_risk_distribution: dict[str, int] | None = None,
) -> tuple[list[str], dict[str, Counter[str]]]:
    errors: list[str] = []
    task_ids: list[str] = []

    for row in rows:
        line = row["_line_number"]
        task_id = row.get("task_id", f"line_{line}")

        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            errors.append(f"{task_id}: missing required fields: {', '.join(missing)}")

        task_ids.append(str(row.get("task_id", "")))

        for field in ("chosen", "rejected", "source_file_or_artifact"):
            if not isinstance(row.get(field), str) or not row.get(field, "").strip():
                errors.append(f"{task_id}: {field} must be a non-empty string")

        if row.get("expected_verdict") not in ALLOWED_VERDICTS:
            errors.append(
                f"{task_id}: expected_verdict must be one of {sorted(ALLOWED_VERDICTS)}"
            )

        if row.get("label_confidence") not in ALLOWED_CONFIDENCE:
            errors.append(
                f"{task_id}: label_confidence must be one of {sorted(ALLOWED_CONFIDENCE)}"
            )

        if row.get("split") == "seed" and row.get("requires_manual_review") is not True:
            errors.append(f"{task_id}: seed rows must have requires_manual_review=true")

        if not isinstance(row.get("scenario_id"), str) or not row.get("scenario_id", "").strip():
            errors.append(f"{task_id}: scenario_id must be present and non-empty")

        if (
            not isinstance(row.get("split_contamination_notes"), str)
            or not row.get("split_contamination_notes", "").strip()
        ):
            errors.append(f"{task_id}: split_contamination_notes must be present and non-empty")

        source = str(row.get("source_file_or_artifact", "")).lower()
        if any(marker.lower() in source for marker in PAPER_SOURCE_MARKERS):
            errors.append(f"{task_id}: paper PDF or paper folder appears in source_file_or_artifact")

        provenance = row.get("source_provenance")
        if isinstance(provenance, dict) and provenance.get("paper_content_used") is not False:
            errors.append(f"{task_id}: source_provenance.paper_content_used must be false")

    if expected_count is not None and len(rows) != expected_count:
        errors.append(
            f"dataset must contain exactly {expected_count} rows; found {len(rows)}"
        )

    duplicate_ids = sorted(task_id for task_id, count in Counter(task_ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"task_id values must be unique; duplicates: {', '.join(duplicate_ids)}")

    counts = {
        "source_type": Counter(str(row.get("source_type", "")) for row in rows),
        "task_type": Counter(str(row.get("task_type", "")) for row in rows),
        "risk_focus": Counter(str(row.get("risk_focus", "")) for row in rows),
        "expected_verdict": Counter(str(row.get("expected_verdict", "")) for row in rows),
    }

    if (
        expected_risk_distribution is not None
        and dict(counts["risk_focus"]) != expected_risk_distribution
    ):
        errors.append(
            "risk_focus distribution mismatch: "
            f"expected {expected_risk_distribution}, found {dict(counts['risk_focus'])}"
        )

    return errors, counts


def print_counts(counts: dict[str, Counter[str]]) -> None:
    for count_name in ("source_type", "task_type", "risk_focus", "expected_verdict"):
        print(f"{count_name}:")
        for key, value in sorted(counts[count_name].items()):
            print(f"  {key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        nargs="?",
        default="training/data/tenacious_bench_seed_20.jsonl",
        help="Path to the Tenacious-Bench JSONL dataset.",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=None,
        help="Optional exact row count to enforce.",
    )
    parser.add_argument(
        "--expected-risk-distribution",
        default=None,
        help=(
            "Optional comma-separated key=value counts to enforce, e.g. "
            "unsupported_pricing_or_scope_claim=5,overclaimed_signal_or_maturity_claim=5"
        ),
    )
    args = parser.parse_args()

    rows, parse_errors = parse_jsonl(Path(args.dataset))
    try:
        expected_risk_distribution = parse_expected_distribution(
            args.expected_risk_distribution
        )
    except ValueError as exc:
        print(f"FAIL\n- {exc}")
        return 2
    validation_errors, counts = validate_rows(
        rows,
        expected_count=args.expected_count,
        expected_risk_distribution=expected_risk_distribution,
    )
    errors = parse_errors + validation_errors

    print(f"Validated: {args.dataset}")
    print_counts(counts)

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
