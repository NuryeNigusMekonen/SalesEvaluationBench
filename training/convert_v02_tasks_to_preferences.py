#!/usr/bin/env python3
"""Convert Tenacious-Bench v0.2 task splits into preference pairs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_ROOT = REPO_ROOT / "tenacious_bench_v0.2"
OUT_DIR = REPO_ROOT / "training" / "data"

SPLIT_MAP = {
    "train": ("train/tasks.jsonl", "v02_train_preferences.jsonl"),
    "dev": ("dev/tasks.jsonl", "v02_dev_preferences.jsonl"),
    "held_out": ("held_out/tasks.jsonl", "v02_test_preferences.jsonl"),
}


def build_prompt(row: dict[str, Any]) -> str:
    """Build a structured judge prompt without leaking preference labels."""
    task_input = row.get("input", {})
    ground_truth = row.get("ground_truth", {})
    metadata = row.get("metadata", {})

    prospect_context = json.dumps(
        task_input.get("prospect_context", {}), ensure_ascii=False, indent=2
    )
    hiring_signal_brief = json.dumps(
        task_input.get("hiring_signal_brief", {}), ensure_ascii=False, indent=2
    )
    competitor_gap_brief = json.dumps(
        task_input.get("competitor_gap_brief", {}), ensure_ascii=False, indent=2
    )
    rubric = ground_truth.get("rubric", {})
    if isinstance(rubric, dict):
        rubric_text = "\n".join(f"  - {key}: {value}" for key, value in rubric.items())
    else:
        rubric_text = str(rubric)

    prompt = f"""### Role
You are a Tenacious sales-agent judge. Evaluate whether the supplied agent output follows Tenacious policy, source grounding, and tone rules.

### Judge Instruction
{task_input.get("judge_instruction", "")}

### Task Metadata
task_id: {row.get("task_id", "")}
risk_focus: {row.get("risk_focus", "")}
task_type: {row.get("task_type", "")}
scenario_id: {metadata.get("scenario_id", "")}

### Prospect Context
{prospect_context}

### Hiring Signal Brief
{hiring_signal_brief}

### Competitor Gap Brief
{competitor_gap_brief}

### Agent Output To Judge
{task_input.get("agent_output", "")}

### Rubric
{rubric_text}

### Required Output Format
Return a JSON object with exactly these keys:
  - verdict: one of "pass", "fail", or "needs_human_review"
  - risk_focus: the primary risk category triggered, or "none"
  - reason: concise evidence grounded in the row and Tenacious policy
  - correction: what the agent should have said or done instead; use "n/a" for pass

Do not include any text outside the JSON object."""
    return prompt


def row_to_preference(row: dict[str, Any], split: str) -> dict[str, Any] | None:
    metadata = row.get("metadata", {})
    ground_truth = row.get("ground_truth", {})
    chosen = str(ground_truth.get("chosen", ""))
    rejected = str(ground_truth.get("rejected", ""))
    task_id = str(row.get("task_id", ""))

    if not chosen or not rejected:
        print(f"[SKIP] {task_id}: missing chosen or rejected", file=sys.stderr)
        return None
    if chosen.strip() == rejected.strip():
        print(f"[SKIP] {task_id}: chosen and rejected are identical", file=sys.stderr)
        return None

    prompt = build_prompt(row)
    if chosen in prompt or rejected in prompt:
        print(f"[WARN] {task_id}: prompt contains chosen/rejected text", file=sys.stderr)

    return {
        "task_id": task_id,
        "split": "test" if split == "held_out" else split,
        "risk_focus": row.get("risk_focus", ""),
        "task_type": row.get("task_type", ""),
        "expected_verdict": ground_truth.get("expected_verdict", ""),
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "source_file_or_artifact": metadata.get("source_file_or_artifact", ""),
        "scenario_id": metadata.get("scenario_id", ""),
        "semantic_family": metadata.get("semantic_family", ""),
    }


def convert_split(input_path: Path, output_path: Path, split: str) -> tuple[int, int]:
    written = 0
    skipped = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open(encoding="utf-8") as input_file, output_path.open(
        "w", encoding="utf-8"
    ) as output_file:
        for lineno, raw in enumerate(input_file, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"[SKIP] {input_path}:{lineno}: {exc}", file=sys.stderr)
                skipped += 1
                continue
            pref = row_to_preference(row, split)
            if pref is None:
                skipped += 1
                continue
            output_file.write(json.dumps(pref, ensure_ascii=False) + "\n")
            written += 1
    return written, skipped


def main() -> int:
    print("=" * 60)
    print("Tenacious-Bench v0.2 Preference Converter")
    print("=" * 60)

    total_written = 0
    total_skipped = 0
    for split, (input_rel, output_name) in SPLIT_MAP.items():
        input_path = BENCH_ROOT / input_rel
        output_path = OUT_DIR / output_name
        if not input_path.exists():
            print(f"[ERROR] input not found: {input_path}", file=sys.stderr)
            total_skipped += 1
            continue
        written, skipped = convert_split(input_path, output_path, split)
        print(f"[{split}] written: {written} skipped: {skipped} -> {output_path}")
        total_written += written
        total_skipped += skipped

    print(f"\nTotal written: {total_written}")
    print(f"Total skipped: {total_skipped}")
    if total_skipped:
        print("FAIL - some rows were skipped.")
        return 1
    print("PASS - preference conversion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
