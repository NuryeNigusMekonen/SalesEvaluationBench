# Tenacious Decision Memo

*To: Tenacious CEO and CFO*  
*Date: April 25, 2026*  
*Status: Draft*
##sqlitebrowser 
## Page 1: The Decision

We built an email-first conversion engine that enriches synthetic prospects from public signals, drafts signal-grounded outreach, enforces honesty and bench guardrails, and routes qualified conversations toward HubSpot and Cal.com with human escalation where needed. In the stored preview run, the repo records a preview cost of `$0.000178` per file-defined qualified lead and a `0%` synchronous stalled-thread rate in the synthetic trace slice against the current Tenacious manual baseline of `30–40%`. Recommendation: run a `30-day Segment 2 pilot` at `80 outbound contacts per month` with a `sub-$100 weekly budget`, and judge it on `>=7% reply rate` plus `<20% stale-qualified-reply rate`.

**Cost per qualified lead**

Repo inputs:

- `llm_eval_usd_recorded = $0.003556`
- `outbound_email_usd = $0.0`
- `sms_usd = $0.0`
- `qualified_leads = 20`

Arithmetic:

`($0.003556 + $0.0 + $0.0) / 20 = $0.0001778`

Rounded preview CPL:

`$0.000178`

Qualification definition matters. `invoice_summary.json` uses `20` file-defined qualified leads, while `submission_run_summary.json` shows a stricter commercially advanced subset of `15` interactions (`5 book_meeting + 10 send_email`). On that stricter denominator the same preview spend is `$0.000237`. Either way, the preview cost is far below the challenge envelope.

**Speed-to-lead delta**

Definition used here: a `stalled thread` is a prospect reply with no recorded next action in the stored trace slice.

- Manual baseline: `30–40%`
- Stored system rate: `0 / 20 = 0%`

Comparison:

- versus midpoint baseline (`35%`): `35pp` improvement
- versus full baseline range: `30–40pp` improvement

Caveat: this is a synthetic preview run with injected replies, so it proves synchronous handling discipline, not final live-market responsiveness.

**Competitive-gap outbound performance**

Variant definitions from stored outbound drafts:

- `Research-led`: body contains `One peer signal stood out:`
- `Generic`: no competitor-gap lead language

Observed mix:

- research-led `18 / 20 = 90%`
- generic `2 / 20 = 10%`

Observed reply rates in the stored synthetic slice:

- research-led `18 / 18 = 100%`
- generic `2 / 2 = 100%`
- delta `0 percentage points`

That is not a real outbound performance claim. The synthetic harness stores one inbound interaction per prospect, so the current codebase proves the variant mix, but not a decision-grade reply-rate lift between variants.

**Pilot scope**

- Segment: `Segment 2 — Mid-market platforms restructuring cost`
- Lead volume: `80 outbound contacts per month`
- Budget: `under $100 per week`
- Thirty-day success criterion: `>=7% reply rate` on live research-led outreach and `<20% stale-qualified-reply rate`

Segment 2 is the right first pilot because the public signal is the clearest in this repo: cost pressure plus active engineering demand is easier to explain honestly than a weaker AI-maturity-only story.

## Page 2: The Skeptic's Appendix

**Four failure modes τ²-Bench does not capture**

1. `Offshore-perception objections`: a senior engineering buyer reacts badly to outsourcing language even when the facts are correct. τ²-Bench misses this because it tests task completion, not Tenacious tone under skepticism. Add Tenacious-specific objection personas scored against the style guide. Cost: `8–10` new probes plus manual review.

2. `Bench staleness`: the weekly bench snapshot is accurate when loaded but stale by the time a live conversation happens. τ²-Bench misses this because it assumes static state. Add time-shifted bench fixtures and staleness injection. Cost: about `1 engineering day` plus fixture maintenance.

3. `Competitor-gap defensiveness`: a self-aware CTO reads a gap brief as patronizing even when the signal extraction is technically correct. τ²-Bench misses this because it has no senior technical persona grading for condescension. Add expert personas and tone-scored competitor-gap probes. Cost: `6–8` targeted probes and manual rubric review.

4. `Multi-thread company leakage`: two contacts at the same company receive different research narratives in parallel. τ²-Bench misses this because it is single-threaded and does not model account-level coordination. Add company-level dedupe logic and replay tests. Cost: about `1 engineering day` plus replay fixtures.

**Public-signal lossiness in AI maturity scoring**

False negative archetype: a quietly sophisticated but publicly silent company with real internal AI work, no public AI roles, no named AI leader, and minimal executive commentary. In this system that company scores low, gets a generic exploratory message, and may never receive the sharper specialized-capability angle it actually deserves. Business impact: a missed high-value touch on an account that may fit Tenacious well but chooses not to advertise its AI work.

False positive archetype: a loud but shallow company with AI-heavy marketing language, some modern data-stack references, and weak evidence of a real operating AI function. In this system the agent can over-read the marketing layer and sound more certain than the evidence supports. Business impact: a CTO sees the outreach as sloppy or performative, which is exactly the kind of brand damage Tenacious cannot afford in a research-led motion.

**One honest unresolved failure**

The cleanest unresolved failure from the probe library is `multi-thread leakage`: two contacts at the same company can still receive different outreach framings inside the same week because the current mechanism is contact-scoped, not company-scoped. Trigger condition: simultaneous outreach to a founder and a VP Engineering at one account with no deduplication layer. Business impact: even if both notes are individually grounded, one sophisticated account comparing screenshots can conclude the system is inconsistent, putting a `$240,000` floor outsourcing opportunity at avoidable brand risk.
