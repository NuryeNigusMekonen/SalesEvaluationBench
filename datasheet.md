# Datasheet: Tenacious-Bench v0.1 Interim

## Telescopic view

This datasheet follows the Gebru et al. datasheets framing and Pushkarna et al. data-card lifecycle framing: it documents purpose, composition, provenance, transformation, intended use, risks, and maintenance rather than only listing fields.

Tenacious-Bench v0.1 is a Tenacious-specific evaluation dataset for judging Week 10 sales-agent behavior. It is not a general sales benchmark and it is not a generic LLM helpfulness set. Its purpose is to measure whether a judge or critic can correctly identify five high-cost failure surfaces in the Tenacious workflow:

- unsupported pricing or scope claims
- overclaimed signals or maturity claims
- generic or ungrounded outreach
- wrong CRM, HubSpot, or calendar next actions
- reply escalation or objection-handling failures

The interim release contains `200` tasks split into `100 train`, `60 dev`, and `40 held_out`.

Dataset license: `Limited License — TRP1 Week 10 Seed Materials`, inherited from
`docs/tenacious_sales_data/LICENSE.md`. This fits the interim Tenacious-Bench package
because the benchmark is local, Tenacious-specific, and derived from challenge-provided
Tenacious materials that should not be redistributed as a generic public sales corpus.
Before any public Hugging Face release, the dataset needs Tenacious approval or a
sanitized public license because the current license is intentionally challenge-limited.

## 1. Motivation

Week 10 established that the Tenacious agent can enrich prospects, route outreach, and handle replies, but the repo evidence also shows a repeated pattern of policy-boundary mistakes: weak public signals become strong claims, pricing questions continue without explicit delivery-lead escalation, and workflow state transitions are sometimes correct and sometimes not. Public retail-style benchmarks do not grade those risks. Tenacious-Bench exists to evaluate those Tenacious-specific boundaries directly.

## 2. Composition

### Core facts

- Dataset name: `Tenacious-Bench v0.1`
- Version: `0.1.0-interim`
- Total tasks: `200`
- Splits: `100 train`, `60 dev`, `40 held_out`
- Task families: `5`
- Task types: `40` each of `reply_judgment`, `outreach_judgment`, `enrichment_judgment`, `crm_decision_judgment`, and `calendar_decision_judgment`
- Source modes:
  - `96` programmatic
  - `50` trace-derived
  - `54` hand-authored adversarial
- Difficulty:
  - `80` `T1_easy`
  - `61` `T2_medium`
  - `59` `T3_hard`
- Expected verdicts:
  - `90 fail`
  - `70 pass`
  - `40 needs_human_review`

### Task counts by failure dimension

| Failure dimension | Train | Dev | Held out | Total |
|---|---:|---:|---:|---:|
| `unsupported_pricing_or_scope_claim` | 20 | 12 | 8 | 40 |
| `overclaimed_signal_or_maturity_claim` | 20 | 12 | 8 | 40 |
| `generic_outreach_ungrounded` | 20 | 12 | 8 | 40 |
| `wrong_crm_hubspot_calendar_next_action` | 20 | 12 | 8 | 40 |
| `reply_escalation_or_objection_failure` | 20 | 12 | 8 | 40 |

### What one row contains

Each row includes:

- structured prospect context
- a hiring-signal brief
- a competitor-gap brief
- the original Week 10-style agent output to judge
- a task-specific judge instruction
- the expected verdict
- the expected grounded reason
- a rubric
- `chosen` and `rejected` preference critiques

### What the dataset does not contain

- real customer data
- live CRM records
- legal approvals
- calibrated conversion outcomes
- a claim that this covers all Tenacious failure modes

## 3. Collection and generation process

### Upstream sources

The interim package is built only from checked-in local materials:

- Week 10 traces in `agent/data/traces.jsonl`
- outbox artifacts in `agent/data/outbox/`
- seed business-rule files in `docs/tenacious_sales_data/seed/`
- policy files in `docs/tenacious_sales_data/policy/`
- Week 10 probes in `probes/`
- the existing seed datasets in `training/data/`

### Authoring modes

The Wednesday package uses three live authoring modes and reserves the fourth for the final release:

- trace-derived tasks from Week 10 traces and reply-decision artifacts
- programmatic tasks from templates grounded in seed rules
- hand-authored adversarial tasks from transcripts and failure analysis

`multi_llm_synthesis` is intentionally documented in the schema but not yet populated in this interim build because no external authoring calls were made during materialization.

Concrete authoring examples:

- Trace-derived: `tb_seed_0071` turns a Week 10-style CRM decision trace for `ApertureBridge` into a judge task about whether the next action obeys pricing and workflow constraints.
- Programmatic: `tb_seed_0003` uses the seed pricing and bench rules to create a `HelioCart` outreach judgment where the candidate critic must reject an unsupported scope/capacity claim.
- Hand-authored adversarial: `tb_seed_0073` is a deliberately tricky CRM-action case for `ApertureWorks`, written from failure-analysis patterns so a fluent but unsafe decision looks superficially plausible.
- Multi-LLM synthesis: no row is included yet; the planned mode is to have one model family author a new adversarial task, a separate model family judge it, and the local filter accept it only if it passes the executable thresholds in `generation_scripts/materialize_tenacious_bench.py`.

### Layered detail

Periscopic:
The current release is the materialized form of `training/data/tenacious_bench_seed_200_v2.jsonl`, not a fresh generation run.

Microscopic:
Every row carries `source_file_or_artifact`, `source_provenance`, `label_confidence`, and `split_contamination_notes` so reviewers can trace it back to a local artifact family.

## 4. Preprocessing and transformation

The benchmark package is produced by `generation_scripts/materialize_tenacious_bench.py`.

That script:

- reads `training/data/tenacious_bench_seed_200_v2.jsonl`
- maps `source_type` to benchmark-facing `source_mode`
- uses random seed `20260429` for reproducible judge-family routing
- assigns a judge family through model-family rotation so a generator family cannot judge its own rows
- applies executable judge-dimension thresholds of `4/5` for coherence, grounding, and rubric clarity
- removes exact duplicate chosen/rejected preference pairs before splitting
- assigns deterministic split labels
- derives a simple difficulty tier
- writes normalized benchmark rows into `tenacious_bench_v0.1/train`, `dev`, and `held_out`
- writes `tenacious_bench_v0.1/summary.json`

No new model inference is required for this materialization step.

## 5. Labeling and validation

### Label shape

The benchmark is judge-oriented. Each task asks whether a candidate critic or judge can classify the embedded sales-agent output as `pass`, `fail`, or `needs_human_review`.

### Validation artifacts

- upstream seed validation: `training/validate_tenacious_bench.py`
- materialized split summary: `tenacious_bench_v0.1/summary.json`
- contamination report: `contamination_check.json`
- inter-rater protocol: `inter_rater_agreement.md`

### Current inter-rater state

The interim package includes a selected 30-task dev subset for the two-pass inter-rater exercise. Round 1 is represented by the checked-in author labels; Round 2 is still pending. Because of that, this is a pre-publication dataset state, not the final adjudicated public release.

## 6. Uses

### Intended uses

- training a small Tenacious-specific judge or critic
- evaluating whether a judge catches unsafe pricing, weak-signal overclaiming, bad workflow actions, and missing human escalations
- supporting Week 11 ablations on Path B

### Out-of-scope uses

- evaluating general sales quality across industries
- making employment, compensation, or account-prioritization decisions
- treating the dataset as legal or compliance advice
- claiming live reply-rate or revenue lift

## 7. Distribution

This interim dataset is currently local to the repo and packaged for the Wednesday GitHub submission. It is not yet the final public Hugging Face release. Before public release, the held-out split needs another de-duplication pass and the inter-rater exercise must be completed.

## 8. Maintenance

Planned next steps:

- complete round-two labeling and rubric revision if agreement is below threshold
- reduce paraphrase-family leakage inside synthetic template expansions
- add multi-LLM-synthesis rows with model-family separation between generation and judging
- freeze the public release candidate and publish with a full Hugging Face card

Versioning rule:
Any change to task text, labels, splits, or contamination logic should trigger a version bump and an update to this datasheet.

## 9. Risks and limitations

- The current held-out split still shows template-family similarity under token-cosine fallback checks.
- One repeated company name appears across splits.
- The benchmark is heavily Tenacious-specific and should not be generalized to “sales agents” broadly.
- It is a judgment benchmark built from static seed materials and Week 10 traces, so public-signal freshness is limited by those local snapshots.
- The evaluator is deterministic and useful for reproducibility, but it is not a substitute for final human review on ambiguous legal or commercial cases.
