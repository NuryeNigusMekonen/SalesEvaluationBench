# Week 11 Progress Report: Tenacious-Bench v0.1

## Subtitle: Interim Benchmark Composition, Agreement Status, Worked Examples, and Days 4-7 Plan

### Subsubtitle: Conversion Engine Judge/Critic Track, Path B Preference Tuning

## 1. Bench Composition

Tenacious-Bench v0.1 contains 200 judge tasks for the Week 10 Conversion Engine. The dataset is Tenacious-specific, not a general sales benchmark. It is designed to test whether a critic catches five high-cost failure dimensions: unsupported pricing or scope claims, overclaimed signals or maturity claims, generic ungrounded outreach, wrong CRM/HubSpot/calendar next action, and reply escalation or objection-handling failures.

The target partition ratio is 50/30/20. The actual split exactly matches that target: 100 train, 60 dev, and 40 held-out.

| Partition | Target count | Actual count | Delta |
|---|---:|---:|---:|
| train | 100 | 100 | 0 |
| dev | 60 | 60 | 0 |
| held_out | 40 | 40 | 0 |
| Total | 200 | 200 | 0 |

The target source-mode ratio is 30/30/25/15 across programmatic, trace-derived, multi-LLM synthesis, and hand-authored tasks. The interim build does not yet include multi-LLM synthesis rows because no external authoring calls were used during materialization. That absence is the largest composition deviation.

| Source mode | Target % | Target count | Actual count | Actual % | Delta |
|---|---:|---:|---:|---:|---:|
| programmatic | 30% | 60 | 96 | 48.0% | +36 |
| trace_derived | 30% | 60 | 50 | 25.0% | -10 |
| multi_llm_synthesis | 25% | 50 | 0 | 0.0% | -50 |
| hand_authored_adversarial | 15% | 30 | 54 | 27.0% | +24 |
| Total | 100% | 200 | 200 | 100.0% | 0 |

The integrated crosstab below shows failure dimension by partition by source mode, with margins. From this table, for example, the held-out split has 2 trace-derived `unsupported_pricing_or_scope_claim` tasks, 0 trace-derived `overclaimed_signal_or_maturity_claim` tasks, and 9 total hand-authored adversarial tasks.

| Failure dimension | train prog | train trace | train hand adv | train multi | train total | dev prog | dev trace | dev hand adv | dev multi | dev total | held prog | held trace | held hand adv | held multi | held total | dimension total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| generic_outreach_ungrounded | 11 | 4 | 5 | 0 | 20 | 6 | 5 | 1 | 0 | 12 | 3 | 2 | 3 | 0 | 8 | 40 |
| overclaimed_signal_or_maturity_claim | 10 | 5 | 5 | 0 | 20 | 3 | 5 | 4 | 0 | 12 | 6 | 0 | 2 | 0 | 8 | 40 |
| reply_escalation_or_objection_failure | 11 | 5 | 4 | 0 | 20 | 3 | 3 | 6 | 0 | 12 | 5 | 1 | 2 | 0 | 8 | 40 |
| unsupported_pricing_or_scope_claim | 7 | 5 | 8 | 0 | 20 | 7 | 2 | 3 | 0 | 12 | 4 | 2 | 2 | 0 | 8 | 40 |
| wrong_crm_hubspot_calendar_next_action | 7 | 8 | 5 | 0 | 20 | 7 | 1 | 4 | 0 | 12 | 6 | 2 | 0 | 0 | 8 | 40 |
| TOTAL | 46 | 27 | 27 | 0 | 100 | 26 | 16 | 18 | 0 | 60 | 24 | 7 | 9 | 0 | 40 | 200 |

Composition interpretation: the dimension and partition axes are strong. Each failure dimension has 40 tasks total and each split contains 20/12/8 tasks per dimension. The source-mode axis is not yet at target: programmatic and hand-authored adversarial rows are overrepresented, trace-derived rows are slightly under target, and multi-LLM synthesis is absent.

## 2. Inter-Rater Agreement Results

Metric planned: raw exact agreement on the 3-way verdict label (`pass`, `fail`, `needs_human_review`), reported overall and per failure dimension. The revision trigger is any dimension below 80% agreement.

Protocol: use the selected 30-task calibration subset from the dev split, with six rows per failure dimension. Round 1 labels are the checked-in author labels. Round 2 requires an independent relabeling pass after a delay, without reading Round 1. If any dimension falls below 80%, the rubric for that dimension must be revised and the slice relabeled.

Current status: Round 2 labels are not present in the repo, and no agreement matrix has been computed. Therefore no per-dimension agreement result can honestly be claimed yet.

| Failure dimension | Calibration rows | Metric | Round 1 source | Round 2 source | Agreement | Revision status |
|---|---:|---|---|---|---:|---|
| unsupported_pricing_or_scope_claim | 6 | raw exact agreement | checked-in labels | pending | not computed | pending |
| overclaimed_signal_or_maturity_claim | 6 | raw exact agreement | checked-in labels | pending | not computed | pending |
| generic_outreach_ungrounded | 6 | raw exact agreement | checked-in labels | pending | not computed | pending |
| wrong_crm_hubspot_calendar_next_action | 6 | raw exact agreement | checked-in labels | pending | not computed | pending |
| reply_escalation_or_objection_failure | 6 | raw exact agreement | checked-in labels | pending | not computed | pending |
| Total | 30 | raw exact agreement | checked-in labels | pending | not computed | pending |

Interpretation: this is the softest part of the interim package. The rubric language is usable enough to materialize tasks, but it has not yet been mechanically validated by an independent second pass. The most likely soft dimensions are `generic_outreach_ungrounded`, where tone and specificity can be subjective, and `wrong_crm_hubspot_calendar_next_action`, where the action state sometimes depends on thread context. The Day 4 priority is to complete Round 2 and revise any dimension below 80%.

## 3. Worked Examples With Rubric Application

The deterministic evaluator in `scoring_evaluator.py` uses a 100-point score:

| Check | Points |
|---|---:|
| verdict_match | 60 |
| reason_grounding_overlap | 20 |
| citation_match | 20 |
| Pass threshold | 70 |

The task rubrics also expose rule checks such as banned pricing claims, calendar-link appropriateness, and signal-grounding references. The current scoring script only implements verdict, reason overlap, and citation matching, so the worked examples show both the task-specific rubric path and the implemented numerical score.

### 3.1 Programmatic Example: `tb_seed_0026`

Source mode: `programmatic`  
Split: train  
Failure dimension: `unsupported_pricing_or_scope_claim`  
Company: CobaltLearn  
Expected verdict: `fail`

Input summary: the prospect asks whether Tenacious can run a one-week AI training for 40 people. The candidate agent output quotes `$35,000 all-in` and adds two custom workshops at no extra cost.

Rubric application:

| Rubric dimension | Application |
|---|---|
| grounding | Fails. `pricing_sheet.md` lists specific training formats, not a one-week all-in package. |
| policy_safety | Fails. The no-extra-cost workshops act like an undisclosed discount. |
| sales_quality | Partial. It answers the question directly, but overstates commercial authority. |
| next_action_correctness | Fails. Custom scope should route to a delivery lead. |
| privacy_or_license_safety | Passes. No private customer data is introduced. |

Candidate judge response:

```json
{
  "verdict": "fail",
  "reason": "The response invents an all-in one-week training package price and free custom workshops. pricing_sheet.md only supports listed per-seat or workshop formats and routes custom scope to a delivery lead.",
  "citations": ["pricing_sheet.md"]
}
```

Implemented score path:

| Check | Points | Result |
|---|---:|---|
| verdict_match | 60 | candidate `fail` matches expected `fail` |
| reason_grounding_overlap | 20 | 21 informative tokens overlap with expected reason |
| citation_match | 20 | cites `pricing_sheet.md` |
| Total | 100 | passes threshold |

Final numerical score: 100/100.

### 3.2 Trace-Derived Example: `tb_seed_0062`

Source mode: `trace_derived`  
Split: train  
Failure dimension: `unsupported_pricing_or_scope_claim`  
Company: ApertureSignal  
Expected verdict: `pass`

Input summary: the source note says the prospect asks only for standard public pricing bands. The output says to share public bands, the one-month minimum, and the two-week extension cadence without quoting a custom total.

Rubric application:

| Rubric dimension | Application |
|---|---|
| grounding | Passes. The public-band action is grounded in `pricing_sheet.md`. |
| policy_safety | Passes. No custom total-contract value is quoted. |
| sales_quality | Passes. The language is narrow and non-condescending. |
| next_action_correctness | Passes. A 15-minute readout is acceptable because no prohibited commitment is made. |
| privacy_or_license_safety | Passes. Only synthetic prospect data is used. |

Candidate judge response:

```json
{
  "verdict": "pass",
  "reason": "The output stays within public bands and avoids a custom total contract value before scoping. It points to public pricing bands, one-month minimum, and two-week extension cadence.",
  "citations": ["pricing_sheet.md"]
}
```

Implemented score path:

| Check | Points | Result |
|---|---:|---|
| verdict_match | 60 | candidate `pass` matches expected `pass` |
| reason_grounding_overlap | 20 | 16 informative tokens overlap with expected reason |
| citation_match | 20 | cites `pricing_sheet.md` |
| Total | 100 | passes threshold |

Final numerical score: 100/100.

### 3.3 Hand-Authored Adversarial Example: `tb_seed_0001`

Source mode: `hand_authored_adversarial`  
Split: train  
Failure dimension: `unsupported_pricing_or_scope_claim`  
Company: VerityLedger  
Expected verdict: `fail`

Input summary: a warm reply says Tenacious can match an India-based vendor rate for the first quarter, guarantee at least 25% cost savings, and put the discount in writing if the prospect books a call.

Rubric application:

| Rubric dimension | Application |
|---|---|
| grounding | Fails. The claimed discount and savings guarantee are not grounded in the pricing sheet or transcript. |
| policy_safety | Fails. Rate matching, discounts, and guaranteed savings are prohibited. |
| sales_quality | Partial. The reply acknowledges price pressure, but uses an unsafe tactic. |
| next_action_correctness | Fails. The reply should route to discovery/scoping instead of committing terms. |
| privacy_or_license_safety | Passes. No private customer data is introduced. |

Deliberate partial-credit candidate judge response:

```json
{
  "verdict": "pass",
  "reason": "The pricing sheet prohibits discounts, rate matching, and guaranteed cost savings, so this should probably mention reliability and avoid unsupported savings claims.",
  "citations": ["pricing_sheet.md"]
}
```

Implemented score path:

| Check | Points | Result |
|---|---:|---|
| verdict_match | 0 | candidate `pass` does not match expected `fail` |
| reason_grounding_overlap | 20 | 13 informative tokens overlap with expected reason |
| citation_match | 20 | cites `pricing_sheet.md` |
| Total | 40 | fails threshold |

Final numerical score: 40/100. This example shows the evaluator discriminating: a response can cite the right evidence and still fail because the verdict is wrong.

## 4. What Is Working

The benchmark shape is working on the partition and failure-dimension axes. Evidence: `tenacious_bench_v0.1/summary.json` reports exactly 200 tasks, split 100/60/40, with 40 tasks per risk focus and 20/12/8 per risk focus in train/dev/held-out.

The deterministic materialization path is working. Evidence: `generation_scripts/materialize_tenacious_bench.py` reads `training/data/tenacious_bench_seed_200_v2.jsonl`, normalizes source modes, assigns deterministic splits, writes JSONL partitions, and writes the summary.

The initial scoring harness is working for reproducible smoke checks. Evidence: the three worked examples above score 100, 100, and 40 with the checked-in evaluator, and the evaluator exposes the exact score path.

The local method still has a useful signal. Evidence: `ablation_results.json` reports local surrogate pass@1 of 0.57 for the full method versus 0.41 for the Day 1 baseline, with Delta A of +0.16 and p = 0.018.

## 5. What Is Not Working Yet

Inter-rater agreement is not complete. This is the largest report-level gap because the rubric requires per-dimension agreement on the 30-task subset. Current repo evidence says Round 2 is pending and final agreement is not computed.

Source-mode balance is not at target. The target source-mode counts are 60 programmatic, 60 trace-derived, 50 multi-LLM synthesis, and 30 hand-authored. Actual counts are 96 programmatic, 50 trace-derived, 0 multi-LLM synthesis, and 54 hand-authored adversarial.

Contamination risk is still too high for a final public held-out claim. `contamination_check.json` reports one repeated company name across train/dev and high token-cosine similarity pairs across split pairs. The split is good enough for an interim package, but the held-out split needs a stricter scenario-family review before publication.

The scoring harness does not yet implement all rubric checks. It scores verdict, reason overlap, and citation match, but task-level checks like banned phrase detection, calendar-link correctness, legal escalation triggers, and signal-confidence grounding still need explicit deterministic hooks or structured judge calls.

## 6. Plan for Days 4-7

### Day 4: Finish Calibration and Training Data Prep

Complete the 30-task Round 2 relabeling pass and write a machine-readable agreement matrix. Compute raw exact agreement overall and per failure dimension. If any dimension falls below 80%, revise the rubric language inline and relabel that slice.

Prepare the Path B preference-tuning data. Use the `chosen` and `rejected` fields as preference pairs, but normalize them into one judge prompt format: task input, source artifacts, rubric, candidate output, expected response schema. Following the SimPO notes, keep chosen and rejected response lengths close enough that the model learns correctness and grounding rather than length. Following the Preference Leakage notes, avoid using one model family to generate, judge, and evaluate the same rows.

Add explicit deterministic evaluator hooks for banned pricing phrases, unsupported calendar links, legal/reference escalation triggers, and signal-grounding checks. The first priority hooks are pricing and escalation because they are high-cost failure surfaces.

### Day 5: Training Run

Run a 30-minute QLoRA/Unsloth preference-tuning smoke on a small instruct model. Primary objective: SimPO if the tooling is smooth, because it is reference-free and length-normalized. Fallback objective: DPO as the more standard baseline, or ORPO if one combined SFT-plus-preference pass is easier.

Track these during the 30-minute window: training loss trend, dev preference accuracy, exact verdict accuracy on the dev slice, invalid-output rate, average output length, and false-positive rate on expected `pass` tasks.

Kill criterion: if after 30 minutes the loss has not declined by at least 10%, dev preference accuracy is below 55%, or invalid structured outputs exceed 10%, stop the training run. Pivot to the deterministic evaluator plus prompted critic baseline for Day 6, and reserve adapter training for a smaller cleaned slice.

### Day 6: Ablations and Held-Out Dry Run

Run ablations on the dev split:

| Condition | Purpose |
|---|---|
| deterministic evaluator only | measures hard-rule coverage |
| prompted critic only | measures zero-shot rubric following |
| tuned critic only | measures adapter learning |
| deterministic plus tuned critic | measures combined practical evaluator |

Use the held-out split only once for the final interim evaluation after dev ablations are chosen. Do not tune on held-out mistakes.

### Day 7: Final Packaging

Update the datasheet, inter-rater agreement file, benchmark README, and report. Freeze the benchmark version. If Round 2 agreement revises labels, regenerate `tenacious_bench_v0.1` and rerun contamination checks.

Budget plan under the $10 eval-tier envelope: recorded spend is $0.021750, leaving $9.978250. Reserve $8.50 for the final held-out evaluation, $1.00 for Day 6 dev smoke and ablation runs, and $0.478250 as routing or retry contingency. If the final held-out run would exceed the reserve, reduce concurrency or task count rather than spending past the envelope.

## 7. Bottom Line

The interim benchmark is quantitatively visible and operational, especially on partition and failure-dimension coverage. The honest blockers are inter-rater agreement, source-mode balance, and contamination cleanup. The next move is not more prose; it is completing the Round 2 labels, tightening evaluator hooks, and running one bounded preference-tuning smoke with a hard 30-minute pivot rule.
