# Week 11 v0.2 Expansion Report

## Why v0.2 was created

Tenacious-Bench v0.2 was created as a seed-only expansion that targets the weakest areas from v0.1 without modifying the frozen v0.1 benchmark or the existing trained adapter. The v0.1 results were strong overall, but the held-out set was weakest on `overclaimed_signal_or_maturity_claim` at 75%, and dev was weakest on `wrong_crm_hubspot_calendar_next_action` at 83.33%.

## How style guide v2 was used

The expansion uses `docs/Tenacious Style Guide and 12 Good-Bad Examples v2.md` as a pattern source for tone markers, formatting constraints, banned phrases, channel rules, pre-flight checks, good/bad draft patterns, tone-preservation scoring, the LinkedIn-roast test, and outreach decision flow. The generated rows are synthetic variants; they do not copy long example bodies from the guide.

## Dataset

- Dataset file: `training/data/tenacious_bench_v0_2_expansion_100.jsonl`
- Rows: 100
- Split state: `seed` only
- Manual review rows: 100
- Existing v0.1 benchmark: not modified
- Existing adapter: not modified
- Semantic repair: `risk_tags` now identify the scenario family, while `actual_failure_modes` records what the output really contains for that row

## Distribution By Risk Focus

- `generic_outreach_ungrounded`: 25
- `overclaimed_signal_or_maturity_claim`: 30
- `reply_escalation_or_objection_failure`: 10
- `unsupported_pricing_or_scope_claim`: 10
- `wrong_crm_hubspot_calendar_next_action`: 25

## Distribution By Risk Tags

- `banned_phrase_violation`: 5
- `bench_language_external`: 13
- `channel_rule_violation`: 25
- `cold_attachment_violation`: 10
- `directness_failure`: 20
- `fake_urgency_or_discount`: 3
- `grounding_failure`: 23
- `honesty_failure`: 26
- `linkedin_roast_risk`: 11
- `multi_ask_violation`: 14
- `non_condescending_failure`: 9
- `professionalism_failure`: 20
- `reengagement_without_new_content`: 12
- `signal_fabrication`: 12
- `word_count_violation`: 8

## Distribution By Actual Failure Modes

- `ambiguous_channel_state`: 10
- `banned_phrase_violation`: 6
- `bench_language_external`: 4
- `channel_rule_violation`: 13
- `cold_attachment_violation`: 6
- `custom_pricing_review_needed`: 3
- `directness_failure`: 6
- `fake_urgency_or_discount`: 1
- `grounding_failure`: 21
- `honesty_failure`: 15
- `legal_escalation_needed`: 7
- `multi_ask_violation`: 3
- `non_condescending_failure`: 6
- `professionalism_failure`: 5
- `reengagement_without_new_content`: 5
- `signal_fabrication`: 5
- `weak_signal_review_needed`: 10

## Distribution By Task Type

- `calendar_decision_judgment`: 6
- `channel_policy_judgment`: 15
- `crm_decision_judgment`: 10
- `enrichment_judgment`: 14
- `outreach_judgment`: 17
- `reply_judgment`: 21
- `tone_preservation_judgment`: 17

## Distribution By Expected Verdict

- `fail`: 45
- `needs_human_review`: 20
- `pass`: 35

## Validation Result

`python3 training/validate_v02_expansion.py` should confirm 100 valid JSONL rows, unique task IDs, seed-only split values, `.example` domains, manual-review gating on every row, non-empty `risk_tags`, verdict-consistent `actual_failure_modes`, no duplicate `agent_output` values, no copied long style-guide example bodies, and v2 style-guide source grounding.

## Contamination Controls

The expansion uses new IDs `tb_v02_0001` through `tb_v02_0100`, synthetic company names, `.example` domains, and seed-only split assignment. Each row includes `split_contamination_notes` instructing future split creation to keep near-duplicate scenario families together. The old v0.1 held-out set must remain sealed and must not be used for tuning the next judge.

## Manual Review Plan

All 100 rows have `requires_manual_review: true`. The adjudication worksheet is `reports/manual_review_v02_expansion_100.md`. Reviewers should verify the expected verdict, the `risk_tags`, the `actual_failure_modes`, and the source grounding before any row is promoted into train/dev/new-held-out splits. Ambiguous rows should either be revised or dropped before conversion to preference pairs.

## Next Training Use

Use v0.2 only after manual review and fresh split creation. The next training run should emphasize tone preservation, signal overclaiming, CRM/calendar/channel action correctness, banned phrases, LinkedIn-roast risk, bench overcommitment, and pricing/scope handoff. Do not tune on the old v0.1 held-out set; use a fresh v0.2 held-out from new scenario families.
