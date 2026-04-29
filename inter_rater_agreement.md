# Inter-Rater Agreement Plan

## Current status

- Round 1 labels: present in the materialized benchmark rows
- Round 2 labels: pending
- Interim state: protocol ready, calibration subset selected, final agreement score not yet computed

This file is intentionally honest about the current state. The Wednesday submission includes the protocol and the selected 30-task subset, but not yet the completed second-pass agreement matrix.

## Protocol

1. Use the 30-task subset drawn from the `dev` split.
2. Label each row independently as `pass`, `fail`, or `needs_human_review` using only the task input, rubric, and source notes.
3. Wait at least 24 hours.
4. Re-label the same 30 rows without reading the first pass.
5. Compute raw agreement and per-risk-focus agreement.
6. If any risk focus falls below `80%`, revise the rubric and repeat the exercise on that slice.

## Selected 30-task calibration subset

Six rows per risk focus:

- `unsupported_pricing_or_scope_claim`
  `tb_seed_0086`, `tb_seed_0068`, `tb_seed_0003`, `tb_seed_0064`, `tb_seed_0067`, `tb_seed_0077`
- `overclaimed_signal_or_maturity_claim`
  `tb_seed_0009`, `tb_seed_0090`, `tb_seed_0093`, `tb_seed_0111`, `tb_seed_0098`, `tb_seed_0100`
- `generic_outreach_ungrounded`
  `tb_seed_0125`, `tb_seed_0123`, `tb_seed_0141`, `tb_seed_0127`, `tb_seed_0117`, `tb_seed_0119`
- `wrong_crm_hubspot_calendar_next_action`
  `tb_seed_0164`, `tb_seed_0156`, `tb_seed_0165`, `tb_seed_0043`, `tb_seed_0145`, `tb_seed_0157`
- `reply_escalation_or_objection_failure`
  `tb_seed_0183`, `tb_seed_0199`, `tb_seed_0184`, `tb_seed_0055`, `tb_seed_0052`, `tb_seed_0059`

## Round 1 notes

Round 1 is represented by the checked-in task labels from `training/data/tenacious_bench_seed_200_v2.jsonl` and the materialized split files. These labels already mark `label_confidence` and `requires_manual_review`, which will be useful for prioritizing ambiguous cases during Round 2.

## TODO before final submission

- record Round 2 labels in a machine-readable file
- compute overall agreement and per-risk-focus agreement
- add a small confusion table for `pass` vs `needs_human_review`
- note any rubric revisions triggered by disagreement
