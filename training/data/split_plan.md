# Tenacious-Bench Split Plan

## Why Random Row Split Is Unsafe

Random row splitting is unsafe because many tasks share the same scenario, prospect, company, source artifact, or failure pattern. A paraphrased pricing failure from one prospect in training and a near-identical pricing failure from the same prospect in test would inflate evaluator performance. The judge could learn the row template or company context rather than the Tenacious rule.

## Split Keys

Future split assignment should use grouped keys in this order:

1. `scenario_id`: keep all variants of the same underlying task together.
2. `prospect_id`: keep all tasks about one synthetic prospect together.
3. Company name and company domain: keep company-level variants together even if prospect IDs differ.
4. `source_file_or_artifact`: keep trace/outbox artifacts from the same source family together when they describe the same scenario.

If any of these keys conflict, choose the most conservative grouping: all related rows go into the same split.

## Avoiding Paraphrase Leakage

Do not place rewritten variants of the same task into different splits. Paraphrase leakage includes changed names with the same facts, reordered email content, the same pricing claim with different numbers, or the same CRM state expressed in different words. Before sealing dev/test, run exact matching on normalized text and a near-duplicate check over `agent_output`, `chosen`, `rejected`, `expected_reason`, and scenario metadata.

Human review should flag rows that feel like restatements of existing held-out tasks even when automated checks pass. When in doubt, group the rows together.

## Future Dynamic Task Generation

Dynamic generation can refresh evaluation coverage, but generated tasks must be anchored to current Tenacious source-of-truth docs and separately reviewed. Store generator prompt version, source artifact, scenario family, generation date, reviewer, and labeler. Never generate new training rows from sealed held-out prompts. For dynamic smoke tests, generate a small post-training slice after model training is complete, review it manually, and keep it out of preference tuning.

## Proposed Split Sizes for 200-300 Tasks

Use scenario-safe grouped splits rather than exact row-level random ratios:

- Training: 50%, about 100-150 tasks.
- Public dev: 30%, about 60-90 tasks.
- Sealed held-out: 20%, about 40-60 tasks.

Keep every risk focus represented in each split, but do not break scenario groups to force perfect balance. If a large scenario group would skew a split, move the whole group and document the imbalance in the data card.

## Seed Set Handling

The current 20-row seed set remains `split: seed`. It should be manually reviewed, edited if needed, and then used as authoring guidance. Do not automatically promote these rows into train/dev/test until scenario grouping and duplicate checks are implemented.
