#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_FILE = PROJECT_ROOT / "held_out_traces.jsonl"
ALLOWED_CONDITIONS = {
    "day1_baseline",
    "automated_optimization_budget_match",
    "full_method",
}
REQUIRED_FIELDS = {
    "trace_id",
    "condition",
    "task_id",
    "passed",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate held_out_traces.jsonl for ablation runs.")
    parser.add_argument("--file", default=str(DEFAULT_TRACE_FILE), help="Trace JSONL file path.")
    parser.add_argument(
        "--require-delta-a-pairs",
        action="store_true",
        help="Fail if any task_id is missing either day1_baseline or full_method.",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{lineno} invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{lineno} row must decode to an object")
        row["__line__"] = lineno
        rows.append(row)
    return rows


def validate_rows(rows: list[dict], *, require_delta_a_pairs: bool) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    seen_pairs: set[tuple[str, str]] = set()
    by_task: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        line = row["__line__"]
        missing = sorted(REQUIRED_FIELDS - row.keys())
        if missing:
            errors.append(f"line {line}: missing required fields: {', '.join(missing)}")
            continue

        condition = row.get("condition")
        task_id = row.get("task_id")
        if condition not in ALLOWED_CONDITIONS:
            errors.append(f"line {line}: unknown condition '{condition}'")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"line {line}: task_id must be a non-empty string")

        if not isinstance(row.get("passed"), bool):
            errors.append(f"line {line}: passed must be true/false")

        for numeric_key in (
            "latency_ms",
            "cost_usd",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "llm_calls",
        ):
            if numeric_key in row and not isinstance(row[numeric_key], (int, float)):
                errors.append(f"line {line}: {numeric_key} must be numeric when present")

        pair = (str(condition), str(task_id))
        if pair in seen_pairs:
            errors.append(
                f"line {line}: duplicate (condition, task_id) pair for {condition}/{task_id}"
            )
        seen_pairs.add(pair)
        by_task[str(task_id)].add(str(condition))

    if require_delta_a_pairs:
        for task_id, conditions in sorted(by_task.items()):
            missing = {"day1_baseline", "full_method"} - conditions
            if missing:
                errors.append(
                    f"task_id {task_id}: missing Delta A pair condition(s): {', '.join(sorted(missing))}"
                )

    summary = {
        "row_count": len(rows),
        "task_count": len(by_task),
        "conditions_present": {
            condition: sum(1 for row in rows if row.get("condition") == condition)
            for condition in sorted(ALLOWED_CONDITIONS)
        },
        "delta_a_complete_tasks": sum(
            1 for conditions in by_task.values() if {"day1_baseline", "full_method"} <= conditions
        ),
    }
    return errors, summary


def main() -> int:
    args = parse_args()
    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"trace file not found: {path}")

    rows = load_rows(path)
    errors, summary = validate_rows(rows, require_delta_a_pairs=args.require_delta_a_pairs)
    print(json.dumps({"summary": summary, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())