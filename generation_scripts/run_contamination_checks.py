#!/usr/bin/env python3
"""Run deterministic contamination checks over the interim Tenacious-Bench splits."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "tenacious_bench_v0.1"
OUTPUT = ROOT / "contamination_check.json"
SPLITS = ("train", "dev", "held_out")
TOKEN_RE = re.compile(r"[a-z0-9]+")


def load_rows(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def normalize_text(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def collect_scalars(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        items: list[str] = []
        for nested in value.values():
            items.extend(collect_scalars(nested))
        return items
    if isinstance(value, list):
        items: list[str] = []
        for nested in value:
            items.extend(collect_scalars(nested))
        return items
    return [str(value)]


def flatten(row: dict) -> str:
    values: list[str] = []
    for field in (
        row["input"]["prospect_context"],
        row["input"]["hiring_signal_brief"],
        row["input"]["competitor_gap_brief"],
    ):
        values.extend(collect_scalars(field))
    return normalize_text(" ".join(values))


def ngrams(text: str, n: int = 8) -> set[str]:
    tokens = text.split()
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[index : index + n]) for index in range(len(tokens) - n + 1)}


def cosine_similarity(text_a: str, text_b: str) -> float:
    counts_a = Counter(text_a.split())
    counts_b = Counter(text_b.split())
    shared = set(counts_a) & set(counts_b)
    numerator = sum(counts_a[token] * counts_b[token] for token in shared)
    denom_a = math.sqrt(sum(value * value for value in counts_a.values()))
    denom_b = math.sqrt(sum(value * value for value in counts_b.values()))
    if not denom_a or not denom_b:
        return 0.0
    return numerator / (denom_a * denom_b)


def scan_pairs(rows_a: list[dict], rows_b: list[dict]) -> dict:
    pairs = []
    ngram_pairs = []
    embedding_pairs = []
    max_ngram_overlap = 0
    max_cosine = 0.0
    closest = None
    for row_a in rows_a:
        text_a = row_a["_normalized_text"]
        ngrams_a = row_a["_ngrams"]
        for row_b in rows_b:
            text_b = row_b["_normalized_text"]
            ngrams_b = row_b["_ngrams"]
            shared_ngrams = len(ngrams_a & ngrams_b)
            cosine = cosine_similarity(text_a, text_b)
            if shared_ngrams > max_ngram_overlap or cosine > max_cosine:
                closest = {
                    "left_task_id": row_a["task_id"],
                    "right_task_id": row_b["task_id"],
                    "shared_8gram_count": shared_ngrams,
                    "token_cosine_similarity": round(cosine, 4),
                }
            max_ngram_overlap = max(max_ngram_overlap, shared_ngrams)
            max_cosine = max(max_cosine, cosine)
            if shared_ngrams > 0 or cosine >= 0.85:
                pair = {
                    "left_task_id": row_a["task_id"],
                    "right_task_id": row_b["task_id"],
                    "shared_8gram_count": shared_ngrams,
                    "token_cosine_similarity": round(cosine, 4),
                }
                pairs.append(pair)
                if shared_ngrams > 0:
                    ngram_pairs.append(pair)
                if cosine >= 0.85:
                    embedding_pairs.append(pair)
    return {
        "pair_count_flagged": len(pairs),
        "ngram_pair_count_flagged": len(ngram_pairs),
        "embedding_fallback_pair_count_flagged": len(embedding_pairs),
        "max_shared_8gram_count": max_ngram_overlap,
        "max_token_cosine_similarity": round(max_cosine, 4),
        "closest_pair": closest,
        "flagged_pairs_sample": pairs[:10],
        "ngram_flagged_pairs_sample": ngram_pairs[:10],
        "embedding_fallback_flagged_pairs_sample": embedding_pairs[:10],
    }


def main() -> int:
    split_rows = {
        split: load_rows(DATASET_DIR / split / "tasks.jsonl")
        for split in SPLITS
    }
    for rows in split_rows.values():
        for row in rows:
            normalized = flatten(row)
            row["_normalized_text"] = normalized
            row["_ngrams"] = ngrams(normalized)

    exact_scenario_overlap = {}
    exact_company_overlap = {}
    for left in SPLITS:
        for right in SPLITS:
            if left >= right:
                continue
            left_scenarios = {row["metadata"]["scenario_id"] for row in split_rows[left]}
            right_scenarios = {row["metadata"]["scenario_id"] for row in split_rows[right]}
            left_companies = {row["metadata"]["company_name"] for row in split_rows[left]}
            right_companies = {row["metadata"]["company_name"] for row in split_rows[right]}
            key = f"{left}__vs__{right}"
            exact_scenario_overlap[key] = sorted(left_scenarios & right_scenarios)
            exact_company_overlap[key] = sorted(left_companies & right_companies)

    report = {
        "dataset": "Tenacious-Bench v0.1",
        "checked_at": "2026-04-29",
        "methods": {
            "exact_overlap": "scenario_id and company_name set intersection across splits",
            "ngram_overlap": "shared normalized 8-gram count across split pairs",
            "embedding_similarity": {
                "status": "fallback_used",
                "method": "token cosine similarity over normalized text",
                "limitation": "No local embedding model is pinned in-repo for this interim pass, so token cosine is used as a deterministic fallback."
            },
            "time_shift": "manual note based on local seed documents, snapshots, and Week 10 traces only",
        },
        "split_counts": {
            split: len(rows) for split, rows in split_rows.items()
        },
        "exact_overlap": {
            "scenario_id": exact_scenario_overlap,
            "company_name": exact_company_overlap,
        },
        "pairwise_checks": {
            "train_vs_dev": scan_pairs(split_rows["train"], split_rows["dev"]),
            "train_vs_held_out": scan_pairs(split_rows["train"], split_rows["held_out"]),
            "dev_vs_held_out": scan_pairs(split_rows["dev"], split_rows["held_out"]),
        },
        "time_shift_notes": {
            "status": "documented",
            "note": "This interim dataset is built only from local Week 10 traces, outbox artifacts, and static Tenacious seed materials already checked into the repo. No fresh public-signal retrieval was performed during this materialization pass. Residual time-shift risk remains for tasks that reference funding, layoffs, or hiring signals captured in those static seed materials."
        },
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
