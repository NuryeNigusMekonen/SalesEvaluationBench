# Tenacious-Bench Seed 20

## Dataset Purpose

`tenacious_bench_seed_20.jsonl` is the first Week 11 seed dataset for a Tenacious-only sales-agent evaluation benchmark. It is designed to train and evaluate a judge or critic that catches Tenacious-specific failures in the Week 10 Conversion Engine: unsupported pricing, overclaimed prospect signals, generic outreach, wrong CRM/calendar actions, and unsafe reply handling.

This is not a general sales benchmark. It is a small, source-grounded seed set for preference tuning and evaluator design.

## Input Sources

The dataset uses Tenacious and Week 10 artifacts as task content:

- `docs/tenacious_sales_data/seed/pricing_sheet.md`
- `docs/tenacious_sales_data/seed/icp_definition.md`
- `docs/tenacious_sales_data/seed/style_guide.md`
- `docs/tenacious_sales_data/seed/bench_summary.json`
- `docs/tenacious_sales_data/seed/baseline_numbers.md`
- `docs/tenacious_sales_data/seed/email_sequences/`
- `docs/tenacious_sales_data/seed/discovery_transcripts/`
- `docs/tenacious_sales_data/policy/data_handling_policy.md`
- `docs/tenacious_sales_data/policy/acknowledgement.md`
- `docs/tenacious_sales_data/schemas/`
- Week 10/11 challenge briefs in `docs/`
- `agent/data/conversion_engine.db`
- `agent/data/traces.jsonl`
- selected `agent/data/outbox/` artifacts

Common and Path B papers were used only for methodology. No paper text is used as benchmark task content.

## Task Schema

Each JSONL row includes the required fields:

- `task_id`, `task_version`, `split`
- `source_type`, `source_file_or_artifact`
- `task_type`, `risk_focus`
- `prospect_context`, `hiring_signal_brief`, `competitor_gap_brief`
- `agent_output`, `judge_instruction`
- `expected_verdict`, `expected_reason`
- `rubric`
- `chosen`, `rejected`
- `label_confidence`, `requires_manual_review`

Rows also include provenance and contamination metadata such as `scenario_id`, `source_provenance`, and `split_contamination_notes`.

## Task Types

- `outreach_judgment`: judge a cold, follow-up, or re-engagement outreach draft.
- `reply_judgment`: judge a warm reply or objection-handling response.
- `crm_decision_judgment`: judge HubSpot or CRM state decisions.
- `calendar_decision_judgment`: judge booking and scheduling decisions.
- `enrichment_judgment`: judge classification, ICP, AI maturity, or signal interpretation.

## Risk Focus Labels

- `unsupported_pricing_or_scope_claim`: invented pricing, discounts, guarantees, unsupported staffing, or premature scope commitments.
- `overclaimed_signal_or_maturity_claim`: over-reading hiring signals, competitor gaps, AI maturity, or ICP segment rules.
- `generic_outreach_ungrounded`: outreach that is templated, internal-sounding, or not grounded in the prospect brief.
- `wrong_crm_hubspot_calendar_next_action`: incorrect opt-out, CRM, suppression, or scheduling behavior.
- `reply_escalation_or_objection_failure`: failure to hand off legal/pricing/reference requests or mishandled objections.

## Labeling Rules

Rows judge the supplied `agent_output`, not the prospect. The expected verdict is based on Tenacious source-of-truth files. `chosen` is the preferred critic response: it must be safer, more grounded, and more aligned with Tenacious rules. `rejected` is a plausible but flawed critic response that misses one clear failure mode. Labels avoid vague judgments and name the exact violated rule.

All current rows are marked `requires_manual_review: true` because this is a seed set intended for a later adjudication pass before training.

## Source-of-Truth Files

Primary business rules come from `pricing_sheet.md`, `icp_definition.md`, `style_guide.md`, `bench_summary.json`, `data_handling_policy.md`, and the email-sequence and transcript files. Week 10 traces and outbox artifacts provide realistic Conversion Engine behavior. The SQLite database was inspected locally to confirm prospect brief structure and synthetic provenance.

## How the common papers influenced this dataset

### Synthetic Data paper

The seed set uses synthetic company and person names for new scenarios, but the failure modes are anchored in Tenacious docs and Week 10 traces. The rows are targeted hard negatives rather than random synthetic examples, with explicit source citations and manual-review flags for quality control.

### Data Cards paper

The README documents purpose, composition, provenance, task schema, risks, intended use, limitations, and maintenance needs. This keeps the dataset understandable to future evaluators and prevents it from being mistaken for a broad sales benchmark.

### Data Contamination paper

Rows include `scenario_id` and split-contamination notes. Future train/dev/test partitioning should split by scenario, company, prospect, and source artifact, not by random row, so rewritten variants cannot leak into held-out evaluation.

### LLM-as-a-Judge paper

Each task includes structured judge instructions, expected verdict, expected reason, and rubric dimensions. The chosen/rejected pair is designed for a judge/critic that produces categorical, evidence-grounded decisions rather than a single vague score.

## How Path B papers influenced preference tuning

### DPO

Every row contains a clear chosen/rejected preference pair for the same prompt context. The chosen response catches the Tenacious-specific rule violation; the rejected response is fluent but misses or excuses it.

### SimPO

SimPO is the recommended primary method for this project because it is reference-free and practical for small adapter training. Pairs are written so the chosen response wins on correctness and grounding, not just length.

### Prometheus 2

The dataset follows a rubric-based judge-training pattern. Each row provides explicit criteria and verbal feedback so a future evaluator can learn Tenacious-specific judgments rather than generic helpfulness.

### Preference Leakage

The dataset records provenance and keeps manual review in the loop. Future generation, labeling, and evaluation should avoid using the same model family end to end, and human spot checks should cover every risk focus.

## Contamination Prevention Strategy

This seed release uses only the `seed` split. Future splits must keep all variants from the same `scenario_id`, `prospect_id`, company/domain, trace, or source artifact together. Paraphrases of the same scenario should not be placed into held-out evaluation. Before scaling, run exact duplicate checks and near-duplicate checks over normalized `agent_output`, `chosen`, `rejected`, and prospect metadata.

## Manual Review Plan

Manually review all 20 seed rows before training. For the next batch, sample at least 20% per risk focus, with full review for pricing, legal/escalation, and opt-out cases. Record reviewer disagreements and revise rubrics if agreement falls below 80% on any risk focus.

## Known Limitations

This is a seed set, not a full benchmark. It has no dev/test split yet, no inter-rater agreement pass, and no automated scoring script attached. Several tasks are hand-authored adversarial cases, so future scaling should add more trace-derived examples and balance pass/fail cases.

## Next Steps

Expand to 200-300 tasks, add pass cases, create scenario-safe train/dev/test splits, run duplicate and near-duplicate checks, write a full data card, and train a small SimPO judge with DPO as a baseline if time allows.
