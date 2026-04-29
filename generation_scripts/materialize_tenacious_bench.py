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
RANDOM_SEED = 20260429
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
JUDGE_DIMENSION_THRESHOLDS = {
    "coherence": 4,
    "grounding": 4,
    "rubric_clarity": 4,
}
AUTHOR_TO_JUDGE_ROTATION = {
    "openai": ("anthropic", "openrouter", "local_rule"),
    "anthropic": ("openai", "openrouter", "local_rule"),
    "openrouter": ("openai", "anthropic", "local_rule"),
    "local_rule": ("openai", "anthropic"),
    "human": ("local_rule", "openai", "anthropic"),
    "unknown": ("local_rule", "openai", "anthropic"),
}
RUBRIC_KEYS = {
    "grounding",
    "policy_safety",
    "sales_quality",
    "next_action_correctness",
    "privacy_or_license_safety",
}


def load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def seeded_hash(value: str, seed: int = RANDOM_SEED) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def normalized_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(normalized_text(nested) for nested in value.values())
    if isinstance(value, list):
        return " ".join(normalized_text(nested) for nested in value)
    return " ".join(str(value).lower().split())


def infer_author_model_family(row: dict) -> str:
    provenance = row.get("source_provenance", {})
    generator = str(provenance.get("generator", "")).lower()
    if "openai" in generator or "gpt" in generator:
        return "openai"
    if "anthropic" in generator or "claude" in generator:
        return "anthropic"
    if "openrouter" in generator:
        return "openrouter"
    if "manual" in generator or "template" in generator or "trace" in generator:
        return "local_rule"
    if "human" in generator:
        return "human"
    return "unknown"


def select_judge_model_family(row: dict) -> str:
    author_family = infer_author_model_family(row)
    candidates = AUTHOR_TO_JUDGE_ROTATION[author_family]
    offset = int(seeded_hash(row["task_id"])[:8], 16) % len(candidates)
    judge_family = candidates[offset]
    if judge_family == author_family:
        raise ValueError(
            f"self-judging blocked for {row['task_id']}: author and judge are both {author_family}"
        )
    return judge_family


def score_judge_dimensions(row: dict) -> dict[str, int]:
    has_required_fields = all(
        row.get(field)
        for field in (
            "task_id",
            "task_type",
            "risk_focus",
            "agent_output",
            "judge_instruction",
            "expected_verdict",
            "expected_reason",
            "chosen",
            "rejected",
        )
    )
    coherence = 5 if has_required_fields and row["expected_verdict"] in {"pass", "fail", "needs_human_review"} else 2

    source_text = str(row.get("source_file_or_artifact", ""))
    expected_reason = str(row.get("expected_reason", ""))
    grounding = 5 if source_text and expected_reason and "+" in source_text else 4 if source_text and expected_reason else 2

    rubric = row.get("rubric", {})
    rubric_keys_present = isinstance(rubric, dict) and RUBRIC_KEYS.issubset(rubric)
    rubric_clarity = 5 if rubric_keys_present and row["risk_focus"] in row["judge_instruction"] else 4 if rubric_keys_present else 2

    return {
        "coherence": coherence,
        "grounding": grounding,
        "rubric_clarity": rubric_clarity,
    }


def preference_pair_signature(row: dict) -> str:
    pair_text = "|".join(
        normalized_text(row.get(field, ""))
        for field in (
            "judge_instruction",
            "agent_output",
            "expected_verdict",
            "expected_reason",
            "chosen",
            "rejected",
        )
    )
    return stable_hash(pair_text)


def prepare_generation_batch(rows: list[dict]) -> tuple[list[dict], dict]:
    included_rows = []
    rejected_rows = []
    seen_pair_signatures: dict[str, str] = {}
    duplicate_pairs = []
    judge_assignments = Counter()
    author_families = Counter()

    for row in rows:
        author_family = infer_author_model_family(row)
        judge_family = select_judge_model_family(row)
        dimension_scores = score_judge_dimensions(row)
        passes_thresholds = all(
            score >= JUDGE_DIMENSION_THRESHOLDS[dimension]
            for dimension, score in dimension_scores.items()
        )
        pair_signature = preference_pair_signature(row)
        duplicate_of = seen_pair_signatures.get(pair_signature)

        row["_judge_filter"] = {
            "author_model_family": author_family,
            "assigned_judge_model_family": judge_family,
            "dimension_scores": dimension_scores,
            "pair_signature": pair_signature,
            "passed_thresholds": passes_thresholds,
            "duplicate_of": duplicate_of,
        }

        if not passes_thresholds:
            rejected_rows.append(
                {
                    "task_id": row["task_id"],
                    "reason": "judge_dimension_threshold",
                    "dimension_scores": dimension_scores,
                }
            )
            continue
        if duplicate_of:
            duplicate_pairs.append(
                {
                    "task_id": row["task_id"],
                    "duplicate_of": duplicate_of,
                    "pair_signature": pair_signature,
                }
            )
            continue

        seen_pair_signatures[pair_signature] = row["task_id"]
        included_rows.append(row)
        judge_assignments[judge_family] += 1
        author_families[author_family] += 1

    return included_rows, {
        "random_seed": RANDOM_SEED,
        "judge_dimension_thresholds": JUDGE_DIMENSION_THRESHOLDS,
        "author_to_judge_rotation": AUTHOR_TO_JUDGE_ROTATION,
        "included_count": len(included_rows),
        "rejected_count": len(rejected_rows),
        "rejected_rows_sample": rejected_rows[:10],
        "exact_preference_pair_duplicates_removed": len(duplicate_pairs),
        "duplicate_pair_sample": duplicate_pairs[:10],
        "judge_assignments": dict(sorted(judge_assignments.items())),
        "author_families": dict(sorted(author_families.items())),
    }


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
            "judge_filter": row["_judge_filter"],
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
            if len(chunk) != count:
                raise ValueError(
                    f"not enough rows for {risk_focus} {split}: needed {count}, found {len(chunk)}"
                )
            cursor += count
            for row in chunk:
                split_rows[split].append(transform_row(row, split))
    return split_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "\n".join(json.dumps(row, ensure_ascii=True) for row in rows) + "\n"
    path.write_text(text, encoding="utf-8")


def build_summary(split_rows: dict[str, list[dict]], filter_report: dict) -> dict:
    summary: dict[str, object] = {
        "dataset_name": "Tenacious-Bench v0.1",
        "dataset_version": "0.1.0-interim",
        "source_seed_file": str(SOURCE.relative_to(ROOT)),
        "total_tasks": sum(len(rows) for rows in split_rows.values()),
        "target_split_ratio": {"train": 0.5, "dev": 0.3, "held_out": 0.2},
        "random_seed": RANDOM_SEED,
        "judge_filter": filter_report,
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
    rows, filter_report = prepare_generation_batch(rows)
    split_rows = assign_splits(rows)

    OUTPUT_DIR.mkdir(exist_ok=True)
    for split in SPLITS:
        split_dir = OUTPUT_DIR / split
        split_dir.mkdir(exist_ok=True)
        ordered_rows = sorted(split_rows[split], key=lambda row: row["task_id"])
        write_jsonl(split_dir / "tasks.jsonl", ordered_rows)

    summary = build_summary(split_rows, filter_report)
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
