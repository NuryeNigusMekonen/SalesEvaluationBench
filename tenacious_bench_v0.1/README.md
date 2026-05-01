# Tenacious-Bench v0.1

This folder contains the Week 11 interim benchmark partitions.

## Files

- `train/tasks.jsonl`
- `dev/tasks.jsonl`
- `held_out/tasks.jsonl`
- `summary.json`
- `datasheet.md`
- `contamination_check.json`
- `inter_rater_agreement.md`

## Composition

- total tasks: `200`
- split counts: `100 train`, `60 dev`, `40 held_out`
- risk-focus balance: `40` per category overall
- source modes: `96 programmatic`, `50 trace-derived`, `54 hand-authored adversarial`

## Rebuild

```bash
python generation_scripts/materialize_tenacious_bench.py
python generation_scripts/run_contamination_checks.py
```

## Important note

The held-out split here is included for the interim repo submission. Before the public release, it should be re-reviewed with the contamination report and inter-rater exercise completed.
