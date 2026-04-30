#!/usr/bin/env python3
"""Validate the Tenacious-Bench v0.1 split package before Colab training."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_ROOT = REPO_ROOT / "tenacious_bench_v0.1"
SUMMARY_FILE = BENCH_ROOT / "summary.json"
DEPRECATED_SEED = "training/data/tenacious_bench_seed_200.jsonl"
EXPECTED_SEED = "training/data/tenacious_bench_seed_200_v2.jsonl"

SPLIT_FILES = {
    "train": BENCH_ROOT / "train" / "tasks.jsonl",
    "dev": BENCH_ROOT / "dev" / "tasks.jsonl",
    "held_out": BENCH_ROOT / "held_out" / "tasks.jsonl",
}
EXPECTED_COUNTS = {"train": 100, "dev": 60, "held_out": 40}
EXPECTED_TOTAL = 200

REQUIRED_METADATA = {"scenario_id", "source_file_or_artifact"}
REQUIRED_TOP = {"task_id", "task_type", "risk_focus"}


def parse_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return rows, [f"file does not exist: {path}"]
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


def validate_row_schema(row: dict[str, Any], split: str, lineno: int) -> list[str]:
    errs: list[str] = []
    tid = row.get("task_id", f"{split}:line_{lineno}")

    # metadata block
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        errs.append(f"{tid}: 'metadata' must be a dict")
    else:
        for f in REQUIRED_METADATA:
            if not meta.get(f):
                errs.append(f"{tid}: metadata.{f} missing or empty")

    # input block
    inp = row.get("input")
    if not isinstance(inp, dict):
        errs.append(f"{tid}: 'input' must be a dict")

    # ground_truth block
    gt = row.get("ground_truth")
    if not isinstance(gt, dict):
        errs.append(f"{tid}: 'ground_truth' must be a dict")
    else:
        for f in ("expected_verdict", "rubric"):
            if not gt.get(f):
                errs.append(f"{tid}: ground_truth.{f} missing or empty")

        # chosen / rejected: may be at top level or in ground_truth
        chosen = row.get("chosen") or gt.get("chosen")
        rejected = row.get("rejected") or gt.get("rejected")
        if not chosen:
            errs.append(f"{tid}: chosen missing or empty (checked top-level and ground_truth)")
        if not rejected:
            errs.append(f"{tid}: rejected missing or empty (checked top-level and ground_truth)")

    # top-level required fields from the task schema
    for f in ("task_id", "task_type", "risk_focus"):
        if not row.get(f):
            errs.append(f"{tid}: top-level field '{f}' missing or empty")

    # scenario_id
    scenario_id = (meta or {}).get("scenario_id") if isinstance(meta, dict) else None
    if not scenario_id:
        errs.append(f"{tid}: scenario_id missing")

    return errs


def check_leakage(
    all_rows: dict[str, list[dict[str, Any]]],
) -> list[str]:
    """Check scenario_id and company_domain leakage across splits."""
    errs: list[str] = []

    split_scenario_ids: dict[str, set[str]] = {}
    split_domains: dict[str, set[str]] = {}
    split_outputs: dict[str, set[str]] = {}

    for split, rows in all_rows.items():
        sids: set[str] = set()
        domains: set[str] = set()
        outputs: set[str] = set()
        for row in rows:
            meta = row.get("metadata") or {}
            sid = meta.get("scenario_id", "")
            dom = meta.get("company_domain", "")
            inp = row.get("input") or {}
            out = inp.get("agent_output", "")
            if sid:
                sids.add(sid)
            if dom:
                domains.add(dom)
            if out:
                outputs.add(out)
        split_scenario_ids[split] = sids
        split_domains[split] = domains
        split_outputs[split] = outputs

    splits = list(all_rows.keys())
    for i, s1 in enumerate(splits):
        for s2 in splits[i + 1 :]:
            shared_sids = split_scenario_ids[s1] & split_scenario_ids[s2]
            if shared_sids:
                errs.append(
                    f"scenario_id leakage between {s1} and {s2}: "
                    + ", ".join(sorted(shared_sids))
                )
            shared_domains = split_domains[s1] & split_domains[s2]
            if shared_domains:
                errs.append(
                    f"company_domain leakage between {s1} and {s2}: "
                    + ", ".join(sorted(shared_domains))
                )
            shared_outputs = split_outputs[s1] & split_outputs[s2]
            if shared_outputs:
                sample = list(sorted(shared_outputs))[:3]
                errs.append(
                    f"exact agent_output duplicate across {s1} and {s2} "
                    f"({len(shared_outputs)} instances); sample: {sample}"
                )

    return errs


def validate_distribution_vs_summary(
    split: str,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> list[str]:
    errs: list[str] = []
    split_summary = summary.get("splits", {}).get(split, {})

    expected_rf = split_summary.get("risk_focus", {})
    expected_tt = split_summary.get("task_type", {})

    actual_rf = Counter(row.get("risk_focus", "") for row in rows)
    actual_tt = Counter(row.get("task_type", "") for row in rows)

    if dict(actual_rf) != expected_rf:
        errs.append(
            f"{split}: risk_focus mismatch — "
            f"expected {expected_rf}, got {dict(actual_rf)}"
        )
    if dict(actual_tt) != expected_tt:
        errs.append(
            f"{split}: task_type mismatch — "
            f"expected {expected_tt}, got {dict(actual_tt)}"
        )

    return errs


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    print("=" * 60)
    print("Tenacious-Bench v0.1 Package Validator")
    print("=" * 60)

    # 1. Check summary.json
    if not SUMMARY_FILE.exists():
        errors.append(f"summary.json not found: {SUMMARY_FILE}")
        summary = {}
    else:
        with SUMMARY_FILE.open(encoding="utf-8") as fh:
            summary = json.load(fh)
        print(f"[OK] summary.json loaded: {SUMMARY_FILE}")

        seed = summary.get("source_seed_file", "")
        if seed != EXPECTED_SEED:
            errors.append(
                f"summary.json source_seed_file is '{seed}'; "
                f"expected '{EXPECTED_SEED}'"
            )
        else:
            print(f"[OK] source_seed_file = {seed}")

        if DEPRECATED_SEED in seed:
            errors.append(
                f"summary.json references deprecated seed: {DEPRECATED_SEED}"
            )

        if summary.get("total_tasks") != EXPECTED_TOTAL:
            errors.append(
                f"summary.json total_tasks = {summary.get('total_tasks')}; "
                f"expected {EXPECTED_TOTAL}"
            )
        else:
            print(f"[OK] total_tasks = {EXPECTED_TOTAL}")

    # 2. Load all split files
    all_rows: dict[str, list[dict[str, Any]]] = {}
    all_task_ids: list[str] = []

    for split, path in SPLIT_FILES.items():
        if not path.exists():
            errors.append(f"[FAIL] {split} file missing: {path}")
            all_rows[split] = []
            continue

        rows, parse_errs = parse_jsonl(path)
        errors.extend(parse_errs)
        all_rows[split] = rows

        expected = EXPECTED_COUNTS[split]
        if len(rows) != expected:
            errors.append(
                f"{split}: expected {expected} rows, found {len(rows)}"
            )
        else:
            print(f"[OK] {split}: {len(rows)} rows")

        # schema validation per row
        for lineno, row in enumerate(rows, 1):
            errors.extend(validate_row_schema(row, split, lineno))

        # collect task_ids
        for row in rows:
            tid = row.get("task_id")
            if tid:
                all_task_ids.append(tid)

    # 3. Total count
    total = sum(len(r) for r in all_rows.values())
    if total != EXPECTED_TOTAL:
        errors.append(f"total rows across all splits = {total}; expected {EXPECTED_TOTAL}")
    else:
        print(f"[OK] total rows = {total}")

    # 4. Unique task_ids across all splits
    dup_ids = [tid for tid, cnt in Counter(all_task_ids).items() if cnt > 1]
    if dup_ids:
        errors.append(f"duplicate task_ids across splits: {', '.join(sorted(dup_ids))}")
    else:
        print(f"[OK] all {len(all_task_ids)} task_ids unique")

    # 5. Leakage checks
    leakage_errs = check_leakage(all_rows)
    if leakage_errs:
        # scenario_id leakage is a hard error; company_domain and output duplication
        # are warnings (the split is interim and company domains may overlap across
        # different scenarios legitimately).
        for e in leakage_errs:
            if "scenario_id leakage" in e:
                errors.append(e)
            else:
                warnings.append(e)
    else:
        print("[OK] no scenario_id or company_domain leakage across splits")

    # 6. Distribution vs summary.json
    if summary:
        for split, rows in all_rows.items():
            dist_errs = validate_distribution_vs_summary(split, rows, summary)
            errors.extend(dist_errs)
        if not any("mismatch" in e for e in errors):
            print("[OK] risk_focus and task_type distributions match summary.json")

    # 7. Deprecated seed reference guard
    deprecated_path = REPO_ROOT / "training" / "data" / "tenacious_bench_seed_200.jsonl"
    if deprecated_path.exists():
        warnings.append(
            f"deprecated seed file exists on disk: {deprecated_path}; "
            "do not reference it in any training pipeline"
        )

    # --- Report ---
    print()
    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  [WARN] {w}")
        print()

    if errors:
        print(f"FAIL — {len(errors)} error(s):")
        for e in errors:
            print(f"  [ERR] {e}")
        return 1

    print("PASS — benchmark package is valid and ready for Colab training.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
