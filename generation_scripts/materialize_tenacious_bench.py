#!/usr/bin/env python3
"""Materialize the Week 11 interim Tenacious-Bench dataset from the v2 seed file."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "training" / "data" / "tenacious_bench_seed_200_v2.jsonl"
OUTPUT_DIR = ROOT / "tenacious_bench_v0.1"
SPLITS = ("train", "dev", "held_out")
RISK_FOCI = (
    "unsupported_pricing_or_scope_claim",
    "overclaimed_signal_or_maturity_claim",
    "generic_outreach_ungrounded",
    "wrong_crm_hubspot_calendar_next_action",
    "reply_escalation_or_objection_failure",
)
SOURCE_MODE_MAP = {
    "trace": "trace_derived",
    "template": "programmatic",
    "manual_adversarial": "hand_authored_adversarial",
    "transcript": "hand_authored_adversarial",
}
TARGET_SPLIT_COUNTS_PER_RISK = {"train": 20, "dev": 12, "held_out": 8}
INTER_RATER_PER_RISK = 6


def load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def infer_difficulty(row: dict) -> str:
    if row["source_type"] == "manual_adversarial" or row["expected_verdict"] == "needs_human_review":
        return "T3_hard"
    if row["source_type"] in {"trace", "transcript"}:
        return "T2_medium"
    return "T1_easy"


def transform_row(row: dict, split: str) -> dict:
    company = row["prospect_context"]["company_name"]
    return {
        "task_id": row["task_id"],
        "task_version": row["task_version"],
        "split": split,
        "source_mode": SOURCE_MODE_MAP[row["source_type"]],
        "source_type": row["source_type"],
        "difficulty": infer_difficulty(row),
        "task_type": row["task_type"],
        "risk_focus": row["risk_focus"],
        "metadata": {
            "scenario_id": row["scenario_id"],
            "prospect_id": row["prospect_context"]["prospect_id"],
            "company_name": company,
            "company_domain": row["prospect_context"]["company_domain"],
            "source_file_or_artifact": row["source_file_or_artifact"],
            "label_confidence": row["label_confidence"],
            "requires_manual_review": row["requires_manual_review"],
            "source_provenance": row["source_provenance"],
            "split_contamination_notes": row["split_contamination_notes"],
        },
        "input": {
            "prospect_context": row["prospect_context"],
            "hiring_signal_brief": row["hiring_signal_brief"],
            "competitor_gap_brief": row["competitor_gap_brief"],
            "agent_output": row["agent_output"],
            "judge_instruction": row["judge_instruction"],
        },
        "ground_truth": {
            "expected_verdict": row["expected_verdict"],
            "expected_reason": row["expected_reason"],
            "rubric": row["rubric"],
            "chosen": row["chosen"],
            "rejected": row["rejected"],
        },
    }


def assign_splits(rows: list[dict]) -> dict[str, list[dict]]:
    split_rows = {split: [] for split in SPLITS}
    by_risk: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_risk[row["risk_focus"]].append(row)

    for risk_focus in RISK_FOCI:
        ordered = sorted(
            by_risk[risk_focus],
            key=lambda row: (
                stable_hash(row["scenario_id"]),
                row["task_id"],
            ),
        )
        cursor = 0
        for split in SPLITS:
            count = TARGET_SPLIT_COUNTS_PER_RISK[split]
            chunk = ordered[cursor : cursor + count]
            cursor += count
            for row in chunk:
                split_rows[split].append(transform_row(row, split))
    return split_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8")


def build_summary(split_rows: dict[str, list[dict]]) -> dict:
    summary: dict[str, object] = {
        "dataset_name": "Tenacious-Bench v0.1",
        "dataset_version": "0.1.0-interim",
        "source_seed_file": str(SOURCE.relative_to(ROOT)),
        "total_tasks": sum(len(rows) for rows in split_rows.values()),
        "target_split_ratio": {"train": 0.5, "dev": 0.3, "held_out": 0.2},
        "splits": {},
        "examples": {},
        "inter_rater_subset": [],
    }

    for split, rows in split_rows.items():
        summary["splits"][split] = {
            "count": len(rows),
            "risk_focus": dict(sorted(Counter(row["risk_focus"] for row in rows).items())),
            "task_type": dict(sorted(Counter(row["task_type"] for row in rows).items())),
            "source_mode": dict(sorted(Counter(row["source_mode"] for row in rows).items())),
            "difficulty": dict(sorted(Counter(row["difficulty"] for row in rows).items())),
            "expected_verdict": dict(
                sorted(Counter(row["ground_truth"]["expected_verdict"] for row in rows).items())
            ),
        }

    all_rows = [row for rows in split_rows.values() for row in rows]
    for source_mode in ("trace_derived", "programmatic", "hand_authored_adversarial"):
        example = next(row for row in all_rows if row["source_mode"] == source_mode)
        summary["examples"][source_mode] = {
            "task_id": example["task_id"],
            "split": example["split"],
            "risk_focus": example["risk_focus"],
            "task_type": example["task_type"],
            "company_name": example["metadata"]["company_name"],
        }

    dev_rows = split_rows["dev"]
    for risk_focus in RISK_FOCI:
        candidates = sorted(
            [row for row in dev_rows if row["risk_focus"] == risk_focus],
            key=lambda row: (stable_hash(row["task_id"]), row["task_id"]),
        )
        for row in candidates[:INTER_RATER_PER_RISK]:
            summary["inter_rater_subset"].append(
                {
                    "task_id": row["task_id"],
                    "risk_focus": row["risk_focus"],
                    "task_type": row["task_type"],
                    "source_mode": row["source_mode"],
                }
            )
    return summary


def main() -> int:
    rows = load_rows(SOURCE)
    split_rows = assign_splits(rows)

    OUTPUT_DIR.mkdir(exist_ok=True)
    for split in SPLITS:
        split_dir = OUTPUT_DIR / split
        split_dir.mkdir(exist_ok=True)
        ordered_rows = sorted(split_rows[split], key=lambda row: row["task_id"])
        write_jsonl(split_dir / "tasks.jsonl", ordered_rows)

    summary = build_summary(split_rows)
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
