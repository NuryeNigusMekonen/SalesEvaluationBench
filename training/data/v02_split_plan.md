# Tenacious-Bench v0.2 Split Plan

`training/data/tenacious_bench_v0_2_expansion_100.jsonl` has been split after the first-pass self-review in `reports/manual_review_v02_expansion_100.md`.

## Source Filter

- included rows: `100`
- filter: `reviewer_verdict=approve`
- excluded rows: `0`
- v0.1 held-out rows used: `0`

## Split Counts

- train: `70`
- dev: `15`
- held_out: `15`

## Split Rules Applied

Rows were grouped by `scenario_id` and explicit `metadata.semantic_family` labels before assignment. Near-duplicate templates were kept in one split, including:

- overclaimed funding/capacity assertions
- ambiguous overclaimed-signal review cases
- CRM auto-booking and channel-escalation cases
- generic follow-up and resource-note patterns
- reply escalation and legal/compliance handoff patterns
- pricing discount, capacity, and custom-scope boundaries

## Distribution

### Risk Focus

| split | generic_outreach_ungrounded | overclaimed_signal_or_maturity_claim | reply_escalation_or_objection_failure | unsupported_pricing_or_scope_claim | wrong_crm_hubspot_calendar_next_action |
|---|---:|---:|---:|---:|---:|
| train | 20 | 20 | 6 | 6 | 18 |
| dev | 3 | 5 | 2 | 1 | 4 |
| held_out | 2 | 5 | 2 | 3 | 3 |

### Expected Verdict

| split | fail | needs_human_review | pass |
|---|---:|---:|---:|
| train | 32 | 12 | 26 |
| dev | 6 | 3 | 6 |
| held_out | 7 | 5 | 3 |

## Generated Files

- `tenacious_bench_v0.2/train/tasks.jsonl`
- `tenacious_bench_v0.2/dev/tasks.jsonl`
- `tenacious_bench_v0.2/held_out/tasks.jsonl`
- `tenacious_bench_v0.2/README.md`
- `tenacious_bench_v0.2/summary.json`
- `training/data/v02_train_preferences.jsonl`
- `training/data/v02_dev_preferences.jsonl`
- `training/data/v02_test_preferences.jsonl`

## Validation Commands

```bash
python training/validate_v02_split.py
python training/convert_v02_tasks_to_preferences.py
python training/validate_v02_preferences.py
```
