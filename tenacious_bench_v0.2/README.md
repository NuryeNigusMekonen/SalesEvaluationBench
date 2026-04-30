# Tenacious-Bench v0.2

This package contains the approved v0.2 Tenacious-Bench split created from `training/data/tenacious_bench_v0_2_expansion_100.jsonl` after self-review in `reports/manual_review_v02_expansion_100.md`.

## Files

- `train/tasks.jsonl`
- `dev/tasks.jsonl`
- `held_out/tasks.jsonl`
- `summary.json`

## Composition

- total tasks: `100`
- split counts: `70 train`, `15 dev`, `15 held_out`
- source filter: only rows with `reviewer_verdict=approve`
- v0.1 held-out use: none

## Split Policy

Rows were assigned by whole `scenario_id` and `metadata.semantic_family`. Near-duplicate templates such as overclaimed funding/capacity claims, CRM auto-booking, generic follow-up wording, escalation handoff ambiguity, and pricing-scope boundaries are kept within one split.

The split is intended for benchmark packaging and preference conversion only. Do not train on this package until validation has passed and the user explicitly asks to train.

## Validation

```bash
python training/validate_v02_split.py
python training/convert_v02_tasks_to_preferences.py
python training/validate_v02_preferences.py
```
