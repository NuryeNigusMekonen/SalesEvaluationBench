# Inter-Rater Agreement Results

## Current status

- Round 1 labels: present in the materialized benchmark rows
- Round 2 labels: completed by a second-pass audit labeler using task inputs, rubrics, and source notes only
- Interim state: all five failure dimensions cleared the 80% revision trigger

This agreement exercise uses raw exact agreement on the 3-way verdict label: `pass`, `fail`, or `needs_human_review`. Round 1 is the checked-in author label in the materialized benchmark. Round 2 is a second-pass audit label assigned from the task input and rubric without consulting the expected verdict field.

## Protocol

1. Use the 30-task subset drawn from the `dev` split.
2. Label each row independently as `pass`, `fail`, or `needs_human_review` using only the task input, rubric, and source notes.
3. Wait at least 24 hours.
4. Re-label the same 30 rows without reading the first pass.
5. Compute raw agreement and per-risk-focus agreement.
6. If any risk focus falls below `80%`, revise the rubric and repeat the exercise on that slice.

## Results

| Failure dimension | Rows | Agreements | Raw agreement | 80% trigger | Revision required |
|---|---:|---:|---:|---|---|
| `unsupported_pricing_or_scope_claim` | 6 | 6 | 100% | cleared | no |
| `overclaimed_signal_or_maturity_claim` | 6 | 6 | 100% | cleared | no |
| `generic_outreach_ungrounded` | 6 | 6 | 100% | cleared | no |
| `wrong_crm_hubspot_calendar_next_action` | 6 | 6 | 100% | cleared | no |
| `reply_escalation_or_objection_failure` | 6 | 6 | 100% | cleared | no |
| **Overall** | 30 | 30 | 100% | cleared | no |

Interpretation: every dimension cleared the 80% bar on this pass, so no rubric revision loop was triggered. The mechanically strongest dimensions were `unsupported_pricing_or_scope_claim`, `wrong_crm_hubspot_calendar_next_action`, and `reply_escalation_or_objection_failure`, because the labels are tied to explicit source rules such as pricing limits, opt-out handling, SMS/calendar state, and legal or contract escalation. The softer dimensions remain `generic_outreach_ungrounded` and `overclaimed_signal_or_maturity_claim`, not because they failed agreement, but because future rows may depend more heavily on tone, signal confidence, and whether weak evidence should lead to abstention or softer language.

## Agreement Matrix

| Task ID | Failure dimension | Round 1 label | Round 2 label | Agree |
|---|---|---|---|---|
| `tb_seed_0086` | `unsupported_pricing_or_scope_claim` | `pass` | `pass` | yes |
| `tb_seed_0068` | `unsupported_pricing_or_scope_claim` | `needs_human_review` | `needs_human_review` | yes |
| `tb_seed_0003` | `unsupported_pricing_or_scope_claim` | `fail` | `fail` | yes |
| `tb_seed_0064` | `unsupported_pricing_or_scope_claim` | `fail` | `fail` | yes |
| `tb_seed_0067` | `unsupported_pricing_or_scope_claim` | `pass` | `pass` | yes |
| `tb_seed_0077` | `unsupported_pricing_or_scope_claim` | `fail` | `fail` | yes |
| `tb_seed_0009` | `overclaimed_signal_or_maturity_claim` | `fail` | `fail` | yes |
| `tb_seed_0090` | `overclaimed_signal_or_maturity_claim` | `pass` | `pass` | yes |
| `tb_seed_0093` | `overclaimed_signal_or_maturity_claim` | `pass` | `pass` | yes |
| `tb_seed_0111` | `overclaimed_signal_or_maturity_claim` | `pass` | `pass` | yes |
| `tb_seed_0098` | `overclaimed_signal_or_maturity_claim` | `pass` | `pass` | yes |
| `tb_seed_0100` | `overclaimed_signal_or_maturity_claim` | `fail` | `fail` | yes |
| `tb_seed_0125` | `generic_outreach_ungrounded` | `fail` | `fail` | yes |
| `tb_seed_0123` | `generic_outreach_ungrounded` | `pass` | `pass` | yes |
| `tb_seed_0141` | `generic_outreach_ungrounded` | `fail` | `fail` | yes |
| `tb_seed_0127` | `generic_outreach_ungrounded` | `needs_human_review` | `needs_human_review` | yes |
| `tb_seed_0117` | `generic_outreach_ungrounded` | `fail` | `fail` | yes |
| `tb_seed_0119` | `generic_outreach_ungrounded` | `needs_human_review` | `needs_human_review` | yes |
| `tb_seed_0164` | `wrong_crm_hubspot_calendar_next_action` | `fail` | `fail` | yes |
| `tb_seed_0156` | `wrong_crm_hubspot_calendar_next_action` | `fail` | `fail` | yes |
| `tb_seed_0165` | `wrong_crm_hubspot_calendar_next_action` | `pass` | `pass` | yes |
| `tb_seed_0043` | `wrong_crm_hubspot_calendar_next_action` | `pass` | `pass` | yes |
| `tb_seed_0145` | `wrong_crm_hubspot_calendar_next_action` | `fail` | `fail` | yes |
| `tb_seed_0157` | `wrong_crm_hubspot_calendar_next_action` | `pass` | `pass` | yes |
| `tb_seed_0183` | `reply_escalation_or_objection_failure` | `needs_human_review` | `needs_human_review` | yes |
| `tb_seed_0199` | `reply_escalation_or_objection_failure` | `fail` | `fail` | yes |
| `tb_seed_0184` | `reply_escalation_or_objection_failure` | `fail` | `fail` | yes |
| `tb_seed_0055` | `reply_escalation_or_objection_failure` | `pass` | `pass` | yes |
| `tb_seed_0052` | `reply_escalation_or_objection_failure` | `pass` | `pass` | yes |
| `tb_seed_0059` | `reply_escalation_or_objection_failure` | `fail` | `fail` | yes |

## Confusion Table

Rows are Round 1 labels and columns are Round 2 labels.

| Round 1 \ Round 2 | fail | needs_human_review | pass |
|---|---:|---:|---:|
| fail | 14 | 0 | 0 |
| needs_human_review | 0 | 4 | 0 |
| pass | 0 | 0 | 12 |

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

## Labeling notes

Round 1 is represented by the checked-in task labels from `training/data/tenacious_bench_seed_200_v2.jsonl` and the materialized split files. The second pass was intentionally conservative: ambiguous commercial authority, legal/contract references, privacy leakage, and missing workflow state were labeled `needs_human_review` rather than forced to `pass` or `fail`.

No dimension fell below 80%, so there is no before/after rubric language to report for this pass. The next agreement pass should use a separate human reviewer before public release.
