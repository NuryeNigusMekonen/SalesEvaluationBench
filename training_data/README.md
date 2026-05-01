# Act III Training Data (Path B)

This folder is the Act III deliverable package for `Path B` (preference-tuned judge/critic).

## Files

- `train_preferences.jsonl` (100 rows)
- `dev_preferences.jsonl` (60 rows)
- `test_preferences.jsonl` (40 rows)
- `contamination_check_train_vs_dev_held_out.json`

## Format

Each row is a preference-training item with:

- prompt/context fields derived from Tenacious-Bench task inputs
- `chosen` critique (policy-correct, grounded)
- `rejected` critique (plausible but incorrect)
- task metadata (`task_id`, `risk_focus`, `task_type`, `expected_verdict`, scenario metadata)

## Validation commands

```bash
python training/validate_preference_splits.py
python training/validate_v02_preferences.py
```

## Contamination status

`contamination_check_train_vs_dev_held_out.json` records the Day 4 check that training preferences do not overlap with dev/held-out on:

- `task_id`
- `scenario_id`
- exact `(chosen, rejected)` pair signatures

All checks pass for the packaged v0.1 preference split (`100/60/40`).
