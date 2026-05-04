#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE_FILE = PROJECT_ROOT / "held_out_traces.jsonl"
ALLOWED_CONDITIONS = {
    "day1_baseline",
    "automated_optimization_budget_match",
    "full_method",
}


def parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "pass", "passed"}:
        return True
    if lowered in {"0", "false", "no", "n", "fail", "failed"}:
        return False
    raise argparse.ArgumentTypeError(
        f"invalid boolean value '{value}'; use true/false or passed/failed"
    )


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno} invalid JSON: {exc.msg}") from exc
    return rows


def build_row(args: argparse.Namespace) -> dict:
    total_tokens = args.total_tokens
    if total_tokens is None:
        total_tokens = args.prompt_tokens + args.completion_tokens

    row = {
        "trace_id": args.trace_id,
        "condition": args.condition,
        "task_id": args.task_id,
        "passed": args.passed,
        "latency_ms": round(args.latency_ms, 3),
        "cost_usd": round(args.cost_usd, 6),
        "failure_mode": args.failure_mode,
        "prompt_tokens": args.prompt_tokens,
        "completion_tokens": args.completion_tokens,
        "total_tokens": total_tokens,
        "llm_calls": args.llm_calls,
    }
    if args.prompt_text:
        row["prompt_text"] = args.prompt_text
    if args.completion_text:
        row["completion_text"] = args.completion_text
    if args.model_output:
        row["model_output"] = args.model_output
    if args.prompt_cost_per_1k is not None:
        row["prompt_cost_per_1k"] = args.prompt_cost_per_1k
    if args.completion_cost_per_1k is not None:
        row["completion_cost_per_1k"] = args.completion_cost_per_1k
    if args.metadata:
        row["metadata"] = json.loads(args.metadata)
    return row


def upsert_row(rows: list[dict], new_row: dict, *, replace: bool) -> list[dict]:
    target_key = (new_row["condition"], new_row["task_id"])
    updated: list[dict] = []
    seen = False
    for row in rows:
        row_key = (row.get("condition"), row.get("task_id"))
        if row_key == target_key:
            if not replace:
                raise ValueError(
                    "row already exists for condition="
                    f"{new_row['condition']} task_id={new_row['task_id']}; use --replace"
                )
            if not seen:
                updated.append(new_row)
                seen = True
            continue
        updated.append(row)
    if not seen:
        updated.append(new_row)
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append or replace one held-out trace row for the ablation harness."
    )
    parser.add_argument("--file", default=str(DEFAULT_TRACE_FILE), help="Trace JSONL file path.")
    parser.add_argument("--trace-id", required=True, help="Unique trace row identifier.")
    parser.add_argument("--condition", choices=sorted(ALLOWED_CONDITIONS), required=True)
    parser.add_argument("--task-id", required=True, help="Shared task id used for paired comparisons.")
    parser.add_argument("--passed", type=parse_bool, required=True, help="Whether this condition passed the task.")
    parser.add_argument("--latency-ms", type=float, required=True)
    parser.add_argument("--cost-usd", type=float, required=True)
    parser.add_argument("--failure-mode", default=None)
    parser.add_argument("--prompt-tokens", type=int, default=0)
    parser.add_argument("--completion-tokens", type=int, default=0)
    parser.add_argument("--total-tokens", type=int, default=None)
    parser.add_argument("--llm-calls", type=int, default=1)
    parser.add_argument("--prompt-text", default=None)
    parser.add_argument("--completion-text", default=None)
    parser.add_argument("--model-output", default=None)
    parser.add_argument("--prompt-cost-per-1k", type=float, default=None)
    parser.add_argument("--completion-cost-per-1k", type=float, default=None)
    parser.add_argument(
        "--metadata",
        default=None,
        help="Optional JSON object string stored under metadata.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace an existing row with the same (condition, task_id).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.file)
    path.parent.mkdir(parents=True, exist_ok=True)

    if args.prompt_tokens < 0 or args.completion_tokens < 0 or args.llm_calls < 1:
        raise SystemExit("prompt/completion tokens must be >= 0 and llm_calls must be >= 1")
    if args.total_tokens is not None and args.total_tokens < 0:
        raise SystemExit("total_tokens must be >= 0")
    if args.metadata is not None:
        try:
            parsed_metadata = json.loads(args.metadata)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"metadata must be valid JSON: {exc.msg}") from exc
        if not isinstance(parsed_metadata, dict):
            raise SystemExit("metadata must decode to a JSON object")

    rows = load_rows(path)
    row = build_row(args)
    updated_rows = upsert_row(rows, row, replace=args.replace)

    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=True) for item in updated_rows) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "file": str(path),
                "condition": row["condition"],
                "task_id": row["task_id"],
                "replace": args.replace,
                "row_count": len(updated_rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())