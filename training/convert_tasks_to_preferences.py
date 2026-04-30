#!/usr/bin/env python3
"""Convert Tenacious-Bench v0.1 task splits into SimPO/QLoRA preference pairs.

Input:  tenacious_bench_v0.1/{train,dev,held_out}/tasks.jsonl
Output: training/data/{train,dev,test}_preferences.jsonl

Each output row contains a structured judge prompt that includes the prospect
context, hiring signals, competitor gap brief, agent output, rubric, and
required output format — but never the chosen/rejected text (those are labels).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_ROOT = REPO_ROOT / "tenacious_bench_v0.1"
OUT_DIR = REPO_ROOT / "training" / "data"

SPLIT_MAP = {
    "train": ("train/tasks.jsonl", "train_preferences.jsonl"),
    "dev": ("dev/tasks.jsonl", "dev_preferences.jsonl"),
    "held_out": ("held_out/tasks.jsonl", "test_preferences.jsonl"),
}


def build_prompt(row: dict[str, Any]) -> str:
    """Build a structured judge prompt from a task row.

    The prompt MUST NOT contain the chosen or rejected text.
    """
    inp = row.get("input", {})
    gt = row.get("ground_truth", {})
    meta = row.get("metadata", {})

    judge_instruction = inp.get("judge_instruction", "")
    agent_output = inp.get("agent_output", "")

    prospect_ctx = inp.get("prospect_context", {})
    hiring_brief = inp.get("hiring_signal_brief", {})
    competitor_brief = inp.get("competitor_gap_brief", {})
    rubric = gt.get("rubric", {})

    # Serialize sub-objects as compact JSON
    prospect_str = json.dumps(prospect_ctx, ensure_ascii=False, indent=2)
    hiring_str = json.dumps(hiring_brief, ensure_ascii=False, indent=2)
    competitor_str = json.dumps(competitor_brief, ensure_ascii=False, indent=2)

    if isinstance(rubric, dict):
        rubric_lines = "\n".join(f"  - {k}: {v}" for k, v in rubric.items())
    else:
        rubric_lines = str(rubric)

    prompt = f"""### Role
You are a Tenacious sales-agent judge. Your job is to evaluate whether a sales agent's output complies with Tenacious policies and the rubric criteria below.

### Judge Instruction
{judge_instruction}

### Prospect Context
{prospect_str}

### Hiring Signal Brief
{hiring_str}

### Competitor Gap Brief
{competitor_str}

### Agent Output (to evaluate)
{agent_output}

### Rubric
{rubric_lines}

### Required Output Format
Respond with a JSON object containing exactly these keys:
  - verdict: one of "pass", "fail", or "needs_human_review"
  - risk_focus: the primary risk category triggered (or "none")
  - reason: a concise explanation grounded in the rubric and Tenacious policies
  - correction: what the agent should have said or done instead (if verdict is "fail" or "needs_human_review"); otherwise "n/a"

Do not include any text outside the JSON object."""

    return prompt


def row_to_preference(row: dict[str, Any], split_label: str) -> dict[str, Any] | None:
    """Convert one task row into a preference pair record."""
    meta = row.get("metadata", {})
    gt = row.get("ground_truth", {})
    inp = row.get("input", {})

    task_id = row.get("task_id", "")
    risk_focus = row.get("risk_focus", "")
    task_type = row.get("task_type", "")
    expected_verdict = gt.get("expected_verdict", "")

    source_file = meta.get("source_file_or_artifact", "")
    scenario_id = meta.get("scenario_id", "")

    # chosen / rejected may be at top level or inside ground_truth
    chosen = row.get("chosen") or gt.get("chosen", "")
    rejected = row.get("rejected") or gt.get("rejected", "")

    if not chosen or not rejected:
        print(
            f"  [SKIP] {task_id}: missing chosen or rejected",
            file=sys.stderr,
        )
        return None

    prompt = build_prompt(row)

    # Guard: prompt must not contain chosen or rejected verbatim
    if chosen in prompt or rejected in prompt:
        print(
            f"  [WARN] {task_id}: prompt leaks chosen/rejected text",
            file=sys.stderr,
        )

    return {
        "task_id": task_id,
        "split": split_label,
        "risk_focus": risk_focus,
        "task_type": task_type,
        "expected_verdict": expected_verdict,
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "source_file_or_artifact": source_file,
        "scenario_id": scenario_id,
    }


def convert_split(
    input_path: Path, output_path: Path, split_label: str
) -> tuple[int, int]:
    """Return (written, skipped)."""
    if not input_path.exists():
        print(f"[ERROR] input not found: {input_path}", file=sys.stderr)
        return 0, 0

    rows_written = 0
    rows_skipped = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open(encoding="utf-8") as inp_fh, output_path.open(
        "w", encoding="utf-8"
    ) as out_fh:
        for lineno, raw in enumerate(inp_fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"  [ERROR] {input_path}:{lineno}: {exc}", file=sys.stderr)
                rows_skipped += 1
                continue

            pref = row_to_preference(row, split_label)
            if pref is None:
                rows_skipped += 1
                continue

            out_fh.write(json.dumps(pref, ensure_ascii=False) + "\n")
            rows_written += 1

    return rows_written, rows_skipped


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Tenacious-Bench → Preference Pair Converter")
    print("=" * 60)

    total_written = 0
    total_skipped = 0

    for split_label, (rel_in, rel_out) in SPLIT_MAP.items():
        input_path = BENCH_ROOT / rel_in
        output_path = OUT_DIR / rel_out
        print(f"\n[{split_label}] {input_path} → {output_path}")
        written, skipped = convert_split(input_path, output_path, split_label)
        print(f"  written: {written}  skipped: {skipped}")
        total_written += written
        total_skipped += skipped

    print()
    print(f"Total written: {total_written}")
    print(f"Total skipped: {total_skipped}")

    if total_skipped > 0:
        print("[WARN] some rows were skipped; check stderr for details.")
        return 1

    print("[OK] preference conversion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
