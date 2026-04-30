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
- Semantic repair: `risk_tags` now describe scenario families and `actual_failure_modes` now describe the concrete row outcome

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

- `ambiguous_channel_state`: 7
- `banned_phrase_violation`: 6
- `bench_language_external`: 4
- `channel_rule_violation`: 13
- `cold_attachment_violation`: 6
- `custom_pricing_review_needed`: 4
- `directness_failure`: 6
- `fake_urgency_or_discount`: 1
- `grounding_failure`: 21
- `honesty_failure`: 15
- `legal_escalation_needed`: 4
- `multi_ask_violation`: 3
- `non_condescending_failure`: 6
- `professionalism_failure`: 5
- `reengagement_without_new_content`: 5
- `signal_fabrication`: 5
- `weak_signal_review_needed`: 7

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

`python3 training/validate_v02_expansion.py` passed. The validator now checks row count, schema fields, `.example` domains, source grounding, exact verdict distributions, `risk_tags`, verdict-aware `actual_failure_modes`, duplicate `agent_output`, duplicate `chosen`, duplicate `rejected`, `expected_reason` repeated more than 3 times, and rejected-core phrases repeated more than 5 times.

## Preference Diversity Repair

The high-priority repeated preference clusters were repaired before any split work. The main changes were:

- pass rows in `tb_v02_0018` to `tb_v02_0025` now carry row-specific wrong critiques tied to the exact signal logic being misread
- review rows in `tb_v02_0026` to `tb_v02_0030` now separate weak-signal, confidence, source-support, segment, and channel-path uncertainty
- CRM and calendar rows in `tb_v02_0043` to `tb_v02_0055` now test distinct operational mistakes instead of repeating one conservative-workflow rationale
- resource-touch and no-signal rows in `tb_v02_0067` to `tb_v02_0080` now name the exact visible signal, the exact missing corroboration, and the exact allowed outreach action
- escalation rows in `tb_v02_0084` to `tb_v02_0090` now distinguish DPA, MSA, healthcare proof, named references, sector proof, combined pricing-plus-legal, and ambiguous security-packet review
- pricing rows in `tb_v02_0093` to `tb_v02_0100` now distinguish public bands, one-month minimum, custom totals, multi-phase scope, volume pricing, urgent pricing pressure, unsupported capacity, and delivery-lead routing

This repair improved pair diversity without changing task IDs, row count, split values, risk-focus distribution, expected-verdict distribution, or source grounding.

## Contamination Controls

The expansion uses new IDs `tb_v02_0001` through `tb_v02_0100`, synthetic company names, `.example` domains, and seed-only split assignment. Each row includes `split_contamination_notes` instructing future split creation to keep near-duplicate scenario families together. The old v0.1 held-out set must remain sealed and must not be used for tuning the next judge.

## Manual Review Plan

All 100 rows have `requires_manual_review: true`. The adjudication worksheet is `reports/manual_review_v02_expansion_100.md`. Reviewers should verify the expected verdict, the `risk_tags`, the `actual_failure_modes`, and the source grounding before any row is promoted into train/dev/new-held-out splits. Ambiguous rows should either be revised or dropped before conversion to preference pairs.

## Next Training Use

Use v0.2 only after manual review and fresh split creation. The next training run should emphasize tone preservation, signal overclaiming, CRM/calendar/channel action correctness, banned phrases, LinkedIn-roast risk, bench overcommitment, and pricing/scope handoff. Do not tune on the old v0.1 held-out set; use a fresh v0.2 held-out from new scenario families.
