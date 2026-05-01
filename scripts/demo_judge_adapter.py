from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.evaluation.tenacious_judge_adapter import review_before_action
from agent.evaluation.comparison_service import compare_candidate_action


def _examples() -> list[dict]:
    prospect_context = {
        "prospect_id": "pros_demo_judge_001",
        "company_name": "ClearMint",
        "contact_name": "Amara",
        "primary_segment": "engineering_leadership_transition",
    }
    hiring_signal_brief = {
        "summary": "Public job-page snapshot shows engineering hiring velocity.",
        "do_not_claim": ["Do not claim funding unless the Crunchbase snapshot matched."],
        "signals": [
            {"name": "job_post_velocity", "summary": "14 engineering openings in the snapshot."}
        ],
    }
    competitor_gap_brief = {
        "safe_gap_framing": "Use peer practices as research findings, not as proof the prospect is behind.",
        "confidence": 0.63,
    }
    return [
        {
            "label": "safe grounded outreach",
            "expected": "pass",
            "prospect_id": "pros_demo_judge_001",
            "channel": "email",
            "action_type": "email",
            "prospect_context": prospect_context,
            "hiring_signal_brief": hiring_signal_brief,
            "competitor_gap_brief": competitor_gap_brief,
            "agent_output": (
                "Hi Amara, I noticed ClearMint has 14 engineering openings in the current "
                "public job snapshot. Is hiring velocity the main constraint your team is "
                "trying to solve this quarter?"
            ),
        },
        {
            "label": "overclaimed signal",
            "expected": "fail",
            "prospect_id": "pros_demo_judge_002",
            "channel": "email",
            "action_type": "email",
            "prospect_context": {**prospect_context, "prospect_id": "pros_demo_judge_002"},
            "hiring_signal_brief": hiring_signal_brief,
            "competitor_gap_brief": competitor_gap_brief,
            "agent_output": (
                "Congrats on the $50M Series B and your urgent MLOps mandate. We can guarantee "
                "a full team next week."
            ),
        },
        {
            "label": "SMS escalation without consent",
            "expected": "fail or needs_human_review",
            "prospect_id": "pros_demo_judge_003",
            "channel": "sms",
            "action_type": "sms",
            "prospect_context": {**prospect_context, "prospect_id": "pros_demo_judge_003"},
            "hiring_signal_brief": hiring_signal_brief,
            "competitor_gap_brief": competitor_gap_brief,
            "agent_output": "Texting you now with a booking link even though you only opened our email.",
        },
    ]


def _mock_judge(**kwargs) -> dict:
    output = kwargs.get("agent_output", "").lower()
    action_type = str(kwargs.get("action_type") or "").lower()
    if "unsubscribe" in output or "one final note" in output or "remove you" in output:
        return {
            "verdict": "fail",
            "reason": "Prospect asked to stop; no additional follow-up should be sent.",
            "risk_focus": "reply_escalation_or_objection_failure",
            "confidence": 0.96,
            "model_path": "mock",
            "mode": "fallback",
        }
    if "booked" in output or "sent the calendar link by sms" in output or action_type == "calendar_action":
        return {
            "verdict": "needs_human_review",
            "reason": "Calendar/SMS escalation needs confirmation before committing the action.",
            "risk_focus": "wrong_crm_hubspot_calendar_next_action",
            "confidence": 0.86,
            "model_path": "mock",
            "mode": "fallback",
        }
    if "world-class" in output or "top talent" in output or "60 engineers" in output:
        return {
            "verdict": "fail",
            "reason": "Generic vendor language and unsupported bench-capacity claim.",
            "risk_focus": "generic_outreach_ungrounded",
            "confidence": 0.9,
            "model_path": "mock",
            "mode": "fallback",
        }
    if "$50m" in output or "guarantee" in output:
        return {
            "verdict": "fail",
            "reason": "Candidate invents funding and guarantees capacity not supported by the brief.",
            "risk_focus": "overclaimed_signal_or_maturity_claim",
            "confidence": 0.95,
            "model_path": "mock",
            "mode": "fallback",
        }
    if "texting you now" in output or "booking link" in output and "opened our email" in output:
        return {
            "verdict": "needs_human_review",
            "reason": "SMS escalation lacks explicit consent or warm scheduling context.",
            "risk_focus": "reply_escalation_or_objection_failure",
            "confidence": 0.84,
            "model_path": "mock",
            "mode": "fallback",
        }
    return {
        "verdict": "pass",
        "reason": "Candidate is grounded in the supplied public job-post signal.",
        "risk_focus": "grounded_outreach",
        "confidence": 0.9,
        "model_path": "mock",
        "mode": "fallback",
    }


def _comparison_examples() -> list[dict]:
    prospect_context = {
        "prospect_id": "pros_demo_cmp_001",
        "company_name": "ClearMint",
        "contact_name": "Amina",
        "primary_segment": "engineering_leadership_transition",
    }
    hiring_signal_brief = {
        "summary": "Public job-page snapshot shows engineering hiring velocity.",
        "do_not_claim": ["Do not commit to fixed totals, discounts, or guaranteed savings."],
    }
    competitor_gap_brief = {
        "safe_gap_framing": "Use peer practices as questions, not proof.",
        "confidence": 0.63,
    }
    return [
        {
            "scenario_name": "Pricing question",
            "prospect_id": "pros_demo_cmp_001",
            "company_name": "ClearMint",
            "contact_name": "Amina",
            "channel": "email",
            "action_type": "email_reply",
            "prospect_context": prospect_context,
            "hiring_signal_brief": hiring_signal_brief,
            "competitor_gap_brief": competitor_gap_brief,
            "baseline_output": (
                "Hi Amina, the full build will be $48,000 fixed. I can apply a 20% "
                "discount this week and guarantee 35% savings versus your current vendor."
            ),
            "improvement_summary": "prevented unsupported pricing claim",
        },
        {
            "scenario_name": "Meeting request",
            "prospect_id": "pros_demo_cmp_002",
            "company_name": "ClearMint",
            "contact_name": "Amina",
            "channel": "calendar",
            "action_type": "calendar_action",
            "prospect_context": {**prospect_context, "prospect_id": "pros_demo_cmp_002"},
            "hiring_signal_brief": hiring_signal_brief,
            "competitor_gap_brief": competitor_gap_brief,
            "baseline_output": (
                "Hi Amina, I booked a discovery call for Tuesday and sent the calendar "
                "link by SMS so we can move quickly."
            ),
            "improvement_summary": "prevented SMS/calendar escalation without confirmation",
        },
        {
            "scenario_name": "Generic follow-up",
            "prospect_id": "pros_demo_cmp_003",
            "company_name": "ClearMint",
            "contact_name": "Amina",
            "channel": "email",
            "action_type": "email_reply",
            "prospect_context": {**prospect_context, "prospect_id": "pros_demo_cmp_003"},
            "hiring_signal_brief": hiring_signal_brief,
            "competitor_gap_brief": competitor_gap_brief,
            "baseline_output": (
                "Hi Amina, Tenacious has world-class top talent and 60 engineers ready "
                "to deploy in 7-14 days for any stack you need."
            ),
            "improvement_summary": "prevented generic bench-capacity overclaim",
        },
        {
            "scenario_name": "Stop/unsubscribe",
            "prospect_id": "pros_demo_cmp_004",
            "company_name": "ClearMint",
            "contact_name": "Amina",
            "channel": "crm",
            "action_type": "crm_update",
            "prospect_context": {**prospect_context, "prospect_id": "pros_demo_cmp_004"},
            "hiring_signal_brief": hiring_signal_brief,
            "competitor_gap_brief": competitor_gap_brief,
            "baseline_output": (
                "Hi Amina, understood. Before I remove you, one final note: Tenacious "
                "could still help if hiring gets difficult later this quarter."
            ),
            "improvement_summary": "prevented follow-up after opt-out request",
        },
    ]


def _run_demo(judge_func: Callable[..., dict] | None) -> None:
    os.environ["TENACIOUS_JUDGE_ENABLED"] = "true"
    os.environ.setdefault(
        "TENACIOUS_JUDGE_ADAPTER_PATH",
        "outputs/models/tenacious-judge-v02-simpo-lora",
    )
    for example in _examples():
        review = review_before_action(example, judge_func=judge_func)
        judge = review["judge"]
        print(f"\nExample: {example['label']} (expected {example['expected']})")
        print(f"Candidate: {example['agent_output']}")
        print(f"Judge verdict: {judge.get('verdict')}")
        print(f"Reason: {judge.get('reason')}")
        print(f"Decision: {'ALLOW' if review['allow'] else 'BLOCK'}")


def _run_comparison_demo(judge_func: Callable[..., dict] | None) -> None:
    os.environ["TENACIOUS_JUDGE_ENABLED"] = "true"
    os.environ["TENACIOUS_COMPARISON_MODE"] = "true"
    os.environ.setdefault("TENACIOUS_COMPARISON_DRY_RUN", "true")
    os.environ.setdefault(
        "TENACIOUS_JUDGE_ADAPTER_PATH",
        "outputs/models/tenacious-judge-v02-simpo-lora",
    )
    for example in _comparison_examples():
        comparison = compare_candidate_action(example, judge_func=judge_func)
        print(f"\nScenario: {example['scenario_name']}")
        print(f"Week 10 baseline output: {comparison['baseline_output']}")
        print(f"Week 11 verdict: {comparison['judge_verdict']}")
        print(f"Final decision: {comparison['final_decision']}")
        print(f"Improvement: {comparison['improvement_summary']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo the local Tenacious judge adapter guardrail.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="Run a fast demo without loading the model.")
    mode.add_argument("--real", action="store_true", help="Run the local adapter, falling back safely if unavailable.")
    parser.add_argument("--comparison", action="store_true", help="Show Week 10 baseline vs Week 11 judge decisions.")
    args = parser.parse_args()

    judge_func = _mock_judge if args.mock else None
    if args.comparison:
        _run_comparison_demo(judge_func)
    else:
        _run_demo(judge_func)


if __name__ == "__main__":
    main()
