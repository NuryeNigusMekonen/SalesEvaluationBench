#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASKS_FILE = PROJECT_ROOT / "tenacious_bench_v0.1" / "held_out" / "tasks.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "reports" / "held_out_trace_template.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a CSV template of held-out tasks for collecting real ablation traces."
    )
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS_FILE), help="Held-out task JSONL file.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="CSV output path.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of tasks to export.")
    parser.add_argument(
        "--conditions",
        default="day1_baseline,full_method",
        help="Comma-separated conditions to prepare measurement rows for.",
    )
    return parser.parse_args()


def load_tasks(path: Path, limit: int) -> list[dict]:
    tasks: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        row = json.loads(stripped)
        tasks.append(row)
        if len(tasks) >= limit:
            break
    return tasks


def main() -> int:
    args = parse_args()
    tasks_path = Path(args.tasks)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not tasks_path.exists():
        raise SystemExit(f"held-out tasks file not found: {tasks_path}")

    conditions = [item.strip() for item in args.conditions.split(",") if item.strip()]
    tasks = load_tasks(tasks_path, args.limit)

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "task_id",
                "scenario_id",
                "risk_focus",
                "task_type",
                "company_name",
                "condition",
                "trace_id",
                "passed",
                "latency_ms",
                "cost_usd",
                "failure_mode",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "llm_calls",
            ],
        )
        writer.writeheader()
        for task in tasks:
            metadata = task.get("metadata") or {}
            for condition in conditions:
                writer.writerow(
                    {
                        "task_id": task.get("task_id"),
                        "scenario_id": metadata.get("scenario_id"),
                        "risk_focus": task.get("risk_focus"),
                        "task_type": task.get("task_type"),
                        "company_name": metadata.get("company_name"),
                        "condition": condition,
                        "trace_id": "",
                        "passed": "",
                        "latency_ms": "",
                        "cost_usd": "",
                        "failure_mode": "",
                        "prompt_tokens": "",
                        "completion_tokens": "",
                        "total_tokens": "",
                        "llm_calls": "",
                    }
                )

    print(
        json.dumps(
            {
                "status": "ok",
                "tasks_file": str(tasks_path),
                "output": str(output_path),
                "task_count": len(tasks),
                "condition_count": len(conditions),
                "row_count": len(tasks) * len(conditions),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())