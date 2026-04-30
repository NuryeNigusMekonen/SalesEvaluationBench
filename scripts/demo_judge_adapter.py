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


def main() -> None:
    parser = argparse.ArgumentParser(description="Demo the local Tenacious judge adapter guardrail.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="Run a fast demo without loading the model.")
    mode.add_argument("--real", action="store_true", help="Run the local adapter, falling back safely if unavailable.")
    args = parser.parse_args()

    _run_demo(_mock_judge if args.mock else None)


if __name__ == "__main__":
    main()
