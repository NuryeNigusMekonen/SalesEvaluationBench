#!/usr/bin/env python3
"""Validate the Tenacious-Bench v0.2 task split package."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_ROOT = REPO_ROOT / "tenacious_bench_v0.2"
SOURCE_SEED = REPO_ROOT / "training" / "data" / "tenacious_bench_v0_2_expansion_100.jsonl"
V01_HELD_OUT = REPO_ROOT / "tenacious_bench_v0.1" / "held_out" / "tasks.jsonl"

SPLIT_FILES = {
    "train": BENCH_ROOT / "train" / "tasks.jsonl",
    "dev": BENCH_ROOT / "dev" / "tasks.jsonl",
    "held_out": BENCH_ROOT / "held_out" / "tasks.jsonl",
}
EXPECTED_COUNTS = {"train": 70, "dev": 15, "held_out": 15}
EXPECTED_TOTAL = 100
EXPECTED_SOURCE = "training/data/tenacious_bench_v0_2_expansion_100.jsonl"
REQUIRED_TOP = {"task_id", "task_version", "split", "source_type", "task_type", "risk_focus"}
REQUIRED_METADATA = {
    "scenario_id",
    "source_file_or_artifact",
    "reviewer_verdict",
    "semantic_family",
}
REQUIRED_INPUT = {
    "prospect_context",
    "hiring_signal_brief",
    "competitor_gap_brief",
    "agent_output",
    "judge_instruction",
}
REQUIRED_GROUND_TRUTH = {"expected_verdict", "expected_reason", "rubric", "chosen", "rejected"}


def parse_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, [f"file not found: {path}"]
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                errors.append(f"{path}:{lineno}: blank line")
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{lineno}: invalid JSON: {exc}")
                continue
            if not isinstance(row, dict):
                errors.append(f"{path}:{lineno}: row is not a JSON object")
                continue
            rows.append(row)
    return rows, errors


def load_v01_held_out_task_ids() -> set[str]:
    if not V01_HELD_OUT.exists():
        return set()
    rows, _ = parse_jsonl(V01_HELD_OUT)
    return {str(row.get("task_id", "")) for row in rows if row.get("task_id")}


def validate_row(row: dict[str, Any], split: str, lineno: int) -> list[str]:
    errors: list[str] = []
    task_id = row.get("task_id", f"{split}:line_{lineno}")

    missing_top = sorted(REQUIRED_TOP - set(row))
    if missing_top:
        errors.append(f"{task_id}: missing top-level fields: {', '.join(missing_top)}")

    if row.get("task_version") != "v0.2":
        errors.append(f"{task_id}: task_version must be v0.2")
    if row.get("split") != split:
        errors.append(f"{task_id}: split field is {row.get('split')!r}; expected {split!r}")

    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{task_id}: metadata must be a dict")
        metadata = {}
    else:
        missing_meta = sorted(REQUIRED_METADATA - set(metadata))
        if missing_meta:
            errors.append(f"{task_id}: missing metadata fields: {', '.join(missing_meta)}")
        if metadata.get("reviewer_verdict") != "approve":
            errors.append(f"{task_id}: reviewer_verdict must be approve")

    task_input = row.get("input")
    if not isinstance(task_input, dict):
        errors.append(f"{task_id}: input must be a dict")
        task_input = {}
    else:
        missing_input = sorted(REQUIRED_INPUT - set(task_input))
        if missing_input:
            errors.append(f"{task_id}: missing input fields: {', '.join(missing_input)}")

    ground_truth = row.get("ground_truth")
    if not isinstance(ground_truth, dict):
        errors.append(f"{task_id}: ground_truth must be a dict")
        ground_truth = {}
    else:
        missing_gt = sorted(REQUIRED_GROUND_TRUTH - set(ground_truth))
        if missing_gt:
            errors.append(f"{task_id}: missing ground_truth fields: {', '.join(missing_gt)}")
        chosen = ground_truth.get("chosen", "")
        rejected = ground_truth.get("rejected", "")
        if chosen and rejected and chosen.strip() == rejected.strip():
            errors.append(f"{task_id}: chosen and rejected are identical")

    scenario_id = metadata.get("scenario_id")
    context_scenario_id = task_input.get("prospect_context", {}).get("scenario_id")
    if scenario_id and context_scenario_id and scenario_id != context_scenario_id:
        errors.append(
            f"{task_id}: metadata scenario_id {scenario_id!r} does not match prospect_context"
        )

    return errors


def summarize(rows_by_split: dict[str, list[dict[str, Any]]]) -> None:
    print("\nDistribution Summary")
    print("-" * 40)
    for split, rows in rows_by_split.items():
        print(f"\n[{split}] {len(rows)} rows")
        risk_counts = Counter(row.get("risk_focus", "") for row in rows)
        verdict_counts = Counter(
            row.get("ground_truth", {}).get("expected_verdict", "") for row in rows
        )
        family_counts = Counter(
            row.get("metadata", {}).get("semantic_family", "") for row in rows
        )
        print("  risk_focus:")
        for key, value in sorted(risk_counts.items()):
            print(f"    {key}: {value}")
        print("  expected_verdict:")
        for key, value in sorted(verdict_counts.items()):
            print(f"    {key}: {value}")
        print(f"  semantic_families: {len(family_counts)}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    print("=" * 60)
    print("Tenacious-Bench v0.2 Split Validator")
    print("=" * 60)

    if not SOURCE_SEED.exists():
        errors.append(f"source seed not found: {SOURCE_SEED}")

    summary_path = BENCH_ROOT / "summary.json"
    if summary_path.exists():
        with summary_path.open(encoding="utf-8") as fh:
            summary = json.load(fh)
        if summary.get("source_seed_file") != EXPECTED_SOURCE:
            errors.append(
                "summary source_seed_file mismatch: "
                f"{summary.get('source_seed_file')!r}"
            )
        if summary.get("total_tasks") != EXPECTED_TOTAL:
            errors.append(
                f"summary total_tasks = {summary.get('total_tasks')}; "
                f"expected {EXPECTED_TOTAL}"
            )
    else:
        errors.append(f"summary.json not found: {summary_path}")

    rows_by_split: dict[str, list[dict[str, Any]]] = {}
    all_task_ids: list[str] = []
    task_split: dict[str, str] = {}
    scenario_split: dict[str, str] = {}
    family_split: dict[str, str] = {}
    pair_seen: dict[tuple[str, str], str] = {}
    v01_held_out_ids = load_v01_held_out_task_ids()

    for split, path in SPLIT_FILES.items():
        rows, parse_errors = parse_jsonl(path)
        errors.extend(parse_errors)
        rows_by_split[split] = rows

        expected_count = EXPECTED_COUNTS[split]
        if len(rows) == expected_count:
            print(f"[OK] {split}: {len(rows)} rows")
        else:
            errors.append(f"{split}: expected {expected_count} rows, found {len(rows)}")

        for lineno, row in enumerate(rows, 1):
            errors.extend(validate_row(row, split, lineno))

            task_id = str(row.get("task_id", ""))
            scenario_id = str(row.get("metadata", {}).get("scenario_id", ""))
            semantic_family = str(row.get("metadata", {}).get("semantic_family", ""))
            ground_truth = row.get("ground_truth", {})
            chosen = str(ground_truth.get("chosen", ""))
            rejected = str(ground_truth.get("rejected", ""))

            if task_id:
                all_task_ids.append(task_id)
                if task_id in v01_held_out_ids:
                    errors.append(f"{task_id}: task_id appears in v0.1 held_out")
                previous = task_split.setdefault(task_id, split)
                if previous != split:
                    errors.append(f"task_id leakage: {task_id} in {previous} and {split}")

            if scenario_id:
                previous = scenario_split.setdefault(scenario_id, split)
                if previous != split:
                    errors.append(
                        f"scenario_id leakage: {scenario_id} in {previous} and {split}"
                    )

            if semantic_family:
                previous = family_split.setdefault(semantic_family, split)
                if previous != split:
                    errors.append(
                        "semantic family leakage: "
                        f"{semantic_family} in {previous} and {split}"
                    )

            pair_key = (chosen.strip(), rejected.strip())
            if all(pair_key):
                previous = pair_seen.setdefault(pair_key, task_id)
                if previous != task_id:
                    errors.append(
                        f"duplicate chosen/rejected pair: {task_id} duplicates {previous}"
                    )

    total = sum(len(rows) for rows in rows_by_split.values())
    if total == EXPECTED_TOTAL:
        print(f"[OK] total rows: {total}")
    else:
        errors.append(f"total rows = {total}; expected {EXPECTED_TOTAL}")

    duplicate_task_ids = [tid for tid, count in Counter(all_task_ids).items() if count > 1]
    if duplicate_task_ids:
        errors.append(f"duplicate task_ids: {', '.join(sorted(duplicate_task_ids))}")
    else:
        print(f"[OK] no task_id leakage across splits")

    if not any("scenario_id leakage" in error for error in errors):
        print("[OK] no scenario_id leakage across splits")
    if not any("semantic family leakage" in error for error in errors):
        print("[OK] no semantic family leakage across splits")
    if not any("reviewer_verdict" in error for error in errors):
        print("[OK] all rows approved")
    if not any("duplicate chosen/rejected pair" in error for error in errors):
        print("[OK] no duplicate chosen/rejected pairs")

    summarize(rows_by_split)

    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  [WARN] {warning}")

    if errors:
        print(f"\nFAIL - {len(errors)} error(s):")
        for error in errors:
            print(f"  [ERR] {error}")
        return 1

    print("\nPASS - v0.2 task split is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
