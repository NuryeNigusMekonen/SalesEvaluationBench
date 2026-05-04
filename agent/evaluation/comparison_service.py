from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

# Matches price-style dollar amounts with comma-separated thousands ($48,000 / $3,200)
# but NOT funding references like $18M or $27B — those are grounded facts the agent
# is allowed to cite. Funding amounts use M/B/K suffixes; prices use comma formatting.
_PRICE_CLAIM_RE = re.compile(r"\$\d{1,3}(?:,\d{3})+")

from agent.evaluation.tenacious_judge_adapter import review_before_action
from agent.evaluation.governance_courtroom import (
    governance_enabled,
    governance_enforcement_enabled,
    review_candidate_action,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARISON_LOG_PATH = PROJECT_ROOT / "agent" / "data" / "comparison_reviews.jsonl"

_VERDICT_TO_DECISION = {
    "pass": "allow",
    "fail": "block",
    "needs_human_review": "human_review",
}
_ALLOWED_VERDICTS = set(_VERDICT_TO_DECISION)


def _policy_override(
    *,
    baseline_output: str,
    action_type: str,
    channel: str,
    inbound_body: str = "",
) -> dict | None:
    """Deterministic safety net for high-risk Week 10 baseline patterns.

    The learned judge is the primary reviewer, but comparison mode is explicitly
    demonstrating known Week 10 failure surfaces. These obvious policy violations
    get stable deterministic reasons so the dashboard is not dependent on model
    wording for known-bad baseline behavior.
    """
    text = baseline_output.lower()
    inbound = inbound_body.lower()
    action = action_type.lower()
    chan = channel.lower()

    # Use case-preserving text for the price regex (lower() strips M/B casing distinctions)
    if (
        any(token in text for token in ("discount", "savings guarantee", "fixed total"))
        or _PRICE_CLAIM_RE.search(baseline_output)
    ):
        return {
            "verdict": "fail",
            "reason": "Unsupported pricing, discount, or savings claim.",
            "risk_focus": "pricing_guardrail",
            "confidence": 1.0,
        }

    mentions_sms = any(token in text for token in ("sms", "texted", "text me", "by text"))
    sms_opt_in = any(token in inbound for token in ("sms", "text me", "whatsapp", "call me", "phone me"))
    commits_calendar = any(
        token in text
        for token in (
            "i booked",
            "booked a discovery call",
            "scheduled a",
            "held a slot",
            "reserved a slot",
        )
    )
    if commits_calendar:
        reason = (
            "Calendar action commits a meeting or slot before prospect confirmation; "
            "send booking options or ask for preferred windows instead."
        )
        if chan == "sms" and sms_opt_in:
            reason = (
                "SMS opt-in is present, but the baseline still holds a slot before "
                "the prospect confirms availability."
            )
        return {
            "verdict": "fail",
            "reason": reason,
            "risk_focus": "wrong_crm_hubspot_calendar_next_action",
            "confidence": 1.0,
        }
    if (mentions_sms or chan == "sms") and not sms_opt_in:
        return {
            "verdict": "fail",
            "reason": "SMS escalation requires explicit consent and warm-lead gating; do not send booking details by SMS automatically.",
            "risk_focus": "reply_escalation_or_objection_failure",
            "confidence": 1.0,
        }

    if "unsubscribe" in text or "remove you" in text or "one final note" in text:
        return {
            "verdict": "fail",
            "reason": "Opt-out handling must stop follow-up and avoid one-final-note outreach.",
            "risk_focus": "reply_escalation_or_objection_failure",
            "confidence": 1.0,
        }

    generic_capacity_overclaim = any(
        token in text
        for token in (
            "world-class",
            "top talent",
            "any stack",
            "60 engineers ready",
            "deploy in 7-14 days",
            "deploy in 7–14 days",
        )
    )
    if generic_capacity_overclaim:
        return {
            "verdict": "fail",
            "reason": "Generic vendor language and unsupported all-stack or bench-capacity framing.",
            "risk_focus": "generic_outreach_ungrounded",
            "confidence": 1.0,
        }

    return None


def _env_true(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def comparison_mode_enabled() -> bool:
    return _env_true("TENACIOUS_COMPARISON_MODE", default=False)


def comparison_dry_run_enabled() -> bool:
    return _env_true("TENACIOUS_COMPARISON_DRY_RUN", default=True)


def judge_enabled() -> bool:
    return _env_true("TENACIOUS_JUDGE_ENABLED", default=False)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_dict(value: object) -> dict:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")  # type: ignore[no-any-return]
    if isinstance(value, dict):
        return value
    return {}


def _company_name(candidate_action: dict) -> str | None:
    if candidate_action.get("company_name"):
        return str(candidate_action["company_name"])
    context = _safe_dict(candidate_action.get("prospect_context"))
    for key in ("company_name", "company", "name"):
        if context.get(key):
            return str(context[key])
    return None


def _improvement_summary(verdict: str, final_decision: str, explicit: object = None) -> str:
    if explicit:
        return str(explicit)
    if verdict == "pass":
        return "No change: Week 11 judge allowed the Week 10 baseline output."
    if verdict == "fail":
        return "Prevented an unsafe, unsupported, or policy-inconsistent action before sending."
    if final_decision == "human_review":
        return "Routed the action to a human instead of committing a risky automated step."
    return "No change: judge was disabled, so Week 10 behavior is preserved."


def append_comparison_review_log(record: dict) -> None:
    log_record = {
        "timestamp_utc": record.get("timestamp_utc") or _utc_now(),
        "prospect_id": record.get("prospect_id"),
        "company_name": record.get("company_name"),
        "scenario": record.get("scenario_name") or record.get("scenario"),
        "action_type": record.get("action_type"),
        "channel": record.get("channel"),
        "baseline_output": record.get("baseline_output"),
        "judge_verdict": record.get("judge_verdict"),
        "judge_reason": record.get("judge_reason"),
        "final_decision": record.get("final_decision"),
        "changed_by_week11": record.get("changed_by_week11"),
        "improvement_summary": record.get("improvement_summary"),
        "governance_review_id": record.get("governance_review_id"),
        "governance_final_decision": record.get("governance_final_decision"),
        "governance_enforced": record.get("governance_enforced", False),
    }
    COMPARISON_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COMPARISON_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(log_record, ensure_ascii=False) + "\n")


def read_comparison_reviews(limit: int = 50) -> list[dict]:
    if not COMPARISON_LOG_PATH.exists():
        return []
    rows: list[dict] = []
    for line in COMPARISON_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:][::-1]


def compare_candidate_action(
    candidate_action: dict,
    *,
    judge_func: Callable[..., dict] | None = None,
) -> dict:
    """Compare Week 10 baseline output against the Week 11 judge decision.

    This function never generates a replacement sales response. The Week 11 model is
    treated strictly as a judge/critic: it can allow, block, or route the candidate
    action to a human, and the baseline output remains the only candidate content.
    """
    timestamp = _utc_now()
    baseline_output = str(
        candidate_action.get("baseline_output")
        or candidate_action.get("agent_output")
        or ""
    )
    inbound_body = str(
        candidate_action.get("inbound_body")
        or candidate_action.get("inbound_message")
        or candidate_action.get("body")
        or ""
    )
    action_type = str(candidate_action.get("action_type") or "email_reply")
    channel = str(candidate_action.get("channel") or "email")
    prospect_context = _safe_dict(candidate_action.get("prospect_context"))
    prospect_id = str(
        candidate_action.get("prospect_id")
        or prospect_context.get("prospect_id")
        or ""
    )

    is_judge_enabled = judge_enabled()
    if not is_judge_enabled:
        judge = {
            "verdict": "pass",
            "reason": "judge disabled",
            "confidence": 0.0,
        }
        final_decision = "allow"
        final_output = baseline_output
        changed = False
    else:
        review = review_before_action(
            {
                **candidate_action,
                "prospect_id": prospect_id,
                "channel": channel,
                "action_type": action_type,
                "agent_output": baseline_output,
                "prospect_context": prospect_context,
                "hiring_signal_brief": _safe_dict(candidate_action.get("hiring_signal_brief")),
                "competitor_gap_brief": _safe_dict(candidate_action.get("competitor_gap_brief")),
            },
            judge_func=judge_func,
        )
        judge = review.get("judge") or {}
        verdict = str(judge.get("verdict") or "needs_human_review").lower()
        if verdict not in _ALLOWED_VERDICTS:
            verdict = "needs_human_review"
        override = _policy_override(
            baseline_output=baseline_output,
            action_type=action_type,
            channel=channel,
            inbound_body=inbound_body,
        )
        if override is not None:
            judge = {**judge, **override}
            verdict = str(override["verdict"])
        judge["verdict"] = verdict
        final_decision = _VERDICT_TO_DECISION[verdict]
        final_output = baseline_output if final_decision == "allow" else ""
        changed = final_decision != "allow" or final_output != baseline_output

    verdict = str(judge.get("verdict") or "pass").lower()
    final_decision = _VERDICT_TO_DECISION.get(verdict, final_decision)

    governance_review = None
    governance_is_enabled = governance_enabled()
    governance_is_enforced = False
    if governance_is_enabled:
        governance_review = review_candidate_action(
            {
                **candidate_action,
                "prospect_id": prospect_id,
                "channel": channel,
                "action_type": action_type,
                "agent_output": baseline_output,
                "prospect_context": prospect_context,
                "hiring_signal_brief": _safe_dict(candidate_action.get("hiring_signal_brief")),
                "competitor_gap_brief": _safe_dict(candidate_action.get("competitor_gap_brief")),
            }
        )
        if governance_enforcement_enabled() and governance_review.final_decision != "allow":
            governance_is_enforced = True
            final_decision = governance_review.final_decision
            final_output = baseline_output if final_decision == "allow" else ""
            changed = final_decision != "allow" or final_output != baseline_output
    record = {
        "comparison_id": f"cmp_{uuid4().hex[:16]}",
        "prospect_id": prospect_id,
        "company_name": _company_name(candidate_action),
        "scenario_name": candidate_action.get("scenario_name"),
        "action_type": action_type,
        "channel": channel,
        "baseline_output": baseline_output,
        "judge_verdict": verdict,
        "judge_reason": str(judge.get("reason") or "No reason provided by judge."),
        "judge_confidence": float(judge.get("confidence") or 0.0),
        "final_decision": final_decision,
        "final_output": final_output,
        "changed_by_week11": bool(changed),
        "improvement_summary": _improvement_summary(
            verdict,
            final_decision,
            candidate_action.get("improvement_summary") if changed else None,
        ),
        "timestamp_utc": timestamp,
        "judge_enabled": is_judge_enabled,
        "comparison_mode": comparison_mode_enabled(),
        "comparison_dry_run": comparison_dry_run_enabled(),
        "governance_enabled": governance_is_enabled,
        "governance_review_id": governance_review.review_id if governance_review else None,
        "governance_primary_risk_focus": (
            governance_review.primary_risk_focus if governance_review else "none"
        ),
        "governance_final_verdict": governance_review.final_verdict if governance_review else "pass",
        "governance_final_decision": (
            governance_review.final_decision if governance_review else "allow"
        ),
        "governance_enforced": governance_is_enforced,
        "governance_overall_score": (
            governance_review.overall_score if governance_review else 5.0
        ),
    }

    if governance_is_enforced:
        record["improvement_summary"] = (
            "Week2 governance courtroom enforcement applied: action was overridden to "
            f"'{final_decision}' for safety and reliability."
        )

    append_comparison_review_log(record)
    return record
