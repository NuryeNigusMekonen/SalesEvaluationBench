# Methodology: Tenacious-Bench v0.1 Interim

## Path declaration

Selected path: `Path B`, preference-tuned judge / critic.

Why: the strongest Week 10 pattern is inconsistency under known policy boundaries, not a universally weak generator. The same agent sometimes chooses `book_meeting` cleanly and sometimes lands in `pricing_guardrail` or weak-signal overclaim territory on structurally similar scenarios. That makes a critic layer the right first intervention.

## Week 10 evidence behind Path B

- `tr_a12a84621b32`, `tr_a7af9f577001`, and `tr_73e8dc8bc8ef` all surface `low_confidence_signal_present`, showing the agent regularly operates under evidence uncertainty.
- `tr_cf2af9903e17`, `tr_17bc945c3ad4`, `tr_8fd4fe25723b`, `tr_d4ae5e4f32a8`, and `tr_98c8820d3d5f` show repeated inbound pricing-boundary cases that still resolve to `send_email`.
- `tr_1e4b31d1882a` records `segment_abstention`, while nearby traces for similar companies still proceed with active outbound or reply decisions. The system can be right; it is not reliably right.
- `tr_e3382190bf3c` and `tr_f98049559727` show opt-out and human-handoff logic that is specific to the Tenacious workflow and therefore worth judging explicitly.

## Dataset authoring method

The interim dataset is materialized from the checked-in `training/data/tenacious_bench_seed_200_v2.jsonl` seed set, which already extends the earlier 20-row and 60-row authoring passes. This keeps the interim build grounded in local Week 10 evidence and Tenacious seed materials rather than depending on fresh external model calls.

Source-mode mapping for the interim release:

- `trace` -> `trace_derived`
- `template` -> `programmatic`
- `manual_adversarial` -> `hand_authored_adversarial`
- `transcript` -> `hand_authored_adversarial`

Current composition:

- `200` total tasks
- `40` tasks per risk focus
- `96` programmatic, `50` trace-derived, `54` hand-authored adversarial
- No live `multi_llm_synthesis` rows in the Wednesday package yet; that expansion is deferred to the final submission

## Partitioning protocol

The benchmark is materialized into scenario-safe interim splits:

- `train`: `100`
- `dev`: `60`
- `held_out`: `40`

The current splitter is deterministic and stratified by risk focus so each split preserves all five failure families. Scenario IDs are unique across splits. One repeated synthetic company name, `OrbitStack Cloud`, still appears across `train` and `dev`; that is documented in the contamination report and is scheduled for cleanup before public release.

## Judge and filtering policy

This interim package is a judge-task benchmark. Each row includes:

- the Week 10 sales-agent output to be judged
- structured context and signal briefs
- an expected verdict: `pass`, `fail`, or `needs_human_review`
- a grounded rationale plus `chosen` and `rejected` preference responses

The deterministic evaluator at `scoring_evaluator.py` scores a candidate judge response on:

- verdict match
- overlap with the grounded expected reason
- matching source citations

## Contamination-check summary

Results are written to `contamination_check.json`.

- exact `scenario_id` overlap across splits: `0`
- exact repeated company overlap across splits: `OrbitStack Cloud` only
- embedding model: not available locally, so the interim pass uses token-cosine fallback
- high token overlap remains in parts of the synthetic expansion because many tasks share scaffolded prompt surfaces; this is explicitly treated as an interim limitation, not a solved problem

## Cost discipline

No new external API calls were used to materialize the Wednesday package. The interim build reuses local seed data, Week 10 traces, and checked-in Tenacious materials. Historic repo costs remain logged in `cost_log.md`, and no new τ²-Bench retail runs were performed for this Week 11 packaging pass.
