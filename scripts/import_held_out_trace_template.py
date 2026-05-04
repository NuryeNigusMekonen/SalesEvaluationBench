#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from add_held_out_trace import DEFAULT_TRACE_FILE, load_rows, parse_bool, upsert_row


REQUIRED_TEMPLATE_COLUMNS = {
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
}
REQUIRED_MEASUREMENT_COLUMNS = {
    "task_id",
    "condition",
    "trace_id",
    "passed",
    "latency_ms",
    "cost_usd",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import completed rows from a held-out trace template CSV into held_out_traces.jsonl."
    )
    parser.add_argument("--csv", required=True, help="Completed trace template CSV path.")
    parser.add_argument("--file", default=str(DEFAULT_TRACE_FILE), help="Target trace JSONL file.")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing rows with the same (condition, task_id).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on incomplete rows instead of skipping them.",
    )
    return parser.parse_args()


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _optional_int(raw: str, field_name: str, *, line_no: int) -> int | None:
    value = _clean(raw)
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"line {line_no}: {field_name} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"line {line_no}: {field_name} must be >= 0")
    return parsed


def _required_float(raw: str, field_name: str, *, line_no: int) -> float:
    value = _clean(raw)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"line {line_no}: {field_name} must be numeric") from exc


def _optional_text(raw: str) -> str | None:
    value = _clean(raw)
    return value or None


def _is_incomplete(row: dict[str, str]) -> bool:
    return any(not _clean(row.get(column)) for column in REQUIRED_MEASUREMENT_COLUMNS)


def _build_trace_row(csv_row: dict[str, str], *, line_no: int) -> dict:
    prompt_tokens = _optional_int(csv_row.get("prompt_tokens", ""), "prompt_tokens", line_no=line_no) or 0
    completion_tokens = _optional_int(
        csv_row.get("completion_tokens", ""),
        "completion_tokens",
        line_no=line_no,
    ) or 0
    total_tokens = _optional_int(csv_row.get("total_tokens", ""), "total_tokens", line_no=line_no)
    llm_calls = _optional_int(csv_row.get("llm_calls", ""), "llm_calls", line_no=line_no) or 1
    if llm_calls < 1:
        raise ValueError(f"line {line_no}: llm_calls must be >= 1")

    trace_row = {
        "trace_id": _clean(csv_row["trace_id"]),
        "condition": _clean(csv_row["condition"]),
        "task_id": _clean(csv_row["task_id"]),
        "passed": parse_bool(_clean(csv_row["passed"])),
        "latency_ms": round(_required_float(csv_row["latency_ms"], "latency_ms", line_no=line_no), 3),
        "cost_usd": round(_required_float(csv_row["cost_usd"], "cost_usd", line_no=line_no), 6),
        "failure_mode": _optional_text(csv_row.get("failure_mode")),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens if total_tokens is not None else prompt_tokens + completion_tokens,
        "llm_calls": llm_calls,
        "metadata": {
            "scenario_id": _clean(csv_row.get("scenario_id")),
            "risk_focus": _clean(csv_row.get("risk_focus")),
            "task_type": _clean(csv_row.get("task_type")),
            "company_name": _clean(csv_row.get("company_name")),
        },
    }
    return trace_row


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv)
    trace_path = Path(args.file)

    if not csv_path.exists():
        raise SystemExit(f"csv file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit("csv file has no header row")
        missing_columns = sorted(REQUIRED_TEMPLATE_COLUMNS - set(reader.fieldnames))
        if missing_columns:
            raise SystemExit(
                "csv file is missing required columns: " + ", ".join(missing_columns)
            )

        existing_rows = load_rows(trace_path)
        imported = 0
        skipped = 0
        for index, csv_row in enumerate(reader, 2):
            if _is_incomplete(csv_row):
                if args.strict:
                    raise SystemExit(
                        f"line {index}: incomplete measurement row; fill required columns or omit --strict"
                    )
                skipped += 1
                continue
            try:
                trace_row = _build_trace_row(csv_row, line_no=index)
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
            existing_rows = upsert_row(existing_rows, trace_row, replace=args.replace)
            imported += 1

    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=True) for item in existing_rows) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ok",
                "csv": str(csv_path),
                "file": str(trace_path),
                "imported_rows": imported,
                "skipped_rows": skipped,
                "replace": args.replace,
                "row_count": len(existing_rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())