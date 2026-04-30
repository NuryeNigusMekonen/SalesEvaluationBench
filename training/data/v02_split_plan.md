# Tenacious-Bench v0.2 Split Plan

`training/data/tenacious_bench_v0_2_expansion_100.jsonl` is a seed-only expansion. It must be manually reviewed before any training split is created.

After review, create fresh v0.2 train/dev/new-held-out splits from the v0.2 scenario families. Do not tune on the old v0.1 held-out set; keep it sealed for historical reporting only. Do not place near-duplicate variants, same scenario families, same company patterns, or same tone/channel failure templates across different splits.

The new held-out split should come from v0.2 scenario families that are not represented by near-duplicates in train or dev. Prioritize the weak v0.1 areas: overclaimed signal/maturity claims, CRM/calendar/channel decisions, generic outreach/tone preservation, LinkedIn-roast risk, and unsupported pricing/capacity claims.

Recommended post-review flow:

1. Resolve all manual review comments and remove ambiguous labels.
2. Group rows by `scenario_id`, `risk_focus`, `tone_failure_modes`, and source pattern.
3. Assign whole groups to train/dev/new-held-out.
4. Validate no old v0.1 held-out rows or near-duplicates were used for tuning.
5. Convert only approved v0.2 split rows into preference pairs for the next judge-adapter run.
