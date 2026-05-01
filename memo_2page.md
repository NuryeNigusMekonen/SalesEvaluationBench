# Tenacious Decision Memo

To: Tenacious CEO and CFO  
Date: May 1, 2026  
Status: Week 11 final memo

## Page 1 - The Decision

### Executive summary (3 sentences)

Tenacious-Bench held-out-style evaluation shows the trained critic improving pass@1 from 0.41 to 0.57 (Delta A +0.16, 95% CI +0.03 to +0.29), with significance from a two-proportion z-test (p=0.018; n=100 local held-out-style tasks). Against a no-training prompt-engineered comparator on the same Qwen2.5-3B backbone and the same PASS/FAIL/NEEDS_HUMAN_REVIEW intervention shape, pass@1 is 0.53, so Delta B is +0.04 and small. Recommendation: deploy with caveat, as a guarded production gate for one segment now, with strict monitoring and rollback criteria.

### Decision evidence

- Delta A (headline): 0.57 - 0.41 = +0.16; 95% CI for lift is +0.03 to +0.29; test: two-proportion z-test, p=0.018.
- Delta B (honest comparator): trained critic 0.57 vs prompt-engineered no-training comparator 0.53 on the same backbone and intervention shape; Delta B = +0.04.
- Honesty note on Delta B: positive but modest; this supports "training helps," but not a claim that prompting alone is insufficient.

### Cost per task and operating implication

- With trained component (full method): $0.026 per task, p95 latency 4.52s.
- Without trained component (Day 1 baseline): $0.024 per task, p95 latency 4.21s.
- No-training prompt comparator: $0.029 per task, p95 latency 5.11s.
- Implication: trained gating adds about $0.002/task vs Day 1 but is cheaper than the no-training prompt comparator and improves quality, so it is economically reasonable for a guarded rollout.

### Production recommendation

Recommendation category: deploy with caveat.

Deployment conditions before expansion beyond the pilot:

1. Run a 14-day pilot on Segment 2 only.
2. Keep audited commercial-safety fail rate at or below baseline +3 percentage points (3pp matches the lower bound of Delta A).
3. Keep mean cost per task at or below $0.03.
4. Keep opt-out rate increase below +1pp vs pre-launch baseline.
5. If any condition fails, do not expand; remain on limited pilot until corrected.

## Page 2 - The Skeptic's Appendix

### Four Tenacious-Bench v0.1 coverage gaps and v0.2 additions

1. Gap: account-level multi-thread consistency has zero tasks in v0.1.  
   v0.2 addition: account-graph tasks with two or more contacts from one company, scored for cross-thread narrative consistency.
2. Gap: signal freshness decay between enrichment time and send time has zero tasks in v0.1.  
   v0.2 addition: time-shifted fixtures with timestamped evidence and stale-signal contradiction probes.
3. Gap: procurement and legal redline handling has zero tasks in v0.1.  
   v0.2 addition: reply tasks with MSA/security-questionnaire snippets requiring correct human-handoff decisions.
4. Gap: seniority-calibrated tone under objection pressure has zero tasks in v0.1.  
   v0.2 addition: persona partitions (CTO, VP Eng, Procurement) with role-specific tone rubrics and objection probes.

### Public-signal lossiness in ground truth

A concrete lossiness mechanism is hiring-signal lag: public job postings and leadership updates often trail real internal priorities, so ground-truth labels can reward conservative language even when stronger private-context personalization would be correct. This systematically over-rewards cautious hedging and under-rewards accurate but higher-specificity outreach, which likely compresses the measured lift on tasks that require timely, account-specific confidence.

### One unresolved training failure

Unresolved training artifact: channel-policy judgment remains weak after training, especially on "auto-book calendar before explicit confirmation" patterns. On current eval artifacts, this slice is 1/3 on v0.2 dev and 0/1 on v0.2 held-out channel-policy tasks; I tried rubric normalization and deterministic decoding but did not remove the failure. Next step is targeted hard-negative oversampling for channel-policy rows before any broader deployment.

### Kill-switch trigger for production

Trigger condition: in any rolling 7-day window, if audited commercial-safety false negatives exceed 5% on high-risk sends (for example, 2+ misses in a 40-thread audit) or if total commercial-safety incident rate rises more than 3pp above pre-launch baseline, disable the trained component immediately. Action: revert to the pre-trained-component pipeline (rule gates + mandatory human review for high-risk classes) within the same on-call window. Threshold rationale: +3pp is the lower bound of the measured Delta A lift, so performance worse than that means the production benefit signal is no longer credible.
