# Methodology Rationale (Act III, Path B)

## Path choice and objective

Selected path: `Path B` (preference-tuned judge/critic).

The Week 10 evidence shows a consistency problem more than a pure generation problem. The system can produce correct actions on many rows, but it is unreliable near policy boundaries. That pattern favors a critic layer trained on pairwise preferences over a generator-only LoRA.

## Week 10 evidence that drove the design

Three repeated boundary classes from Week 10 traces motivated Path B:

- Weak-signal interpretation risk:
  `tr_a12a84621b32`, `tr_a7af9f577001`, and `tr_73e8dc8bc8ef` include `low_confidence_signal_present`, where the main failure is not grammar but unsupported confidence.
- Pricing and scope guardrail risk:
  `tr_cf2af9903e17`, `tr_17bc945c3ad4`, and `tr_8fd4fe25723b` show threads that continue while carrying pricing-boundary flags.
- Escalation and stop-condition risk:
  `tr_e3382190bf3c`, `tr_f98049559727`, and `tr_bae3299d6e7e` show opt-out and handoff behavior that must be judged against workflow rules, not tone alone.

These are exactly the cases where preference supervision helps: the critic must prefer a grounded, policy-correct decision over a fluent but unsafe one.

## Paper-grounded method decisions

Two core papers directly shaped the training-data format:

1. **Direct Preference Optimization (Rafailov et al., 2023)**  
   DPO formalizes learning from `(chosen, rejected)` pairs without requiring scalar rewards. This maps cleanly to our judge-task rows where each sample contains a preferred critique and a plausible but incorrect critique.

2. **SimPO (Meng, Xia, and Chen, 2024)**  
   SimPO supports reference-free preference optimization, which is compute-efficient for small LoRA runs. It also reduces operational complexity compared with maintaining a separate reference model.

A third paper shaped leakage controls:

3. **Preference Leakage (Li et al., 2025)**  
   We explicitly separate generator and judge model families in the authoring pipeline and keep deterministic provenance metadata. This reduces the chance that a single model family both writes and validates the same preference pattern.

## Training-data construction for Path B

The Path B training format is pairwise preferences:

- prompt/context: prospect context + briefs + agent output + judge instruction
- `chosen`: corrected critique aligned to rubric and policy
- `rejected`: plausible critique that misses a key rule

Prepared files:

- `training_data/train_preferences.jsonl` (100 rows)
- `training_data/dev_preferences.jsonl` (60 rows)
- `training_data/test_preferences.jsonl` (40 rows)

These are converted from Tenacious-Bench task rows with deterministic scripts in `training/convert_tasks_to_preferences.py` and validated with `training/validate_preference_splits.py`.

## Contamination and split safety

Contamination checks for Act III were run between training preferences and both evaluation partitions:

- train vs dev: zero overlap on `task_id`, `scenario_id`, and exact `(chosen, rejected)` pair signatures
- train vs held-out: zero overlap on the same checks

The report is committed as:

- `training_data/contamination_check_train_vs_dev_held_out.json`

This gives a mechanically auditable pass condition for the Day 4 deliverable and keeps preference tuning isolated from evaluation partitions.

## Why this is the right Day 4 tradeoff

Given the Week 10 failure profile, spending Day 4 on preference data quality is the highest-leverage choice. A critic trained on grounded preference pairs can block unsafe outputs even when the generator remains unchanged. This matches the observed failure mode (inconsistent boundary decisions) and gives the best chance of non-flat Day 5 ablations on held-out.
