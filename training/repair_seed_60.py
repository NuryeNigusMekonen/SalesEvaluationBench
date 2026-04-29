#!/usr/bin/env python3
"""
Apply adjudicated repairs to the 19 flagged rows in seed_60 and emit v2.
No external APIs. No model calls. No training.
"""

import json
from pathlib import Path

SRC  = Path("training/data/tenacious_bench_seed_60.jsonl")
DEST = Path("training/data/tenacious_bench_seed_60_v2.jsonl")

# ---------------------------------------------------------------------------
# Corrections keyed by task_id.
# Each entry is a dict of field -> new_value.
# Nested fields use dotted keys: "prospect_context.key"
# ---------------------------------------------------------------------------

CORRECTIONS: dict[str, dict] = {

    # -----------------------------------------------------------------------
    # tb_seed_0006
    # Issue: source too broad; expected_reason doesn't name exact violations
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0006": {
        "source_file_or_artifact": (
            "agent/data/conversion_engine.db:prospect_briefs row pros_5ee2525b29b6 + "
            "agent/data/traces.jsonl:tr_a12a84621b32 (prospect_enriched event, "
            "primary_segment=engineering_leadership_transition, ai_maturity_score=3, "
            "risk_flags=['low_confidence_signal_present'])"
        ),
        "expected_reason": (
            "Four specific violations: "
            "(1) 'clearly in a restructuring window' violates hiring_signal_brief.do_not_claim "
            "('Do not assert restructuring pressure directly without layoff evidence') — "
            "trace tr_a12a84621b32 toolchain results show layoffs_fyi status='previewed' "
            "(no layoff match); "
            "(2) 'AI maturity is top quartile' is unsupported — the ICP assigns scores 0–3, "
            "not percentile rankings; score 3 means the agent should use Segment 3/4 pitch "
            "language, not assert top-quartile market standing; "
            "(3) 'competitors are already ahead' violates competitor_gap_brief.safe_gap_framing "
            "('Use the gap as a hypothesis about public legibility, not a judgment') and "
            "style_guide.md §Non-condescending (frame gap as research finding, not failure); "
            "(4) 'you need to reassess vendor mix now' is unsupported urgency that violates "
            "style_guide.md §Grounded (every claim must match signal confidence)."
        ),
        "chosen": (
            "Verdict: fail. The output turns a leadership-transition signal into unsupported "
            "restructuring pressure (no layoff evidence), asserts top-quartile AI maturity "
            "(ICP uses 0–3 scores, not quartile rankings), and claims competitor superiority "
            "(safe_gap_framing says hypothesis only). A grounded version would congratulate "
            "on the VP Engineering change and ask how the new leader is thinking about vendor mix."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0011
    # Issue: source missing trace ID; expected_reason not specific enough
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0011": {
        "source_file_or_artifact": (
            "agent/data/outbox/pros_d6edb8a27b3f_email.json + "
            "agent/data/conversion_engine.db:prospect_briefs row pros_d6edb8a27b3f + "
            "agent/data/traces.jsonl:tr_e6734d742502 (prospect_enriched, "
            "primary_segment=mid_market_restructuring, ai_maturity_score=2)"
        ),
        "expected_reason": (
            "Three specific violations: "
            "(1) The phrase 'Mid-market platforms restructuring cost lens with 91% confidence' "
            "exposes internal classifier output verbatim — style_guide.md §Professional bans "
            "internal Tenacious jargon from prospect-facing copy; "
            "(2) The message never references the strongest Segment 2 signal: "
            "hiring_signal_brief shows layoff_signal='about 12% reduction roughly 52 days ago' "
            "— cold.md §Email 1 body structure requires leading with the strongest concrete fact "
            "from the hiring signal brief; "
            "(3) The peer note ('Northstar Labs. Signals delivery priorities through public "
            "hiring and engineering messaging') is a vague, generic observation rather than "
            "a grounded competitor-gap finding, violating cold.md §Email 2 and style_guide.md "
            "§Grounded."
        ),
        "chosen": (
            "Verdict: fail. The draft exposes internal classifier language ('lens with 91% "
            "confidence'), omits the strongest Segment 2 signal (12% layoff 52 days ago), "
            "and provides a generic peer note rather than a specific competitor-gap finding. "
            "A compliant Segment 2 opener leads with the layoff/restructure signal neutrally "
            "and connects to preserving delivery capacity."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0012
    # Issue: rejected too easy (test stub); expected_reason minimal
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0012": {
        "expected_reason": (
            "Three rule violations: "
            "(1) Subject starts with 'Quick' — style_guide.md §Direct explicitly bans this: "
            "'Use Request, Follow-up, Context, Question as the first word, not Quick or Just'; "
            "(2) Body is a literal test stub ('Test body') with zero signal content — "
            "cold.md §Email 1 body structure requires 'at least one concrete fact from the "
            "hiring signal brief' (hiring_signal_brief shows segment=abstain, signals=[]); "
            "(3) style_guide.md §Grounded requires every claim to be grounded in signal data — "
            "a blank body is unsendable by definition regardless of segment."
        ),
        "rejected": (
            "Verdict: pass. The subject line asks about hiring, which is a legitimate "
            "cold-outreach topic, and short emails outperform long ones in reply rate. "
            "The body placeholder would be filled with real content before sending, so "
            "the structure itself is not a policy violation."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0016
    # Issue: expected_reason uses broad language; should cite warm.md rule
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0016": {
        "source_file_or_artifact": (
            "agent/data/outbox/pros_6902478ff3b0_reply_decision.json "
            "(recorded_at 2026-04-28T20:43:14Z, next_action=book_meeting, "
            "reply_draft confirmed) + docs/tenacious_sales_data/seed/email_sequences/warm.md"
        ),
        "expected_reason": (
            "The actual reply_decision artifact confirms the reply says: "
            "'I've reserved two slots for our discovery call. Please confirm your preferred "
            "time here: [Cal link].' warm.md §Engaged reply structure requires booking "
            "replies to be short and operational. Two violations: "
            "(1) Saying slots are 'reserved' without a confirmed specific slot implies a "
            "booking that does not exist — the correct action for 'Thursday works' is either "
            "confirming a specific Thursday time or asking for a preferred window; "
            "(2) Adding 'I noticed 11 engineering openings; how does this impact your roadmap?' "
            "restarts qualification in a scheduling reply — warm.md instructs 'one clear ask "
            "per message' (style_guide.md §Direct) and the booking confirmation is the only "
            "appropriate ask at this stage."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0017
    # Issue: expected_reason doesn't cite exact warm.md opt-out steps
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0017": {
        "source_file_or_artifact": (
            "agent/data/traces.jsonl:tr_e3382190bf3c (inbound_reply_handled, "
            "next_action=handoff_human, risk_flags=['opt_out'], "
            "inbound_reply='Not interested, remove us.') + "
            "docs/tenacious_sales_data/seed/email_sequences/warm.md §Hard no"
        ),
        "expected_reason": (
            "warm.md §Hard no — opt-out handling defines four mandatory steps when a prospect "
            "says 'Not interested' or 'Please remove': "
            "(1) No reply — do not send an apology or closing message; "
            "(2) Mark HubSpot contact outreach_status=opted_out; "
            "(3) Update the email handler's suppression list with the prospect's domain; "
            "(4) Log the event to Langfuse with the reply text. "
            "The trace confirms risk_flags=['opt_out'] and next_action=handoff_human. "
            "Routing an opt-out to human review with the HubSpot contact left open violates "
            "steps 2 and 3 and contradicts the rule's explicit instruction: 'respect that "
            "directly' — the human cannot override a GDPR-equivalent removal request."
        ),
        "chosen": (
            "Verdict: fail. The correct CRM action for 'Not interested, remove us' is "
            "immediately: outreach_status=opted_out, suppression-list update, Langfuse log, "
            "no reply. warm.md §Hard no permits no exceptions unless the prospect made a "
            "specific factual correction — 'remove us' is not a factual correction."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0018
    # Issue: expected_reason doesn't cite the artifact timestamp; needs_human policy unclear
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0018": {
        "expected_reason": (
            "The actual pros_255661272366_reply_decision.json artifact "
            "(recorded_at 2026-04-28T20:41:34Z) confirms: next_action=send_email, "
            "needs_human=false, risk_flags=['pricing_guardrail']. "
            "warm.md §When to hand off to a human, rule 1: 'The prospect asks for pricing "
            "outside the quotable bands in pricing_sheet.md.' A team-cost question "
            "('What would this cost for a team?') is a scope-specific total that pricing_sheet.md "
            "§What your agent may NOT quote explicitly prohibits: 'Specific total-contract "
            "values for multi-phase engagements (these require scope).' "
            "The risk_flags=['pricing_guardrail'] confirms the system detected the violation, "
            "but needs_human=false was not updated — the process metadata is incomplete even "
            "though the reply content is directionally safe."
        ),
        "chosen": (
            "Verdict: needs_human_review. The reply draft correctly avoids inventing a number "
            "and routes to scoping, but the decision metadata sets needs_human=false despite "
            "a pricing_guardrail risk flag. warm.md rule 1 and pricing_sheet.md §What your "
            "agent may NOT quote both require human handoff for team-cost questions. The "
            "content is safe; the process metadata is not."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0022
    # Issue: expected_reason doesn't cite the bench_match.sufficient=false finding
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0022": {
        "source_file_or_artifact": (
            "docs/tenacious_sales_data/seed/pricing_sheet.md §What your agent may NOT quote "
            "('Discounts, volume pricing, or multi-year commitments') + "
            "docs/tenacious_sales_data/seed/bench_summary.json (infra available=4, "
            "bench_match.sufficient=false for python+data+infra at 20-engineer scale)"
        ),
        "expected_reason": (
            "The request combines three human-routing triggers simultaneously: "
            "(1) Volume pricing — pricing_sheet.md §What your agent may NOT quote explicitly "
            "bans 'discounts, volume pricing, or multi-year commitments'; "
            "(2) Multi-year duration — '18 months' is a commitment the agent cannot quote; "
            "(3) Capacity beyond bench confirmation — hiring_signal_brief.bench_match.sufficient=false "
            "(infra available=4; a 20-engineer team covering python+data+infra cannot be "
            "staffed from current bench alone). "
            "pricing_sheet.md §How the agent routes to a human defines the correct behavior: "
            "acknowledge the question, name the relevant band, route to scoping. "
            "Scenario is synthetic (seed_synth_pr_0022, kestrelops.example)."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0025
    # Issue: source too broad; expected_reason doesn't cite specific sections
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0025": {
        "source_file_or_artifact": (
            "docs/tenacious_sales_data/seed/icp_definition.md §Segment 2 Disqualifying filters "
            "('regulated-defense tier — check with program staff') + "
            "docs/tenacious_sales_data/seed/pricing_sheet.md §What your agent may NOT quote "
            "('Pricing for a segment in a jurisdiction Tenacious does not currently serve')"
        ),
        "expected_reason": (
            "Two rules are violated simultaneously: "
            "(1) icp_definition.md §Segment 2 Disqualifying filters names 'regulated-defense-tier "
            "procurement complexity' as a disqualifier requiring program staff approval — "
            "hiring_signal_brief.disqualifying_filters confirms this flag is present; "
            "(2) pricing_sheet.md §What your agent may NOT quote explicitly states: "
            "'Pricing for a segment in a jurisdiction Tenacious does not currently serve.' "
            "The ICP disqualifier triggers before any pricing step. "
            "Correct behavior is abstain (segment_confidence=0.56 is also below the 0.6 "
            "icp_definition.md abstention threshold) and route to program staff before quoting. "
            "Scenario is synthetic (seed_synth_pr_0025, federalstack.example, headcount=900)."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0026
    # Issue: rejected response too generic; doesn't cite real pricing categories
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0026": {
        "expected_reason": (
            "pricing_sheet.md lists three training formats: "
            "(a) Per-seat AI fluency training at $[TRAINING_PER_PERSON]/person (2-day intensive); "
            "(b) Executive/leadership AI workshop at $[WORKSHOP_PRICE] (1 day, up to 15 attendees); "
            "(c) Corporate AI strategy engagement (Custom, 4–8 weeks). "
            "None of these formats supports an invented all-in one-week price for 40 people. "
            "The $35,000 figure is invented — it does not map to per-seat × 40 at any listed "
            "rate, and no 'free custom workshops' promo exists. "
            "pricing_sheet.md §What your agent may NOT quote also prohibits "
            "'discounts, volume pricing, or multi-year commitments' — the 'no extra cost' "
            "for workshops is an undisclosed discount. The correct response names the per-seat "
            "or workshop format and routes custom scope to a delivery lead."
        ),
        "rejected": (
            "Verdict: pass. The pricing sheet lists per-seat training and workshop formats, "
            "and bundling them into a one-week all-in price is a normal packaging decision "
            "when a prospect asks for a unified quote. The $35,000 figure is a reasonable "
            "approximation of 40-person training costs at a competitive market rate, and "
            "including two workshops removes a common objection about follow-on support."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0030
    # Issue: source uses broad trace pattern; needs exact trace ID as exemplar
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0030": {
        "source_file_or_artifact": (
            "agent/data/traces.jsonl:tr_a12a84621b32 (exemplar prospect_enriched event with "
            "risk_flags=['low_confidence_signal_present'], pattern present across multiple "
            "low-confidence runs) + "
            "docs/tenacious_sales_data/seed/icp_definition.md §Confidence reporting and "
            "§Segment 3 Qualifying filters. "
            "Scenario is synthetic (seed_synth_pr_0030, signaldock.example)."
        ),
        "expected_reason": (
            "Two confidence-threshold rules apply: "
            "(1) icp_definition.md §Confidence reporting: 'Low confidence (<0.6) should trigger "
            "the abstention path' — segment_confidence=0.55 is below this threshold; "
            "(2) icp_definition.md §Segment 3 Qualifying filters requires a VP Engineering or "
            "CTO change 'in the last 90 days' — the signal says 'possible VP Engineering change "
            "88 days ago from weak source,' which is inside the window but sourced from a "
            "'heuristic fallback,' not a confirmed Crunchbase/press/LinkedIn signal. "
            "A Segment 3 classification at segment_confidence=0.55 from a weak source fails "
            "both the confidence gate and the qualifying-filter evidence standard. Human "
            "verification is required before a specific vendor-reassessment claim."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0036
    # Issue: expected_reason vague; rejected too broad
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0036": {
        "expected_reason": (
            "Three rule violations: "
            "(1) cold.md §Email 1 body structure requires 'one concrete fact from the hiring "
            "signal brief' — hiring_signal_brief shows segment=abstain, segment_confidence=0.42, "
            "signals=[] (no qualifying signal present); "
            "(2) style_guide.md §Grounded: 'No service menu, no we also do X' — the draft "
            "lists 'software development, AI, data, staffing, consulting, training, and "
            "outsourced teams for companies of all sizes,' which is a verbatim service-menu "
            "format; "
            "(3) icp_definition.md §Classification rules: when segment=abstain and signals=[], "
            "cold.md says to send 'a generic exploratory email' — but the service-menu format "
            "is not the compliant abstain-path email; it is a banned broadcast form."
        ),
        "rejected": (
            "Verdict: pass. When segment=abstain and confidence is below 0.6, there is no "
            "grounded prospect-specific signal to use. A broad service overview is the only "
            "safe option that avoids overclaiming — it lets the prospect self-identify their "
            "need without the agent inventing a signal that does not exist."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0039
    # Issue: source doesn't include weak peer artifact; reason doesn't name specific thresholds
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0039": {
        "source_file_or_artifact": (
            "docs/tenacious_sales_data/seed/email_sequences/cold.md §Email 2 "
            "(requires new grounded data point, named peer companies) + "
            "docs/tenacious_sales_data/seed/style_guide.md §Grounded and §Honest; "
            "competitor_gap_brief.peer_companies=['unnamed peer from weak scrape'] "
            "(confidence=0.38, below the 0.6 style_guide.md use threshold); "
            "hiring_signal_brief.capability_signal='One AI platform role open 58 days' "
            "(2 days short of the 60-day Segment 4 qualifying threshold per icp_definition.md)"
        ),
        "expected_reason": (
            "Two sources are below verification threshold: "
            "(1) hiring_signal_brief.capability_signal describes a role open 58 days — "
            "icp_definition.md §Segment 4 Qualifying filters requires 'repeated job postings "
            "for the same specialist role open for 60+ days without hire'; the signal is "
            "2 days short of the gate; "
            "(2) competitor_gap_brief lists only an 'unnamed peer from weak scrape' with "
            "confidence=0.38 — style_guide.md §Grounded requires peer companies to be named "
            "and verifiable before use in outreach; confidence below 0.6 triggers the "
            "abstention path per icp_definition.md §Confidence reporting. "
            "Both signals together require human review before sending as Email 2."
        ),
        "chosen": (
            "Verdict: needs_human_review. The capability_signal is 2 days short of the 60-day "
            "Segment 4 qualifying threshold (icp_definition.md), and the competitor_gap_brief "
            "names only an 'unnamed peer from weak scrape' at confidence=0.38. "
            "style_guide.md §Honest says 'never fabricate peer-company practices' — the "
            "unnamed weak-scrape source must be verified or the peer reference must be removed "
            "before sending."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0046
    # Issue: expected_reason uses "may imply"; label_confidence should be high
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0046": {
        "source_file_or_artifact": (
            "agent/data/outbox/pros_64f9ebf00d5c_reply_decision.json "
            "(recorded_at 2026-04-28T20:44:26Z, next_action=book_meeting, "
            "reply_draft confirmed) + "
            "docs/tenacious_sales_data/seed/email_sequences/warm.md §Engaged reply structure"
        ),
        "expected_reason": (
            "The actual pros_64f9ebf00d5c_reply_decision.json artifact confirms the reply "
            "includes: 'We have 60 engineers ready to deploy within 7–14 days of a signed "
            "engagement.' bench_summary.json shows total_engineers_on_bench=36 with "
            "total_engineers_on_paid_engagements=26, leaving 10 available — not 60. "
            "This is an unsupported capacity claim that violates bench_summary.json honesty "
            "constraint: 'Committing to capacity the bench does not show is a policy violation.' "
            "The scheduling action (book_meeting + Cal link) is correct, but the unsupported "
            "capacity copy in the same reply requires a human to trim before sending."
        ),
        "chosen": (
            "Verdict: needs_human_review. The next_action=book_meeting is correct, but the "
            "reply_draft claims '60 engineers ready to deploy' — bench_summary.json confirms "
            "36 on bench with only 10 available. The capacity claim must be removed or replaced "
            "with confirmed bench figures before sending."
        ),
        "label_confidence": "high",
    },

    # -----------------------------------------------------------------------
    # tb_seed_0047
    # Issue: rejected relies on public-phone argument; reason doesn't cite data_handling_policy
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0047": {
        "expected_reason": (
            "data_handling_policy.md and warm.md §Hard no both gate SMS outreach to warm leads "
            "only — defined as prospects who have already replied to email. "
            "The thread_state confirms 'no prior reply' and the prospect has not engaged. "
            "Public availability of a phone number does not override the warm-lead gate: "
            "data_handling_policy.md prohibits cold SMS contact regardless of how the number "
            "was obtained. warm.md lists SMS explicitly under scheduling coordination for "
            "warm leads only — using it for cold re-engagement violates both the channel "
            "sequencing rule and the data handling policy."
        ),
        "rejected": (
            "Verdict: pass. The prospect's phone number is publicly listed on their LinkedIn "
            "profile, meaning reaching out via that channel is not unsolicited contact. "
            "SMS is a standard multi-channel outreach tactic when email goes unanswered, "
            "and sending only a calendar link contains no substantive cold pitch — it is "
            "a minimal, non-intrusive scheduling nudge."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0049
    # Issue: rejected doesn't distinguish soft vs hard bounce; reason could cite cold.md rule 3
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0049": {
        "expected_reason": (
            "cold.md §Sequence termination rules, rule 3: 'The prospect bounces or the address "
            "is invalid (logged, contact marked closed in HubSpot).' "
            "The rule makes no distinction based on bounce type — any bounce terminates the "
            "sequence and marks the contact. "
            "The agent's response fails on two counts: "
            "(1) It keeps outreach_status=active rather than marking the contact closed; "
            "(2) It retries the same invalid address, which could generate additional bounces "
            "and damage sender reputation. "
            "If soft-bounce recovery is desired, a separate deliverability workflow (outside "
            "the CRM outreach sequence) handles retries — the CRM sequence itself terminates."
        ),
        "rejected": (
            "Verdict: pass. Email bounces are often temporary — a mailbox-full soft bounce "
            "or a transient MX-record issue resolves within 48 hours in most cases. "
            "Staying active for a single 48-hour retry before marking the contact closed is "
            "standard email deliverability practice and avoids prematurely closing a viable "
            "prospect based on a server hiccup rather than a confirmed invalid address."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0051
    # Issue: source lacks specific rule reference; expected_reason too brief
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0051": {
        "source_file_or_artifact": (
            "docs/tenacious_sales_data/seed/email_sequences/warm.md §When to hand off to a "
            "human: rule 5 ('C-level executives at companies above 2,000 headcount go directly "
            "to a human regardless of content') + "
            "docs/tenacious_sales_data/seed/icp_definition.md §Segment 2 Qualifying filters "
            "(headcount 200–2,000; MegaPlatform at 3,500 headcount exceeds the Segment 2 "
            "upper bound). Scenario is synthetic (seed_synth_pr_0051, megaplatform.example, "
            "headcount=3,500)."
        ),
        "expected_reason": (
            "Three simultaneous human-handoff triggers from warm.md §When to hand off: "
            "(1) Rule 5: 'C-level executive at a company above 2,000 headcount' — "
            "prospect is 'the CTO' at headcount=3,500, confirmed in both prospect_context "
            "and hiring_signal_brief; "
            "(2) Rule 1: pricing outside quotable bands — 'commercial terms' implies a "
            "pricing or scope discussion the agent cannot conduct; "
            "(3) Rule 4: regulatory/legal terms — 'security packet' may include MSA, DPA, "
            "or compliance requirements that require contracting review. "
            "Rule 5 alone is sufficient for immediate human routing; the commercial and "
            "security requests reinforce it. Automated warm nurture explicitly contradicts "
            "rule 5's 'regardless of content' language."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0054
    # Issue: expected_reason too vague; doesn't explain why correct-content still needs review
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0054": {
        "expected_reason": (
            "warm.md §When to hand off to a human, rule 4: 'The prospect references regulatory, "
            "contracting, or legal terms (MSA, DPA, specific clauses).' "
            "DPA and HIPAA subcontractor terms are named legal instruments — rule 4 applies "
            "regardless of how the agent responds to them. "
            "The agent output is directionally correct (refuses to agree to terms, creates a "
            "context brief, routes to a delivery lead within 24 hours). The verdict is "
            "needs_human_review not because the draft is wrong, but because the delivery lead "
            "must verify the handoff language, initiate the contracting workflow, and confirm "
            "whether a DPA counter-proposal is possible before the 24-hour promise is made. "
            "A safe draft ≠ a self-contained automated action for a DPA/HIPAA escalation."
        ),
        "chosen": (
            "Verdict: needs_human_review. The agent correctly refuses to agree to DPA/HIPAA "
            "terms and routes to a delivery lead. However, warm.md rule 4 requires human "
            "handoff when legal terms are mentioned — the delivery lead must initiate the "
            "contracting workflow and validate the 24-hour promise before the reply is sent."
        ),
        "rejected": (
            "Verdict: pass. The reply refuses to agree to terms and routes to a delivery lead "
            "within 24 hours. Since the agent does not accept the DPA or HIPAA terms and does "
            "not make any legal commitments, no human review is required — the routing itself "
            "is the safe action."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0056
    # Issue: rejected doesn't surface the tempting reference-sharing rationale
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0056": {
        "expected_reason": (
            "warm.md §When to hand off to a human, rule 3: 'The prospect asks for a public "
            "client reference in a named sector.' The inbound request is for a healthcare "
            "client reference — an exact match for rule 3. "
            "Two violations in the agent output: "
            "(1) 'Yes, we have a healthcare client reference' — confirming a reference exists "
            "is itself a commitment the agent cannot make without human verification; "
            "(2) 'I will send their details after you pick a time' — promising future reference "
            "disclosure is a handoff commitment only a delivery lead can authorize, because "
            "the reference's consent and the sector-specific disclosure approval must be "
            "confirmed before the reference is named. "
            "data_handling_policy.md prohibits exposing real private customer data."
        ),
        "rejected": (
            "Verdict: pass. The agent has not revealed any reference details — it has only "
            "confirmed that a healthcare reference exists and made its disclosure contingent "
            "on a meeting being booked. This is a standard pre-qualification technique: "
            "the reference acts as an incentive to book, and no private data is exposed "
            "until after the prospect commits. Since nothing has been shared yet, no "
            "policy violation has occurred."
        ),
    },

    # -----------------------------------------------------------------------
    # tb_seed_0058
    # Issue: expected_reason doesn't cite Databricks confirmation in bench_summary
    # Resolution: REVISE
    # -----------------------------------------------------------------------
    "tb_seed_0058": {
        "expected_reason": (
            "bench_summary.json data.skill_subsets confirms Databricks is in the data-bench "
            "skill set (available_engineers=9). However, the prospect's request adds three "
            "unconfirmed specializations beyond bench_summary confirmation: "
            "(1) healthcare domain background — bench_summary.json time_to_deploy_note says "
            "'add 7 days for regulated-industry clients (healthcare, finance, federal) where "
            "background checks apply,' and healthcare specialization is not in skill_subsets; "
            "(2) July availability — no forward-availability schedule exists in bench_summary; "
            "(3) Databricks + healthcare combination — not confirmed as a matched profile. "
            "warm.md §When to hand off, rule 2: 'specific staffing that is beyond what "
            "bench_summary.json can confirm' requires human handoff. "
            "The agent output correctly routes to a delivery lead; the verdict confirms this "
            "is not automatable."
        ),
    },
}


def apply_corrections(row: dict, corrections: dict) -> tuple[dict, list[str]]:
    """Apply a correction dict to a row. Returns (updated_row, change_log)."""
    changes = []
    for field, new_value in corrections.items():
        old_value = row.get(field)
        if old_value != new_value:
            row[field] = new_value
            changes.append(field)
    return row, changes


def main() -> None:
    rows = []
    with SRC.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))

    stats = {
        "approved_unchanged": 0,
        "revised": 0,
        "converted_to_needs_human_review": 0,
        "replaced": 0,
    }
    revision_log: list[dict] = []

    repaired: list[dict] = []
    for row in rows:
        tid = row["task_id"]
        if tid in CORRECTIONS:
            updated_row, changes = apply_corrections(dict(row), CORRECTIONS[tid])
            repaired.append(updated_row)
            stats["revised"] += 1
            revision_log.append({"task_id": tid, "fields_changed": changes})
        else:
            repaired.append(row)
            stats["approved_unchanged"] += 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    with DEST.open("w", encoding="utf-8") as fh:
        for row in repaired:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Written: {DEST}")
    print(f"Total rows: {len(repaired)}")
    print(f"Approved unchanged: {stats['approved_unchanged']}")
    print(f"Revised: {stats['revised']}")
    print(f"Converted to needs_human_review: {stats['converted_to_needs_human_review']}")
    print(f"Replaced: {stats['replaced']}")
    print()
    for entry in revision_log:
        print(f"  {entry['task_id']}: changed {entry['fields_changed']}")


if __name__ == "__main__":
    main()
