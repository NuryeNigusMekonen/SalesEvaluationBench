#!/usr/bin/env python3
"""Validate Tenacious-Bench v0.2 preference split files."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
PREF_DIR = REPO_ROOT / "training" / "data"
TASK_ROOT = REPO_ROOT / "tenacious_bench_v0.2"

PREF_FILES = {
    "train": PREF_DIR / "v02_train_preferences.jsonl",
    "dev": PREF_DIR / "v02_dev_preferences.jsonl",
    "test": PREF_DIR / "v02_test_preferences.jsonl",
}
TASK_FILES = {
    "train": TASK_ROOT / "train" / "tasks.jsonl",
    "dev": TASK_ROOT / "dev" / "tasks.jsonl",
    "test": TASK_ROOT / "held_out" / "tasks.jsonl",
}
EXPECTED_COUNTS = {"train": 70, "dev": 15, "test": 15}
REQUIRED_FIELDS = {
    "task_id",
    "split",
    "risk_focus",
    "task_type",
    "expected_verdict",
    "prompt",
    "chosen",
    "rejected",
    "source_file_or_artifact",
    "scenario_id",
    "semantic_family",
}


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


def task_count(path: Path) -> int:
    rows, _ = parse_jsonl(path)
    return len(rows)


def validate_row(row: dict[str, Any], expected_split: str) -> list[str]:
    errors: list[str] = []
    task_id = row.get("task_id", "<missing task_id>")
    missing = sorted(REQUIRED_FIELDS - set(row))
    if missing:
        errors.append(f"{task_id}: missing fields: {', '.join(missing)}")
    if row.get("split") != expected_split:
        errors.append(
            f"{task_id}: split is {row.get('split')!r}; expected {expected_split!r}"
        )
    prompt = str(row.get("prompt", ""))
    chosen = str(row.get("chosen", ""))
    rejected = str(row.get("rejected", ""))
    if not prompt:
        errors.append(f"{task_id}: prompt is empty")
    if not chosen:
        errors.append(f"{task_id}: chosen is empty")
    if not rejected:
        errors.append(f"{task_id}: rejected is empty")
    if chosen and rejected and chosen.strip() == rejected.strip():
        errors.append(f"{task_id}: chosen and rejected are identical")
    if chosen and chosen in prompt:
        errors.append(f"{task_id}: prompt contains chosen text verbatim")
    if rejected and rejected in prompt:
        errors.append(f"{task_id}: prompt contains rejected text verbatim")
    return errors


def main() -> int:
    errors: list[str] = []
    rows_by_split: dict[str, list[dict[str, Any]]] = {}
    pair_seen: dict[tuple[str, str], str] = {}
    task_ids_by_split: dict[str, set[str]] = {}
    scenario_ids_by_split: dict[str, set[str]] = {}
    family_by_split: dict[str, set[str]] = {}

    print("=" * 60)
    print("Tenacious-Bench v0.2 Preference Validator")
    print("=" * 60)

    for split, path in PREF_FILES.items():
        rows, parse_errors = parse_jsonl(path)
        rows_by_split[split] = rows
        errors.extend(parse_errors)

        expected = EXPECTED_COUNTS[split]
        if len(rows) == expected:
            print(f"[OK] {split}: {len(rows)} preference rows")
        else:
            errors.append(f"{split}: expected {expected} rows, found {len(rows)}")

        tasks = task_count(TASK_FILES[split])
        if len(rows) != tasks:
            errors.append(
                f"{split}: preference count {len(rows)} does not match task count {tasks}"
            )

        task_ids_by_split[split] = set()
        scenario_ids_by_split[split] = set()
        family_by_split[split] = set()
        for row in rows:
            errors.extend(validate_row(row, split))
            task_id = str(row.get("task_id", ""))
            scenario_id = str(row.get("scenario_id", ""))
            semantic_family = str(row.get("semantic_family", ""))
            if task_id:
                task_ids_by_split[split].add(task_id)
            if scenario_id:
                scenario_ids_by_split[split].add(scenario_id)
            if semantic_family:
                family_by_split[split].add(semantic_family)
            pair = (str(row.get("chosen", "")).strip(), str(row.get("rejected", "")).strip())
            if all(pair):
                previous = pair_seen.setdefault(pair, task_id)
                if previous != task_id:
                    errors.append(
                        f"duplicate chosen/rejected pair: {task_id} duplicates {previous}"
                    )

        duplicates = [
            task_id
            for task_id, count in Counter(row.get("task_id", "") for row in rows).items()
            if task_id and count > 1
        ]
        if duplicates:
            errors.append(f"{split}: duplicate task_ids: {', '.join(sorted(duplicates))}")

    splits = list(PREF_FILES)
    for i, left in enumerate(splits):
        for right in splits[i + 1 :]:
            shared_tasks = task_ids_by_split[left] & task_ids_by_split[right]
            if shared_tasks:
                errors.append(
                    f"task_id leakage between {left} and {right}: "
                    + ", ".join(sorted(shared_tasks))
                )
            shared_scenarios = scenario_ids_by_split[left] & scenario_ids_by_split[right]
            if shared_scenarios:
                errors.append(
                    f"scenario_id leakage between {left} and {right}: "
                    + ", ".join(sorted(shared_scenarios))
                )
            shared_families = family_by_split[left] & family_by_split[right]
            if shared_families:
                errors.append(
                    f"semantic family leakage between {left} and {right}: "
                    + ", ".join(sorted(shared_families))
                )

    print("\nDistribution Summary")
    print("-" * 40)
    for split, rows in rows_by_split.items():
        print(f"\n[{split}] {len(rows)} rows")
        for label, field in (
            ("risk_focus", "risk_focus"),
            ("expected_verdict", "expected_verdict"),
        ):
            print(f"  {label}:")
            for key, value in sorted(Counter(row.get(field, "") for row in rows).items()):
                print(f"    {key}: {value}")

    if errors:
        print(f"\nFAIL - {len(errors)} error(s):")
        for error in errors:
            print(f"  [ERR] {error}")
        return 1

    print("\nPASS - v0.2 preference files are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
