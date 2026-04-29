# Generation Scripts

This folder contains the reproducible authoring pipeline for the Week 11 interim benchmark package.

## What is here

- `materialize_tenacious_bench.py`
  Builds `tenacious_bench_v0.1/` from `training/data/tenacious_bench_seed_200_v2.jsonl`, assigns deterministic train/dev/held_out splits, and writes `summary.json`.
- `run_contamination_checks.py`
  Runs exact-overlap, shared 8-gram, and token-cosine fallback checks across the materialized splits and writes `contamination_check.json`.
- `judge_prompts.md`
  Documents the offline prompt contracts and model-routing placeholders for later multi-LLM expansion.

## Local commands

```bash
python generation_scripts/materialize_tenacious_bench.py
python generation_scripts/run_contamination_checks.py
python training/validate_tenacious_bench.py training/data/tenacious_bench_seed_200_v2.jsonl --expected-count 200
```

## Notes

- The current interim dataset is materialized from the local `seed_200_v2` file and does not require network access.
- Multi-LLM synthesis is planned for the final submission; the routing policy and prompt placeholders are documented now so they can be swapped in without changing the dataset contract.
