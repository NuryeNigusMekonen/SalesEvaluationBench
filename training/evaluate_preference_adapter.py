#!/usr/bin/env python3
"""Batch preference-scoring evaluator for the Tenacious judge adapter.

Loads a base model + LoRA adapter, scores each (prompt, chosen, rejected)
triple using per-token log-probabilities, and reports accuracy by risk_focus,
task_type, and expected_verdict.

Usage:
    python3 training/evaluate_preference_adapter.py \
        --adapter-path outputs/tenacious-judge-v02-simpo-lora \
        --split-file training/data/v02_dev_preferences.jsonl \
        --output-report outputs/v02_dev_eval_report.json

A row is marked correct when chosen_logprob > rejected_logprob.
No generation is performed; scoring is deterministic.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

BASE_MODEL = "Qwen/Qwen2.5-3B-Instruct"
PROGRESS_EVERY = 10


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _require_package(name: str) -> None:
    if importlib.util.find_spec(name) is None:
        print(
            f"\nERROR: required package '{name}' is not installed.\n"
            f"This evaluator is designed to run on Google Colab T4 with the\n"
            f"packages from training/COLAB_TRAINING_GUIDE.md installed:\n"
            f"  pip install unsloth unsloth_zoo transformers trl peft\n",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _load_model_and_tokenizer(adapter_path: str):
    """Load base model + LoRA adapter.  Prefers Unsloth for 4-bit on T4."""
    import torch

    adapter = Path(adapter_path)
    if not adapter.exists():
        print(
            f"\nERROR: adapter path does not exist: {adapter_path}\n"
            f"Train the adapter first (see training/COLAB_TRAINING_GUIDE.md),\n"
            f"then run this evaluator against the saved checkpoint.\n",
            file=sys.stderr,
        )
        raise SystemExit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("WARNING: CUDA not available — running on CPU (slow).", file=sys.stderr)

    if importlib.util.find_spec("unsloth") is not None:  # noqa: F821 — top-level import
        from unsloth import FastLanguageModel
        from peft import PeftModel

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=BASE_MODEL,
            max_seq_length=2048,
            dtype=None,
            load_in_4bit=True,
        )
        # PeftModel.from_pretrained loads an existing adapter; do NOT call
        # FastLanguageModel.get_peft_model here — that creates a new adapter
        # and expects an integer rank, not a path.
        model = PeftModel.from_pretrained(model, adapter_path)
        model.eval()
        print(f"Loaded via Unsloth (4-bit) + PEFT: {BASE_MODEL} + {adapter_path}")
    else:
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel

        quant_cfg = None
        if device == "cuda":
            try:
                quant_cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype="float16")
            except Exception:
                pass

        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            quantization_config=quant_cfg,
            device_map="auto" if device == "cuda" else None,
            torch_dtype="auto",
        )
        model = PeftModel.from_pretrained(model, adapter_path)
        model.eval()
        print(f"Loaded via PEFT: {BASE_MODEL} + {adapter_path}")

    return model, tokenizer, device


# ---------------------------------------------------------------------------
# Log-probability scoring
# ---------------------------------------------------------------------------

def _sequence_logprob(model, tokenizer, device: str, prompt: str, response: str) -> float:
    """Return sum of per-token log-probabilities for *response* given *prompt*.

    The model sees the full (prompt + response) sequence; only the response
    token positions contribute to the score.  No tokens are generated.
    """
    import torch

    full_text = prompt + response
    enc_full = tokenizer(full_text, return_tensors="pt", truncation=True, max_length=2048)
    enc_prompt = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

    prompt_len = enc_prompt["input_ids"].shape[1]
    input_ids = enc_full["input_ids"].to(device)
    attention_mask = enc_full["attention_mask"].to(device)

    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        log_probs = torch.nn.functional.log_softmax(outputs.logits, dim=-1)

    # log_probs[0, t, :] is the distribution over the next token after position t.
    # We want P(token[t+1] | tokens[0..t]) for t in [prompt_len-1, seq_len-2].
    ids = input_ids[0]
    seq_len = ids.shape[0]
    if seq_len <= prompt_len:
        return 0.0

    # Gather log-probs at each response token position.
    response_ids = ids[prompt_len:seq_len]          # shape: (R,)
    lp_slice = log_probs[0, prompt_len - 1 : seq_len - 1, :]  # shape: (R, vocab)
    token_logprobs = lp_slice.gather(1, response_ids.unsqueeze(1)).squeeze(1)
    return float(token_logprobs.sum().item())


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"WARNING: skipping line {lineno} in {path} — {exc}", file=sys.stderr)
    return rows


def _update_breakdown(
    breakdown: dict[str, dict[str, int]],
    key: str,
    value: str,
    correct: bool,
) -> None:
    if value not in breakdown[key]:
        breakdown[key][value] = {"correct": 0, "total": 0}
    breakdown[key][value]["total"] += 1
    if correct:
        breakdown[key][value]["correct"] += 1


def _accuracy(counts: dict[str, int]) -> float:
    total = counts.get("total", 0)
    return round(counts["correct"] / total, 4) if total else 0.0


def _breakdown_with_accuracy(raw: dict[str, dict[str, dict[str, int]]]) -> dict:
    result = {}
    for dim, values in raw.items():
        result[dim] = {}
        for val, counts in values.items():
            result[dim][val] = {
                "correct": counts["correct"],
                "total": counts["total"],
                "accuracy": _accuracy(counts),
            }
    return result


def evaluate(
    model,
    tokenizer,
    device: str,
    rows: list[dict],
    split_label: str,
) -> dict[str, Any]:
    total = len(rows)
    correct_count = 0
    row_results = []

    breakdown_raw: dict[str, dict[str, dict[str, int]]] = {
        "by_risk_focus": {},
        "by_task_type": {},
        "by_expected_verdict": {},
    }

    for idx, row in enumerate(rows):
        task_id = row.get("task_id", f"row_{idx}")
        prompt = row.get("prompt", "")
        chosen = row.get("chosen", "")
        rejected = row.get("rejected", "")

        chosen_lp = _sequence_logprob(model, tokenizer, device, prompt, chosen)
        rejected_lp = _sequence_logprob(model, tokenizer, device, prompt, rejected)
        correct = chosen_lp > rejected_lp

        if correct:
            correct_count += 1

        _update_breakdown(breakdown_raw, "by_risk_focus", row.get("risk_focus", "unknown"), correct)
        _update_breakdown(breakdown_raw, "by_task_type", row.get("task_type", "unknown"), correct)
        _update_breakdown(breakdown_raw, "by_expected_verdict", row.get("expected_verdict", "unknown"), correct)

        row_results.append({
            "task_id": task_id,
            "correct": correct,
            "chosen_logprob": round(chosen_lp, 6),
            "rejected_logprob": round(rejected_lp, 6),
            "margin": round(chosen_lp - rejected_lp, 6),
            "risk_focus": row.get("risk_focus"),
            "task_type": row.get("task_type"),
            "expected_verdict": row.get("expected_verdict"),
        })

        if (idx + 1) % PROGRESS_EVERY == 0 or (idx + 1) == total:
            acc_so_far = correct_count / (idx + 1)
            print(f"  [{idx + 1:4d}/{total}]  running accuracy: {acc_so_far:.3f}")

    overall_accuracy = round(correct_count / total, 4) if total else 0.0

    return {
        "split": split_label,
        "total": total,
        "correct": correct_count,
        "accuracy": overall_accuracy,
        **_breakdown_with_accuracy(breakdown_raw),
        "rows": row_results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Batch log-probability preference evaluator for the Tenacious judge adapter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--adapter-path",
        required=True,
        metavar="PATH",
        help="Path to the saved LoRA adapter (e.g. outputs/tenacious-judge-v02-simpo-lora).",
    )
    p.add_argument(
        "--split-file",
        required=True,
        metavar="FILE",
        help="JSONL preference file to evaluate (prompt/chosen/rejected rows).",
    )
    p.add_argument(
        "--output-report",
        required=True,
        metavar="FILE",
        help="Where to write the JSON evaluation report.",
    )
    p.add_argument(
        "--base-model",
        default=BASE_MODEL,
        metavar="MODEL_ID",
        help=f"HuggingFace model ID for the base model (default: {BASE_MODEL}).",
    )
    p.add_argument(
        "--held-out",
        action="store_true",
        default=False,
        help=(
            "Mark this run as the sealed v0.2 held-out evaluation. "
            "Run only once, after dev evaluation has been reviewed. "
            "Do not tune hyperparameters after seeing these results."
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    split_path = Path(args.split_file)
    if not split_path.exists():
        print(f"ERROR: split file not found: {args.split_file}", file=sys.stderr)
        return 1

    output_path = Path(args.output_report)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check ML packages before loading anything.
    _require_package("torch")
    _require_package("transformers")

    HELD_OUT_WARNING = (
        "Held-out test result was run once after dev review and was not used for tuning."
    )

    print(f"\nTenacious Judge Adapter — Preference Evaluator")
    if args.held_out:
        print(f"  *** SEALED HELD-OUT EVALUATION — run once only ***")
        print(f"  *** {HELD_OUT_WARNING} ***")
    print(f"  adapter  : {args.adapter_path}")
    print(f"  split    : {args.split_file}")
    print(f"  report   : {args.output_report}")
    print(f"  base     : {args.base_model}")
    print()

    rows = _load_jsonl(split_path)
    print(f"Loaded {len(rows)} rows from {split_path.name}")

    model, tokenizer, device = _load_model_and_tokenizer(args.adapter_path)

    split_label = split_path.stem
    print(f"\nScoring {len(rows)} rows (progress every {PROGRESS_EVERY})...")
    report = evaluate(model, tokenizer, device, rows, split_label)
    report["adapter_path"] = args.adapter_path
    report["split_file"] = str(split_path)
    report["base_model"] = args.base_model
    if args.held_out:
        report["held_out_evaluation"] = True
        report["held_out_warning"] = HELD_OUT_WARNING

    output_path.write_text(json.dumps(report, indent=2))

    # Print summary.
    print(f"\n{'='*60}")
    if args.held_out:
        print(f"*** SEALED HELD-OUT EVALUATION ***")
        print(f"*** {HELD_OUT_WARNING} ***")
        print()
    print(f"Split  : {split_label}")
    print(f"Total  : {report['total']}")
    print(f"Correct: {report['correct']}")
    print(f"Accuracy: {report['accuracy']:.4f} ({report['accuracy']*100:.1f}%)")
    print()
    print("By risk_focus:")
    for k, v in sorted(report["by_risk_focus"].items()):
        print(f"  {k:<45} {v['correct']}/{v['total']}  ({v['accuracy']*100:.1f}%)")
    print()
    print("By task_type:")
    for k, v in sorted(report["by_task_type"].items()):
        print(f"  {k:<45} {v['correct']}/{v['total']}  ({v['accuracy']*100:.1f}%)")
    print()
    print("By expected_verdict:")
    for k, v in sorted(report["by_expected_verdict"].items()):
        print(f"  {k:<45} {v['correct']}/{v['total']}  ({v['accuracy']*100:.1f}%)")
    print(f"\nReport saved to: {output_path}")
    print(f"{'='*60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
