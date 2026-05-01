# Draft GitHub Issue (Community Engagement)

Title: Tenacious-specific evaluation gaps not captured by retail workflow benchmarks

Hello maintainers, and thanks for the benchmark work.

I’m sharing a Tenacious-specific benchmark extension from my evaluation cycle because I observed recurring failure classes that are high-cost in sales automation but underweighted in retail-style workflow scoring.

## What I found

In my trace/probe evidence, the biggest failures were not basic tool-use errors. They were boundary failures:

1. Unsupported pricing/scope claims in warm replies
2. Overconfident interpretation of weak public signals
3. Wrong CRM/calendar/SMS next-action decisions for thread state
4. Missing human escalation on legal/commercial triggers
5. Generic outreach that ignores required signal grounding

These behaviors can be fluent and operationally “complete” while still being unsafe or commercially incorrect.

## What I built

I created and published **Tenacious-Bench v0.1**:

- Dataset URL: https://huggingface.co/datasets/Nurye/tenacious_bench_v0.1
- 200 tasks, split 100/60/40 (train/dev/held-out)
- Five risk-focus families balanced at 40 tasks each
- Machine-checkable task schema with expected verdict/rationale
- Preference-ready chosen/rejected pairs for critic training
- Contamination and inter-rater artifacts included

## Why this may be useful to your roadmap

The extension is not trying to replace your benchmark. It is a domain-specific complement showing how to score:

- policy-compliant restraint under uncertainty
- explicit human-handoff correctness
- source-grounding quality for high-stakes commercial claims

If useful, I can open a follow-up with a compact adapter layer proposal mapping these risk dimensions to your existing task taxonomy.

Thanks again for maintaining the benchmark and leaderboard infrastructure.
