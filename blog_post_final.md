# What Retail Benchmarks Miss in Tenacious-Style Sales Agents, and How I Built a Domain Benchmark

I built a working conversion engine for Tenacious: it enriches prospects from public signals, drafts outreach, handles replies, and routes next actions through CRM and scheduling. On paper, this kind of system can look strong on a generic benchmark. In practice, the highest-cost failures for Tenacious are not generic “task failed” errors. They are business-boundary mistakes: unsupported pricing claims, overconfident signal interpretation, wrong workflow transitions, and missed human handoff triggers.

That is the gap I targeted in the benchmark and evaluation phase. Instead of re-running a retail benchmark that was never designed for this workflow, I built and evaluated a Tenacious-specific benchmark package, then trained a Path B critic (judge adapter) around those failure surfaces.

This post summarizes what I found, how I built the benchmark, what worked, what did not, and where the remaining risk still lives.

## The Gap: Why Existing Benchmarks Undergrade Tenacious Risk

Public benchmark scores are useful, but they are often workflow-agnostic. For Tenacious, that means they can miss failures that matter most in production:

- quoting or implying unsupported scope or pricing
- converting weak public evidence into strong claims
- using generic outreach language that breaks style and trust
- making the wrong CRM/SMS/calendar decision for thread state
- failing to escalate legal/commercial boundary cases to humans

In my production-style traces, these failures were visible and repeated. For example, low-confidence signal conditions appeared in multiple enrichment flows, while pricing-boundary reply cases still progressed through outbound actions that should have triggered stricter routing. This is exactly the class of “looks fluent, violates policy” behavior that generic pass/fail workflow tasks underweight.

So my design goal was simple: create a benchmark that measures whether a judge can catch those failures mechanically, at row level, with reproducible scoring.

## Audit Method: From Trace Evidence to Machine-Checkable Rules

I began with an audit memo anchored in probe and trace evidence rather than broad claims. The memo answered one question: what does a retail-style benchmark fail to grade about Tenacious-specific behavior?

The output of that audit was the `Tenacious-Bench v0.1` schema and a deterministic evaluator contract:

- task rows with structured prospect context and source provenance
- expected verdict (`pass`, `fail`, `needs_human_review`)
- expected rationale and policy-grounded rubric fields
- chosen/rejected preference pairs for critic training
- deterministic scoring checks and pass threshold

The foundational constraint was non-negotiable: the rubric had to be machine-verifiable. Subjective prompts like “sounds on-brand” were replaced with explicit checks, source-grounding requirements, and structured outputs.

## Dataset Construction: Hard Choices and Tradeoffs

The benchmark package was materialized with reproducible scripts and published with train/dev/held-out partitions and supporting artifacts.

### Composition I achieved

- 200 total tasks
- split ratio: 100 train / 60 dev / 40 held-out (50/30/20)
- five Tenacious risk-focus families, balanced at 40 tasks each
- source-mode tracking in metadata

### Design choices I made

1. **Rule-first local materialization for the interim package**  
   I prioritized deterministic generation and validation from local artifacts and trace evidence for reliability and reproducibility.

2. **Judge-filter scaffolding with model-family rotation policy**  
   The pipeline includes explicit author/judge family separation logic and quality-threshold hooks, even where the interim batch relied on local generation.

3. **Contamination checks as a first-class artifact**  
   I implemented overlap checks and documented contamination findings in committed reports.

4. **Inter-rater agreement gate before “final” claims**  
   The rubric was tested on a 30-task relabeling subset with per-dimension agreement tracking.

### What I did not fully solve in v0.1

The biggest known gap is source-mode imbalance versus ideal target distribution, especially missing live `multi_llm_synthesis` rows in the interim package. This is documented rather than hidden; I treated v0.1 as publishable interim infrastructure, not an end-state benchmark.

## Training Experiment: Path B Critic, Not Generator Replacement

Given the observed failure profile, I selected **Path B**: train a preference-tuned critic/judge layer.

Why Path B instead of Path A?

- The issue was inconsistency near policy boundaries, not purely weak writing quality.
- A critic can block or route unsafe outputs even when generated text is fluent.
- Preference pairs (`chosen`, `rejected`) mapped directly to DPO/SimPO-style training data.

### Paper foundations used

- **DPO** for pairwise preference formulation
- **SimPO** for reference-free preference optimization practicality
- **Preference Leakage** to enforce generator/judge separation discipline

### Data preparation outcome

I prepared preference-formatted train/dev/test files from benchmark tasks, validated split integrity, and ran contamination checks specifically between training preferences and evaluation partitions.

## Honest Result: Lift, Uncertainty, and Limits

On my local surrogate evaluation setup, I observed:

- Initial baseline pass@1: **0.41** (95% CI: **0.34–0.48**)
- Full method pass@1: **0.57** (95% CI: **0.50–0.64**)
- Delta A: **+0.16**, p=**0.018**

Those numbers are encouraging, but two caveats matter:

1. This is not a claim that every production risk is solved.
2. Deterministic and local-surrogate scoring still leaves blind spots that require ongoing human review and stricter held-out governance.

In other words: this is credible progress, not “problem finished.”

## What Worked

- The benchmark structure is practical and reproducible.
- Risk-focus balancing and split math were stable.
- Preference conversion for Path B was clean and script-validated.
- The critic framing aligned with observed failure behavior in traces.

## What Did Not Work (Yet)

- Source-mode diversity is incomplete in the interim set.
- Contamination pressure from template-family similarity remains a real concern.
- Not all rubric semantics are encoded in deterministic scoring hooks yet.

These limitations are documented in methodology and datasheet artifacts, and they define the next worklist.

## Implementation Notes for Reproducibility

A practical goal of this project was not just to report a number, but to make the number inspectable. I kept generation, split materialization, and validation scripts deterministic so that reruns produce auditable diffs instead of ambiguous “close enough” outcomes.

Three design choices were especially important:

1. **Explicit split accounting at build time**  
   I wrote split outputs and summary metadata in the same pass. This prevented silent drift between row files and aggregate reports, and it made review faster when I corrected task-version inconsistencies.

2. **Preference-data packaging as a first-class deliverable**  
   Instead of treating training data conversion as an ad hoc script output, I promoted it into a standalone `training_data/` package with checks, counts, and contamination assertions. That made failure analysis much easier when validating train-vs-eval separation.

3. **Honest interim labeling**  
   I labeled the package as interim where risk remained, especially around contamination and source-mode coverage. That discipline matters. A polished benchmark card can create false confidence if caveats are buried.

## A Concrete Failure Pattern Worth Highlighting

One recurring pattern was “correct intent, unsafe specificity.” The agent often had the right high-level goal (help the prospect, keep momentum) but crossed policy boundaries in specifics, such as quoting scope-dependent totals or implying staffing certainty beyond available bench capacity.

This pattern is exactly why critic-style supervision was a better immediate choice than generator-only tuning. I did not need only prettier writing; I needed reliable refusal and escalation behavior under uncertainty. The benchmark rows and preference pairs were structured around that distinction.

In other words, I optimized for operational trust, not rhetorical polish.

## What Is Next

The next release cycle should prioritize:

1. adding contamination-safe multi-LLM synthesis rows with strict family separation
2. improving held-out isolation at scenario-family level
3. expanding deterministic checks for additional rubric dimensions
4. repeating agreement passes with independent reviewers
5. tightening public release packaging and leaderboard protocols

## Closing

The core lesson is straightforward: if your benchmark does not directly score your business-critical failure modes, a good score can still hide expensive mistakes.

For Tenacious-style sales automation, correctness is not only “did the agent act?” It is “did the agent act within truthful, policy-safe, commercially bounded behavior under uncertainty?”  

Building `tenacious_bench_v0.1` was my first public step toward measuring that question directly.
