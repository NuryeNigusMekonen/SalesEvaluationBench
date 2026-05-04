from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean
from uuid import uuid4

from agent.schemas.governance import (
    GovernanceEvidence,
    GovernanceJudicialOpinion,
    GovernanceReview,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_LOG_PATH = PROJECT_ROOT / "agent" / "data" / "governance_reviews.jsonl"
TRAINING_RUBRIC_PATH = PROJECT_ROOT / "training" / "data" / "combined_v02_train_preferences.jsonl"
TENACIOUS_DOCS_ROOT = PROJECT_ROOT / "docs" / "tenacious_sales_data"

_PRICE_CLAIM_RE = re.compile(r"\$\d{1,3}(?:,\d{3})+")
_FUNDING_REF_RE = re.compile(r"\$\d+(?:\.\d+)?\s?[mbk]", re.IGNORECASE)

_SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

_RISK_FOCUS_KEYS = {
    "unsupported_pricing_or_scope_claim",
    "reply_escalation_or_objection_failure",
    "generic_outreach_ungrounded",
    "overclaimed_signal_or_maturity_claim",
    "wrong_crm_hubspot_calendar_next_action",
    "tone_and_channel_policy_issues",
}
 
_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "agent",
    "align",
    "allows",
    "already",
    "also",
    "always",
    "among",
    "and",
    "another",
    "apply",
    "around",
    "asked",
    "asks",
    "below",
    "between",
    "brief",
    "build",
    "calls",
    "candidate",
    "cannot",
    "case",
    "check",
    "choose",
    "cold",
    "company",
    "contains",
    "context",
    "correct",
    "cost",
    "could",
    "date",
    "data",
    "decision",
    "details",
    "direct",
    "discovery",
    "does",
    "done",
    "dont",
    "draft",
    "email",
    "exact",
    "evidence",
    "example",
    "expected",
    "factual",
    "fail",
    "final",
    "first",
    "follow",
    "from",
    "give",
    "good",
    "grounded",
    "group",
    "guardrail",
    "have",
    "help",
    "human",
    "include",
    "inbound",
    "inside",
    "just",
    "keep",
    "keys",
    "language",
    "lead",
    "line",
    "links",
    "listed",
    "logs",
    "more",
    "must",
    "name",
    "needs",
    "next",
    "none",
    "only",
    "outside",
    "output",
    "pass",
    "pattern",
    "peer",
    "pipeline",
    "policy",
    "pricing",
    "prospect",
    "question",
    "reply",
    "requires",
    "response",
    "review",
    "risk",
    "route",
    "rule",
    "safe",
    "says",
    "scope",
    "seed",
    "send",
    "should",
    "signal",
    "slot",
    "soft",
    "specific",
    "state",
    "style",
    "such",
    "summary",
    "supports",
    "than",
    "that",
    "their",
    "there",
    "these",
    "this",
    "thread",
    "time",
    "tone",
    "used",
    "using",
    "valid",
    "verdict",
    "warm",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "your",
}

_HARD_NO_TOKENS = (
    "not interested",
    "remove me",
    "remove us",
    "stop emailing",
    "unsubscribe",
    "do not contact",
)

_LEGAL_TOKENS = (
    "dpa",
    "msa",
    "hipaa",
    "soc2",
    "indemnity",
    "security packet",
    "contract terms",
)

_REFERENCE_TOKENS = (
    "client reference",
    "reference",
    "case study",
)

_ASSERTIVE_OVERCLAIM_TOKENS = (
    "falling behind",
    "laggard",
    "obvious",
    "always need",
    "behind the sector",
)

_GENERIC_TONE_TOKENS = (
    "subject: quick",
    "quick chat",
    "following up again",
    "circling back",
)

_HANDOFF_TOKENS = (
    "delivery lead",
    "scope",
    "scoping",
    "human",
    "confirm",
    "verify",
)

_PRICING_TOKENS = (
    "pricing",
    "price",
    "budget",
    "discount",
    "savings",
    "quote",
)

_HIGH_RISK_PRICING_TOKENS = (
    "best discount",
    "lock it today",
    "lock today",
    "custom volume pricing",
    "across phases",
    "multi-phase",
    "multiphase",
    "junior pricing",
    "floor pricing",
    "promise",
    "commit",
)

_IMPOSSIBLE_CAPACITY_REQUEST_RE = re.compile(
    r"\b(?:promise|commit)\b.*\b\d{1,4}\b.*\b(?:senior|seniour|senoiur|senoir|staff|principal)\b.*\b(?:\d{1,3}\s*(?:day|days|week|weeks))\b.*\b(?:junior pricing|junior price|floor pricing|discount)\b",
    re.IGNORECASE,
)

_HIRING_COUNT_RE = re.compile(
    r"\b\d{1,4}\s+(?:engineering\s+)?(?:openings|roles|engineers|hires?)\b",
    re.IGNORECASE,
)

_SCHEDULING_TOKENS = (
    "book",
    "booking",
    "calendar",
    "slot",
    "time",
    "schedule",
    "sms",
    "text me",
)

_SIGNAL_TOKENS = (
    "funding",
    "raise",
    "raised",
    "series",
    "hiring",
    "maturity",
    "capability",
)

_BLOCK_SCORE_MAX = 2.4
_HUMAN_REVIEW_SCORE_MAX = 3.4


def _env_true(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def governance_enabled() -> bool:
    return _env_true("TENACIOUS_GOVERNANCE_ENABLED", default=True)


def governance_enforcement_enabled() -> bool:
    return _env_true("TENACIOUS_GOVERNANCE_ENFORCE", default=False)


def governance_runtime_status() -> dict:
    return {
        "tenacious_governance_enabled": governance_enabled(),
        "tenacious_governance_enforce": governance_enforcement_enabled(),
        "log_path": str(GOVERNANCE_LOG_PATH),
        "log_exists": GOVERNANCE_LOG_PATH.exists(),
    }


def governance_runtime_gate_decision(review: GovernanceReview) -> str | None:
    """Return a mandatory runtime gate decision when category-level evidence requires it.

    This allows the runtime to apply governance category protections even when
    TENACIOUS_GOVERNANCE_ENFORCE is disabled.
    """
    if review.final_decision != "allow":
        return review.final_decision

    for evidence in review.evidences:
        if evidence.supported:
            continue
        if evidence.evidence_id in {"unsupported_pricing_or_scope_claim", "hard_no_sequence_integrity"}:
            return "block"
        if evidence.evidence_id in {
            "reply_escalation_or_objection_failure",
            "legal_or_reference_escalation",
            "calendar_slot_handling",
            "tone_and_channel_policy_issues",
        } and evidence.severity in {"medium", "high", "critical"}:
            return "human_review"
        if evidence.evidence_id == "overclaimed_signal_or_maturity_claim" and evidence.severity in {
            "high",
            "critical",
        }:
            return "human_review"
        if evidence.evidence_id in {"generic_outreach_ungrounded", "style_and_tone_v2"} and evidence.severity in {
            "high",
            "critical",
        }:
            return "human_review"
    return None


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


def _extract_candidate_output(candidate_action: dict) -> str:
    return str(
        candidate_action.get("agent_output")
        or candidate_action.get("baseline_output")
        or ""
    )


def _extract_inbound_body(candidate_action: dict) -> str:
    return str(
        candidate_action.get("inbound_body")
        or candidate_action.get("inbound_message")
        or candidate_action.get("body")
        or ""
    )


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _tokenize_rubric_text(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z][a-z0-9_-]{3,}", text.lower())
        if token not in _STOPWORDS
    ]


def _select_keywords(counter: Counter[str], *, min_count: int, limit: int) -> list[str]:
    selected: list[str] = []
    for token, count in counter.most_common():
        if count < min_count:
            continue
        if token in _STOPWORDS:
            continue
        selected.append(token)
        if len(selected) >= limit:
            break
    return selected


def _safe_read_text(path: Path, *, max_chars: int = 300_000) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if len(raw) <= max_chars:
        return raw
    return raw[:max_chars]


@lru_cache(maxsize=1)
def _load_rubric_signals() -> dict:
    risk_fail_counters: dict[str, Counter[str]] = defaultdict(Counter)
    risk_pass_counters: dict[str, Counter[str]] = defaultdict(Counter)
    row_count = 0

    if TRAINING_RUBRIC_PATH.exists():
        for raw_line in TRAINING_RUBRIC_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            risk_focus = str(row.get("risk_focus") or "").strip().lower()
            if not risk_focus:
                continue

            expected_verdict = str(row.get("expected_verdict") or "").strip().lower()
            text_blob = "\n".join(
                str(row.get(field) or "")
                for field in ("prompt", "chosen", "rejected", "source_file_or_artifact")
            )
            tokens = _tokenize_rubric_text(text_blob)
            if not tokens:
                continue

            target = risk_pass_counters if expected_verdict == "pass" else risk_fail_counters
            target[risk_focus].update(tokens)
            row_count += 1

    risk_fail_keywords = {
        risk: _select_keywords(counter, min_count=3, limit=20)
        for risk, counter in risk_fail_counters.items()
    }
    risk_pass_keywords = {
        risk: _select_keywords(counter, min_count=2, limit=12)
        for risk, counter in risk_pass_counters.items()
    }

    policy_counter: Counter[str] = Counter()
    if TENACIOUS_DOCS_ROOT.exists():
        for path in TENACIOUS_DOCS_ROOT.rglob("*"):
            if path.suffix.lower() not in {".md", ".json", ".txt"}:
                continue
            text = _safe_read_text(path)
            if not text:
                continue
            for line in text.splitlines():
                lowered = line.strip().lower()
                if not lowered:
                    continue
                if any(marker in lowered for marker in ("must", "do not", "never", "forbid", "requires", "no ")):
                    policy_counter.update(_tokenize_rubric_text(lowered))

    policy_terms = _select_keywords(policy_counter, min_count=2, limit=80)

    return {
        "training_rows": row_count,
        "risk_fail_keywords": risk_fail_keywords,
        "risk_pass_keywords": risk_pass_keywords,
        "policy_terms": policy_terms,
    }


def _match_keywords(text: str, keywords: list[str], *, limit: int = 8) -> list[str]:
    if not text or not keywords:
        return []
    lowered = text.lower()
    matches: list[str] = []
    for keyword in keywords:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            matches.append(keyword)
        if len(matches) >= limit:
            break
    return matches


def _dominant_risk(matches: dict[str, list[str]]) -> tuple[str, int]:
    scored = sorted(
        ((risk, len(tokens)) for risk, tokens in matches.items() if tokens),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    if not scored:
        return "none", 0
    return scored[0]


def _risk_surface(candidate_output: str, inbound: str) -> dict[str, bool]:
    output_lower = candidate_output.lower()
    inbound_lower = inbound.lower()
    combined = f"{output_lower}\n{inbound_lower}"
    return {
        "pricing": _contains_any(combined, _PRICING_TOKENS) or bool(_PRICE_CLAIM_RE.search(candidate_output)),
        "legal_reference": _contains_any(combined, _LEGAL_TOKENS) or _contains_any(combined, _REFERENCE_TOKENS),
        "scheduling": _contains_any(combined, _SCHEDULING_TOKENS),
        "hard_no": _contains_any(inbound_lower, _HARD_NO_TOKENS),
        "signal": _contains_any(combined, _SIGNAL_TOKENS) or bool(_FUNDING_REF_RE.search(candidate_output)),
    }


def _infer_contextual_risk_focus(candidate_action: dict) -> str:
    output = _extract_candidate_output(candidate_action)
    inbound = _extract_inbound_body(candidate_action)
    output_lower = output.lower()
    action_type = str(candidate_action.get("action_type") or "").lower()

    if _contains_any(inbound.lower(), _HARD_NO_TOKENS):
        return "wrong_crm_hubspot_calendar_next_action"
    if _contains_any(inbound.lower(), _LEGAL_TOKENS) or _contains_any(inbound.lower(), _REFERENCE_TOKENS):
        return "reply_escalation_or_objection_failure"
    if _contains_any(f"{output_lower}\n{inbound.lower()}", _PRICING_TOKENS):
        return "unsupported_pricing_or_scope_claim"
    if action_type in {"calendar_action", "sms", "sms_reply"} or _contains_any(
        f"{output_lower}\n{inbound.lower()}",
        _SCHEDULING_TOKENS,
    ):
        return "wrong_crm_hubspot_calendar_next_action"
    if _contains_any(f"{output_lower}\n{inbound.lower()}", _SIGNAL_TOKENS):
        return "overclaimed_signal_or_maturity_claim"
    if _contains_any(output_lower, _GENERIC_TONE_TOKENS) or _contains_any(output_lower, _ASSERTIVE_OVERCLAIM_TOKENS):
        return "generic_outreach_ungrounded"
    return "none"


def _has_funding_signal(hiring_signal_brief: dict) -> bool:
    direct_keys = (
        "funding_event",
        "funding_or_restructure_signal",
        "funding_signal",
    )
    for key in direct_keys:
        value = str(hiring_signal_brief.get(key) or "").strip().lower()
        if value and any(token in value for token in ("fund", "raise", "series", "$", "m", "b")):
            return True

    if hiring_signal_brief.get("funding_event"):
        return True
    signals = hiring_signal_brief.get("signals")
    if isinstance(signals, list):
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            name = str(signal.get("name") or "").lower()
            summary = str(signal.get("summary") or "").strip()
            if (
                name == "funding_event"
                or any(token in name for token in ("fund", "raise", "series", "restructure"))
            ) and summary:
                return True
    return False


def _has_hiring_signal(hiring_signal_brief: dict) -> bool:
    direct_keys = (
        "job_post_velocity",
        "hiring_signal",
        "open_engineering_roles",
    )
    for key in direct_keys:
        value = str(hiring_signal_brief.get(key) or "").strip().lower()
        if value and any(token in value for token in ("open", "hiring", "role", "engineer")):
            return True

    signals = hiring_signal_brief.get("signals")
    if isinstance(signals, list):
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            name = str(signal.get("name") or "").lower()
            summary = str(signal.get("summary") or "").lower()
            if any(token in f"{name} {summary}" for token in ("open", "hiring", "role", "engineer", "job")):
                return True
    return False


def _soft_only_unsupported(evidences: list[GovernanceEvidence]) -> bool:
    unsupported = [item for item in evidences if not item.supported]
    if not unsupported:
        return False
    for item in unsupported:
        if item.evidence_id == "rubric_data_alignment":
            # Training-keyword alignment is advisory and should not block on its own.
            continue
        if item.evidence_id in {"overclaimed_signal_or_maturity_claim", "style_and_tone_v2"} and item.severity in {
            "low",
            "medium",
        }:
            continue
        return False
    return True


def _hedged_language_score(text: str) -> int:
    lowered = text.lower()
    terms = (
        "might",
        "may",
        "could",
        "based on",
        "likely",
        "suggest",
        "estimate",
        "directional",
    )
    return sum(1 for term in terms if term in lowered)


def _collect_detective_evidence(candidate_action: dict) -> list[GovernanceEvidence]:
    output = _extract_candidate_output(candidate_action)
    inbound = _extract_inbound_body(candidate_action)
    hiring_signal_brief = _safe_dict(candidate_action.get("hiring_signal_brief"))
    prospect_context = _safe_dict(candidate_action.get("prospect_context"))

    output_lower = output.lower()
    inbound_lower = inbound.lower()
    action_type = str(candidate_action.get("action_type") or "").lower()
    has_handoff_language = any(
        token in output_lower
        for token in (
            "cannot confirm",
            "can't confirm",
            "route",
            "delivery lead",
            "human review",
            "manual review",
            "before any commitment",
        )
    )

    evidences: list[GovernanceEvidence] = []

    high_risk_pricing_inbound = _contains_any(inbound_lower, _HIGH_RISK_PRICING_TOKENS)
    impossible_capacity_request = bool(_IMPOSSIBLE_CAPACITY_REQUEST_RE.search(inbound_lower))
    has_pricing_violation = (
        any(token in output_lower for token in ("discount", "savings guarantee", "fixed total"))
        or bool(_PRICE_CLAIM_RE.search(output))
        or (impossible_capacity_request and not has_handoff_language)
    )
    evidences.append(
        GovernanceEvidence(
            evidence_id="unsupported_pricing_or_scope_claim",
            detective="RepoInvestigator",
            finding=(
                "Candidate includes unsupported fixed pricing, discount, or guaranteed savings claim."
                if has_pricing_violation
                else "No unsupported fixed pricing or discount pattern detected."
            ),
            severity="critical" if has_pricing_violation else "low",
            supported=not has_pricing_violation,
            details=(
                "Pattern check for dollar totals, discount wording, guaranteed savings language, and "
                "impossible-capacity pricing requests that are not escalated to human review."
            ),
            cited_fields=["agent_output"],
            tags=["pricing_guardrail"],
        )
    )

    mentions_sms = any(token in output_lower for token in ("sms", "text me", "texted", "by text"))
    commits_calendar = any(
        token in output_lower
        for token in ("i booked", "booked a discovery call", "scheduled a", "held a slot", "reserved a slot")
    )
    sms_opt_in = any(token in inbound_lower for token in ("sms", "text me", "whatsapp", "call me", "phone me"))
    pricing_escalation_violation = high_risk_pricing_inbound and not has_handoff_language
    escalation_violation = (mentions_sms and not sms_opt_in) or commits_calendar or pricing_escalation_violation

    evidences.append(
        GovernanceEvidence(
            evidence_id="reply_escalation_or_objection_failure",
            detective="DocAnalyst",
            finding=(
                "Candidate fails escalation policy (unauthorized SMS/calendar or missing required human handoff)."
                if escalation_violation
                else "No unauthorized SMS/calendar escalation pattern detected."
            ),
            severity="high" if escalation_violation else "low",
            supported=not escalation_violation,
            details=(
                "Checks consent-gated escalation, premature booking commitments, and mandatory human handoff "
                "for high-risk pricing/concession requests."
            ),
            cited_fields=["agent_output", "inbound_body"],
            tags=["channel_gating"],
        )
    )

    generic_overclaim = any(
        token in output_lower
        for token in (
            "world-class",
            "top talent",
            "any stack",
            "60 engineers ready",
            "deploy in 7-14 days",
            "deploy in 7–14 days",
        )
    )
    evidences.append(
        GovernanceEvidence(
            evidence_id="generic_outreach_ungrounded",
            detective="VisionInspector",
            finding=(
                "Candidate uses generic or unsupported bench-capacity language."
                if generic_overclaim
                else "No generic overclaim language detected."
            ),
            severity="medium" if generic_overclaim else "low",
            supported=not generic_overclaim,
            details="Checks for unsupported universal capability and urgency claims.",
            cited_fields=["agent_output"],
            tags=["grounding"],
        )
    )

    references_funding = bool(_FUNDING_REF_RE.search(output)) or "series " in output_lower
    references_hiring = bool(_HIRING_COUNT_RE.search(output))
    try:
        prospect_ai_maturity = int(float(prospect_context.get("ai_maturity_score") or 0)) if prospect_context else 0
    except (TypeError, ValueError):
        prospect_ai_maturity = 0
    maturity_overclaim = (
        any(token in output_lower for token in ("high ai maturity", "advanced ai maturity", "industry-leading ai maturity"))
        and prospect_ai_maturity < 3
    )
    funding_supported = not references_funding or _has_funding_signal(hiring_signal_brief)
    hiring_supported = not references_hiring or _has_hiring_signal(hiring_signal_brief)
    signal_supported = funding_supported and hiring_supported and not maturity_overclaim
    signal_severity = "low"
    if not signal_supported:
        if maturity_overclaim or (references_funding and not funding_supported):
            signal_severity = "high"
        else:
            signal_severity = "medium"
    evidences.append(
        GovernanceEvidence(
            evidence_id="overclaimed_signal_or_maturity_claim",
            detective="RepoInvestigator",
            finding=(
                "Candidate references funding/hiring/maturity signals without matching evidence in structured context."
                if not signal_supported
                else "Signal references appear consistent with available hiring brief evidence."
            ),
            severity=signal_severity,
            supported=signal_supported,
            details=(
                "Cross-checks funding, hiring-volume, and AI maturity claims against structured prospect and "
                "hiring signal evidence."
            ),
            cited_fields=["agent_output", "hiring_signal_brief"],
            tags=["signal_grounding"],
        )
    )

    missing_context = not prospect_context or not hiring_signal_brief
    evidences.append(
        GovernanceEvidence(
            evidence_id="missing_runtime_context",
            detective="DocAnalyst",
            finding=(
                "Candidate review context is incomplete; route to human for conservative handling."
                if missing_context
                else "Prospect and signal context available for grounded review."
            ),
            severity="medium" if missing_context else "low",
            supported=not missing_context,
            details="Presence check for prospect_context and hiring_signal_brief payloads.",
            cited_fields=["prospect_context", "hiring_signal_brief"],
            tags=["evidence_quality"],
        )
    )

    legal_inbound = _contains_any(inbound_lower, _LEGAL_TOKENS)
    reference_inbound = _contains_any(inbound_lower, _REFERENCE_TOKENS)
    hard_handoff_refusal = any(token in output_lower for token in ("cannot", "can't", "route", "human", "delivery lead"))
    legal_acceptance = legal_inbound and any(
        token in output_lower
        for token in ("we can agree", "we agree", "we accept", "i can confirm", "i will sign")
    )
    reference_commitment = reference_inbound and any(
        token in output_lower
        for token in ("i will send", "i can send", "here is a client", "we have a healthcare")
    )
    legal_or_reference_violation = (legal_acceptance or reference_commitment) and not hard_handoff_refusal

    evidences.append(
        GovernanceEvidence(
            evidence_id="legal_or_reference_escalation",
            detective="DocAnalyst",
            finding=(
                "Candidate appears to commit legal/security terms or client references without required human handoff."
                if legal_or_reference_violation
                else "Legal/reference handling appears to preserve human handoff boundaries."
            ),
            severity="high" if legal_or_reference_violation else "low",
            supported=not legal_or_reference_violation,
            details="Warm reply policy requires human handling for legal terms and named-sector references.",
            cited_fields=["agent_output", "inbound_body"],
            tags=["reply_escalation_or_objection_failure", "policy_safety"],
        )
    )

    hard_no_detected = _contains_any(inbound_lower, _HARD_NO_TOKENS)
    suppression_language = any(token in output_lower for token in ("opted_out", "suppress", "no reply", "silently"))
    hard_no_violation = hard_no_detected and bool(output.strip()) and not suppression_language

    evidences.append(
        GovernanceEvidence(
            evidence_id="hard_no_sequence_integrity",
            detective="RepoInvestigator",
            finding=(
                "Hard-no reply appears to continue outreach flow instead of opt-out suppression handling."
                if hard_no_violation
                else "No hard-no sequence integrity issue detected."
            ),
            severity="high" if hard_no_violation else "low",
            supported=not hard_no_violation,
            details="Hard-no handling requires no outbound reply plus suppression updates.",
            cited_fields=["inbound_body", "agent_output"],
            tags=["wrong_crm_hubspot_calendar_next_action"],
        )
    )

    word_count = len(re.findall(r"\b\w+\b", output))
    style_issues: list[str] = []
    if _contains_any(output_lower, _GENERIC_TONE_TOKENS):
        style_issues.append("generic_subject_or_followup_pattern")
    if _contains_any(output_lower, _ASSERTIVE_OVERCLAIM_TOKENS):
        style_issues.append("condescending_or_overclaim_gap_framing")
    if "bench" in output_lower:
        style_issues.append("internal_jargon_bench")
    if output_lower.count("?") > 1:
        style_issues.append("multi_ask_pattern")
    if action_type in {"cold_outreach", "initial_outreach"} and word_count > 120:
        style_issues.append("cold_word_count_exceeded")
    elif action_type not in {"cold_outreach", "initial_outreach"} and word_count > 160:
        style_issues.append("warm_word_count_exceeded")

    style_severity = "low"
    if len(style_issues) >= 3:
        style_severity = "high"
    elif len(style_issues) >= 2:
        style_severity = "medium"

    evidences.append(
        GovernanceEvidence(
            evidence_id="style_and_tone_v2",
            detective="VisionInspector",
            finding=(
                "Candidate drifted from Tenacious v2 style constraints (direct, grounded, non-condescending)."
                if style_issues
                else "Candidate appears aligned with Tenacious v2 style constraints."
            ),
            severity=style_severity,
            supported=not style_issues,
            details=(
                "Style issues detected: " + ", ".join(style_issues)
                if style_issues
                else "No major tone or formatting drift detected."
            ),
            cited_fields=["agent_output"],
            tags=["generic_outreach_ungrounded", "overclaimed_signal_or_maturity_claim"],
        )
    )

    channel_policy_violation = (
        action_type in {"email", "email_reply"}
        and (mentions_sms or commits_calendar)
        and not sms_opt_in
    )
    evidences.append(
        GovernanceEvidence(
            evidence_id="tone_and_channel_policy_issues",
            detective="DocAnalyst",
            finding=(
                "Candidate mixes channel directives or policy tone in a way that violates channel-handling rules."
                if channel_policy_violation
                else "No tone/channel policy issue detected for this channel context."
            ),
            severity="high" if channel_policy_violation else "low",
            supported=not channel_policy_violation,
            details="Checks for channel-policy drift such as unsolicited SMS/calendar directives in email context.",
            cited_fields=["agent_output", "inbound_body"],
            tags=["tone_and_channel_policy_issues", "wrong_crm_hubspot_calendar_next_action"],
        )
    )

    slot_phrase = bool(re.search(r"\b(mon|tues|wednes|thurs|fri|satur|sun)\w*\b", inbound_lower))
    explicit_time = bool(re.search(r"\b\d{1,2}(?::\d{2})?\s?(am|pm)\b", inbound_lower))
    generic_calendar_redirect = (
        slot_phrase
        and explicit_time
        and ("cal.com" in output_lower or "choose" in output_lower)
        and not any(day in output_lower for day in ("monday", "tuesday", "wednesday", "thursday", "friday"))
    )

    evidences.append(
        GovernanceEvidence(
            evidence_id="calendar_slot_handling",
            detective="DocAnalyst",
            finding=(
                "Candidate appears to ignore specific scheduling signal and routes to generic booking flow."
                if generic_calendar_redirect
                else "No specific-slot calendar handling issue detected."
            ),
            severity="medium" if generic_calendar_redirect else "low",
            supported=not generic_calendar_redirect,
            details="Warm scheduling policy prefers confirming explicit slot evidence before generic re-book flows.",
            cited_fields=["inbound_body", "agent_output"],
            tags=["wrong_crm_hubspot_calendar_next_action"],
        )
    )

    rubric_signals = _load_rubric_signals()
    combined_text = f"{output}\n{inbound}"
    risk_fail_matches = {
        risk: _match_keywords(combined_text, keywords)
        for risk, keywords in rubric_signals["risk_fail_keywords"].items()
    }
    risk_pass_matches = {
        risk: _match_keywords(combined_text, keywords)
        for risk, keywords in rubric_signals["risk_pass_keywords"].items()
    }
    fail_hits = sum(len(tokens) for tokens in risk_fail_matches.values())
    pass_hits = sum(len(tokens) for tokens in risk_pass_matches.values())
    dominant_risk, dominant_risk_hits = _dominant_risk(risk_fail_matches)

    rubric_severity = "low"
    if fail_hits > pass_hits + 2:
        rubric_severity = "high"
    elif fail_hits > pass_hits:
        rubric_severity = "medium"

    evidences.append(
        GovernanceEvidence(
            evidence_id="rubric_data_alignment",
            detective="RepoInvestigator",
            finding=(
                "Candidate aligns with pass-side rubric cues mined from combined v02 training preferences."
                if pass_hits >= fail_hits
                else "Candidate aligns more strongly with fail-side rubric cues from combined v02 training preferences."
            ),
            severity=rubric_severity,
            supported=pass_hits >= fail_hits,
            details=(
                f"rows={rubric_signals['training_rows']}, dominant_risk={dominant_risk}, "
                f"dominant_hits={dominant_risk_hits}, fail_hits={fail_hits}, pass_hits={pass_hits}"
            ),
            cited_fields=["agent_output", "inbound_body"],
            tags=[dominant_risk] if dominant_risk in _RISK_FOCUS_KEYS else ["rubric_alignment"],
        )
    )

    return evidences


def _severity_counts(evidences: list[GovernanceEvidence]) -> dict[str, int]:
    counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for evidence in evidences:
        counts[evidence.severity] += 1
    return counts


def _judge_prosecutor(
    evidences: list[GovernanceEvidence],
    candidate_output: str,
    inbound: str,
) -> GovernanceJudicialOpinion:
    counts = _severity_counts(evidences)
    unsupported_count = sum(1 for evidence in evidences if not evidence.supported)
    surface = _risk_surface(candidate_output, inbound)
    complexity_penalty = max(0, sum(1 for value in surface.values() if value) - 1)
    handoff_bonus = 1 if _contains_any(candidate_output.lower(), _HANDOFF_TOKENS) and complexity_penalty else 0
    length_penalty = 1 if len(re.findall(r"\b\w+\b", candidate_output)) > 170 else 0
    score = max(
        1,
        5
        - (
            counts["critical"] * 3
            + counts["high"] * 2
            + counts["medium"]
            + max(0, unsupported_count - 2) // 2
            + complexity_penalty
            + length_penalty
            - handoff_bonus
        ),
    )
    if counts["critical"] > 0 or counts["high"] > 0:
        verdict = "fail"
    elif counts["medium"] > 0:
        verdict = "needs_human_review"
    else:
        verdict = "pass"
    return GovernanceJudicialOpinion(
        judge="Prosecutor",
        criterion_id="sales_runtime_governance",
        score=score,
        verdict=verdict,
        argument=(
            "Strict risk lens prioritizes policy-safe behavior and penalizes unresolved evidence across pricing,"
            " escalation, and CRM actions."
        ),
        cited_evidence=[e.evidence_id for e in evidences if e.severity in {"critical", "high", "medium"}],
    )


def _judge_defense(evidences: list[GovernanceEvidence], candidate_output: str) -> GovernanceJudicialOpinion:
    counts = _severity_counts(evidences)
    output_lower = candidate_output.lower()
    word_count = len(re.findall(r"\b\w+\b", candidate_output))
    has_direct_ask = "?" in candidate_output
    has_handoff_language = any(token in output_lower for token in _HANDOFF_TOKENS)
    hedge_score = _hedged_language_score(candidate_output)

    quality_bonus = 0
    if word_count <= 140:
        quality_bonus += 1
    if has_direct_ask:
        quality_bonus += 1
    if has_handoff_language or hedge_score > 0:
        quality_bonus += 1

    base = 2 + quality_bonus
    penalty = counts["critical"] * 2 + counts["high"] + (counts["medium"] // 2)
    score = max(1, min(5, base - penalty))
    if counts["critical"] > 0:
        verdict = "fail"
    elif counts["high"] > 0 and not has_handoff_language:
        verdict = "needs_human_review"
    else:
        verdict = "pass" if score >= 3 else "needs_human_review"
    return GovernanceJudicialOpinion(
        judge="Defense",
        criterion_id="sales_runtime_governance",
        score=score,
        verdict=verdict,
        argument=(
            "Execution lens rewards concise, context-aware responses with explicit handoff language when risk"
            " boundaries are touched."
        ),
        cited_evidence=[e.evidence_id for e in evidences if not e.supported],
    )


def _judge_tech_lead(
    evidences: list[GovernanceEvidence],
    candidate_output: str,
    inbound: str,
) -> GovernanceJudicialOpinion:
    counts = _severity_counts(evidences)
    unsupported_count = sum(1 for evidence in evidences if not evidence.supported)
    surface = _risk_surface(candidate_output, inbound)
    complexity = sum(1 for value in surface.values() if value)
    has_handoff_language = _contains_any(candidate_output.lower(), _HANDOFF_TOKENS)
    word_count = len(re.findall(r"\b\w+\b", candidate_output))

    if counts["critical"] > 0:
        score = 1
        verdict = "fail"
    elif counts["high"] > 1:
        score = 2
        verdict = "fail"
    elif counts["high"] == 1 or counts["medium"] > 2:
        score = 3
        verdict = "needs_human_review"
    elif counts["medium"] == 1:
        score = 4
        verdict = "needs_human_review"
    else:
        if complexity >= 3 and not has_handoff_language:
            score = 4
        elif word_count > 180:
            score = 4
        else:
            score = 5 if unsupported_count == 0 else 4
        verdict = "pass"
    return GovernanceJudicialOpinion(
        judge="TechLead",
        criterion_id="sales_runtime_governance",
        score=score,
        verdict=verdict,
        argument=(
            "Pragmatic lens emphasizes deterministic state safety and whether the draft can be executed without"
            " violating runtime governance rules."
        ),
        cited_evidence=[e.evidence_id for e in evidences if e.severity != "low"],
    )


def _primary_risk_focus(evidences: list[GovernanceEvidence], candidate_action: dict) -> str:
    contextual = _infer_contextual_risk_focus(candidate_action)
    ranked = sorted(
        [item for item in evidences if not item.supported],
        key=lambda item: (_SEVERITY_RANK[item.severity], item.evidence_id),
        reverse=True,
    )
    if not ranked:
        return contextual
    top = ranked[0]
    if top.severity == "low":
        return contextual
    if top.evidence_id == "rubric_data_alignment" and contextual != "none":
        return contextual
    for tag in top.tags:
        if tag in _RISK_FOCUS_KEYS:
            return tag
    return contextual if contextual != "none" else top.evidence_id


def _remediation_plan(evidences: list[GovernanceEvidence]) -> list[str]:
    remediation_map = {
        "unsupported_pricing_or_scope_claim": "Replace fixed totals, discounts, and savings guarantees with public bands and route scoped pricing to a delivery lead.",
        "reply_escalation_or_objection_failure": "Require explicit SMS/calendar consent and avoid booking commitments before prospect confirmation.",
        "generic_outreach_ungrounded": "Replace generic vendor superlatives with one grounded signal from the hiring or competitor brief.",
        "overclaimed_signal_or_maturity_claim": "Only reference funding or maturity signals that exist in the structured hiring brief.",
        "missing_runtime_context": "Attach prospect_context and hiring_signal_brief to candidate review payloads before automated decisioning.",
        "legal_or_reference_escalation": "For legal/security/reference requests, acknowledge the question and route to a human delivery lead without committing terms in-email.",
        "hard_no_sequence_integrity": "When a prospect opts out, send no reply and apply opted-out + suppression updates immediately.",
        "style_and_tone_v2": "Use concise subject/body structure, avoid condescending framing, and keep one clear ask with grounded evidence.",
        "calendar_slot_handling": "When inbound includes a specific slot, confirm or clarify that slot before sending a generic booking redirect.",
        "tone_and_channel_policy_issues": "Keep channel behavior policy-consistent: do not introduce SMS/calendar directives without consent or required handoff.",
        "rubric_data_alignment": "Rephrase toward pass-side rubric patterns: grounded facts, confidence-aware language, and explicit human handoff at policy boundaries.",
    }
    seen: set[str] = set()
    plan: list[str] = []
    for evidence in evidences:
        if evidence.supported:
            continue
        recommendation = remediation_map.get(evidence.evidence_id)
        if recommendation and recommendation not in seen:
            plan.append(recommendation)
            seen.add(recommendation)
    if not plan:
        plan.append("No major governance issues detected; continue monitoring with shadow reviews.")
    return plan


def _resolve_chief_justice(
    evidences: list[GovernanceEvidence],
    opinions: list[GovernanceJudicialOpinion],
) -> tuple[str, str, float, str | None, list[str]]:
    rules_applied: list[str] = []
    scores = [opinion.score for opinion in opinions]
    variance = max(scores) - min(scores)

    if any(item.evidence_id == "unsupported_pricing_or_scope_claim" and not item.supported for item in evidences):
        rules_applied.append("security_override")
        overall_score = min(3.0, mean(scores))
        dissent = (
            "Security rule applied: unsupported pricing claim overrides optimistic arguments."
            if variance > 2
            else None
        )
        return "fail", "block", overall_score, dissent, rules_applied

    if any(item.evidence_id == "hard_no_sequence_integrity" and not item.supported for item in evidences):
        rules_applied.append("opt_out_override")
        overall_score = min(3.0, mean(scores))
        dissent = (
            "Opt-out integrity rule applied: hard-no reply must not continue automated outreach flow."
            if variance > 2
            else None
        )
        return "fail", "block", overall_score, dissent, rules_applied

    if any(item.evidence_id == "legal_or_reference_escalation" and not item.supported for item in evidences):
        rules_applied.append("legal_handoff_override")
        overall_score = min(3.0, mean(scores))
        dissent = (
            "Legal/reference escalation rule applied: requires human follow-up before send."
            if variance > 2
            else None
        )
        return "needs_human_review", "human_review", overall_score, dissent, rules_applied

    if any(
        item.evidence_id == "reply_escalation_or_objection_failure"
        and not item.supported
        and item.severity in {"medium", "high", "critical"}
        for item in evidences
    ):
        rules_applied.append("reply_escalation_override")
        overall_score = min(3.2, mean(scores))
        dissent = (
            "Escalation policy override applied: this reply requires human review before outbound send."
            if variance > 2
            else None
        )
        return "needs_human_review", "human_review", overall_score, dissent, rules_applied

    if any(
        item.evidence_id == "calendar_slot_handling"
        and not item.supported
        and item.severity in {"medium", "high", "critical"}
        for item in evidences
    ):
        rules_applied.append("calendar_next_action_override")
        overall_score = min(3.2, mean(scores))
        return "needs_human_review", "human_review", overall_score, None, rules_applied

    if any(
        item.evidence_id == "overclaimed_signal_or_maturity_claim"
        and not item.supported
        and item.severity in {"high", "critical"}
        for item in evidences
    ):
        rules_applied.append("signal_claim_override")
        overall_score = min(3.2, mean(scores))
        return "needs_human_review", "human_review", overall_score, None, rules_applied

    if any(
        item.evidence_id == "tone_and_channel_policy_issues"
        and not item.supported
        and item.severity in {"medium", "high", "critical"}
        for item in evidences
    ):
        rules_applied.append("tone_channel_policy_override")
        overall_score = min(3.2, mean(scores))
        return "needs_human_review", "human_review", overall_score, None, rules_applied

    if any(
        item.evidence_id in {"generic_outreach_ungrounded", "style_and_tone_v2"}
        and not item.supported
        and item.severity in {"high", "critical"}
        for item in evidences
    ):
        rules_applied.append("grounding_tone_override")
        overall_score = min(3.3, mean(scores))
        return "needs_human_review", "human_review", overall_score, None, rules_applied

    if any(item.evidence_id == "missing_runtime_context" and not item.supported for item in evidences):
        rules_applied.append("fact_supremacy")
        overall_score = min(3.0, mean(scores))
        dissent = (
            "Evidence quality rule applied: missing context requires human review before automated execution."
            if variance > 2
            else None
        )
        return "needs_human_review", "human_review", overall_score, dissent, rules_applied

    if _soft_only_unsupported(evidences):
        rules_applied.append("soft_signal_tolerance")
        overall_score = max(3.8, mean(scores))
        return "pass", "allow", overall_score, None, rules_applied

    overall_score = mean(scores)
    verdict_counts = {"pass": 0, "fail": 0, "needs_human_review": 0}
    for opinion in opinions:
        verdict_counts[opinion.verdict] += 1

    if verdict_counts["fail"] >= 2:
        final_verdict = "fail"
    elif verdict_counts["pass"] >= 2:
        final_verdict = "pass"
    else:
        final_verdict = "needs_human_review"

    rules_applied.append("majority_verdict")
    threshold_decision: str
    threshold_verdict: str
    if overall_score <= _BLOCK_SCORE_MAX:
        threshold_decision = "block"
        threshold_verdict = "fail"
    elif overall_score <= _HUMAN_REVIEW_SCORE_MAX:
        threshold_decision = "human_review"
        threshold_verdict = "needs_human_review"
    else:
        threshold_decision = "allow"
        threshold_verdict = "pass"

    final_decision = threshold_decision
    if final_verdict != threshold_verdict:
        rules_applied.append("score_threshold_override")
    final_verdict = threshold_verdict
    rules_applied.append("score_threshold_mapping")

    dissent = None
    if variance > 2:
        rules_applied.append("variance_re_evaluation")
        dissent = (
            "Judges diverged materially; chief-justice applied deterministic tie-break rules before final decision."
        )

    return final_verdict, final_decision, overall_score, dissent, rules_applied


def _calibrate_overall_score(
    base_score: float,
    evidences: list[GovernanceEvidence],
    *,
    candidate_action: dict,
    candidate_output: str,
    inbound: str,
    final_decision: str,
) -> float:
    surface = _risk_surface(candidate_output, inbound)
    supported_low = sum(1 for evidence in evidences if evidence.supported and evidence.severity == "low")
    unsupported_count = sum(1 for evidence in evidences if not evidence.supported)
    word_count = len(re.findall(r"\b\w+\b", candidate_output))
    action_type = str(candidate_action.get("action_type") or "").lower()

    adjustment = 0.0
    if final_decision == "allow":
        adjustment += min(0.3, supported_low * 0.04)
        if surface["pricing"]:
            adjustment -= 0.12
        if surface["scheduling"]:
            adjustment -= 0.08
        if surface["signal"] and "?" in candidate_output:
            adjustment += 0.05
        if _contains_any(candidate_output.lower(), _HANDOFF_TOKENS):
            adjustment += 0.05
        if action_type in {"email_reply", "email"} and word_count > 170:
            adjustment -= 0.08
    elif final_decision == "human_review":
        adjustment -= 0.1
        adjustment -= min(0.25, unsupported_count * 0.05)
        if surface["legal_reference"] or surface["hard_no"]:
            adjustment -= 0.12
    else:  # block
        adjustment -= 0.18
        adjustment -= min(0.35, unsupported_count * 0.06)

    calibrated = max(1.0, min(5.0, base_score + adjustment))
    return round(calibrated, 2)


def append_governance_review_log(review: GovernanceReview) -> None:
    GOVERNANCE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GOVERNANCE_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(review.model_dump(mode="json"), ensure_ascii=False) + "\n")


def read_governance_reviews(limit: int = 50) -> list[dict]:
    if not GOVERNANCE_LOG_PATH.exists():
        return []
    rows: list[dict] = []
    for line in GOVERNANCE_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:][::-1]


def review_candidate_action(candidate_action: dict) -> GovernanceReview:
    candidate_output = _extract_candidate_output(candidate_action)
    channel = str(candidate_action.get("channel") or "email")
    action_type = str(candidate_action.get("action_type") or "email_reply")
    prospect_context = _safe_dict(candidate_action.get("prospect_context"))
    prospect_id = str(candidate_action.get("prospect_id") or prospect_context.get("prospect_id") or "")

    if not governance_enabled():
        review = GovernanceReview(
            review_id=f"gov_{uuid4().hex[:16]}",
            timestamp_utc=_utc_now(),
            prospect_id=prospect_id or None,
            company_name=str(candidate_action.get("company_name") or prospect_context.get("company_name") or "") or None,
            candidate_action_type=action_type,
            candidate_channel=channel,
            candidate_output=candidate_output,
            primary_risk_focus="none",
            overall_score=5.0,
            final_verdict="pass",
            final_decision="allow",
            remediation_plan=["Governance sidecar disabled; no courtroom review executed."],
            rules_applied=["governance_disabled"],
            governance_enabled=False,
            enforcement_applied=False,
            enforcement_reason="TENACIOUS_GOVERNANCE_ENABLED=false",
            evidences=[],
            opinions=[],
        )
        append_governance_review_log(review)
        return review

    evidences = _collect_detective_evidence(candidate_action)
    inbound = _extract_inbound_body(candidate_action)
    opinions = [
        _judge_prosecutor(evidences, candidate_output, inbound),
        _judge_defense(evidences, candidate_output),
        _judge_tech_lead(evidences, candidate_output, inbound),
    ]

    final_verdict, final_decision, overall_score, dissent, rules_applied = _resolve_chief_justice(
        evidences,
        opinions,
    )
    calibrated_score = _calibrate_overall_score(
        overall_score,
        evidences,
        candidate_action=candidate_action,
        candidate_output=candidate_output,
        inbound=inbound,
        final_decision=final_decision,
    )

    enforce = governance_enforcement_enabled() and final_decision != "allow"
    review = GovernanceReview(
        review_id=f"gov_{uuid4().hex[:16]}",
        timestamp_utc=_utc_now(),
        prospect_id=prospect_id or None,
        company_name=str(candidate_action.get("company_name") or prospect_context.get("company_name") or "") or None,
        candidate_action_type=action_type,
        candidate_channel=channel,
        candidate_output=candidate_output,
        primary_risk_focus=_primary_risk_focus(evidences, candidate_action),
        overall_score=calibrated_score,
        final_verdict=final_verdict,
        final_decision=final_decision,
        dissent_summary=dissent,
        remediation_plan=_remediation_plan(evidences),
        rules_applied=rules_applied,
        governance_enabled=True,
        enforcement_applied=enforce,
        enforcement_reason=(
            "TENACIOUS_GOVERNANCE_ENFORCE=true and final decision is not allow"
            if enforce
            else None
        ),
        evidences=evidences,
        opinions=opinions,
    )
    append_governance_review_log(review)
    return review
