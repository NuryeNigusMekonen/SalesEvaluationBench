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

Required-reading rationale:

- Rafailov et al.'s Direct Preference Optimization paper supports the `chosen` / `rejected` pair structure: the benchmark teaches a critic to prefer the rationale that catches the Tenacious-specific failure instead of merely imitating fluent sales prose.
- Meng, Xia, and Chen's SimPO paper motivates concise, calibrated judge responses and length-aware preference pairs, which matters because a verbose critique should not beat a short correct one by style alone.
- Li et al.'s Preference Leakage paper is the reason the generation notes and materializer enforce model-family separation: a model family that authors a task should not also judge that same task family.
- Pushkarna et al.'s Data Cards paper and the Gebru et al. datasheets framing drive the layered documentation in `datasheet.md`, especially provenance, intended uses, limits, and maintenance.

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

The current splitter is deterministic and stratified by risk focus so each split preserves all five failure families. The judge-routing filter uses the pinned seed `20260429`. Scenario IDs are unique across splits. One repeated synthetic company-name overlap remains after materialization: `OrbitStack Cloud` across `dev` / `train`. It is documented in the contamination report and scheduled for co-location or renaming before public release.

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

The generation filter in `generation_scripts/materialize_tenacious_bench.py` also executes the scaffold that had previously lived only in prose: model-family rotation blocks self-judging, judge-dimension thresholds are set to `>=4/5` for coherence, grounding, and rubric clarity, and exact duplicate chosen/rejected preference-pair signatures are removed before split assignment. In the current local batch, `200` rows passed, `0` rows failed thresholds, and `0` exact preference-pair duplicates were removed.

## Contamination-check summary

Results are written to `contamination_check.json`.

Results by check type:

| Check type | Flagged result | Resolution |
|---|---:|---|
| Exact `scenario_id` overlap | `0` across all split pairs | No action needed. |
| Exact `company_name` overlap | `1` split-pair overlap: `OrbitStack Cloud` | Retained for the interim with explicit disclosure; co-locate or rename before public release. |
| Exact preference-pair duplicate | `0` removed by the materializer | No duplicate pair removal needed in this batch. |
| Shared normalized 8-gram overlap | `2881` train/dev pairs, `2034` train/held-out pairs, `1193` dev/held-out pairs | Treated as template-scaffold leakage risk; retained only as interim data and called out as a limitation. |
| Embedding-style similarity | `0` token-cosine fallback pairs at the `>=0.85` threshold | No removal from this check; a real pinned embedding model should replace the fallback before public release. |
| Time-shift check | Manual snapshot review only | No fresh public-signal retrieval was used; static funding, hiring, and layoff facts remain a freshness limitation. |

The high n-gram counts come from repeated benchmark scaffolding and seed-rule phrasing, not exact scenario duplication. They are not treated as solved; they are the main reason this package is still labeled `0.1.0-interim`.

## Cost discipline

No new external API calls were used to materialize the Wednesday package. The interim build reuses local seed data, Week 10 traces, and checked-in Tenacious materials. Historic repo costs remain logged in `cost_log.md`, and no new τ²-Bench retail runs were performed for this Week 11 packaging pass.
