from agent.channels.email import email_channel
from agent.channels.sms import sms_channel
from agent.channels.voice import voice_channel
from agent.generation.service import generation_service
from agent.schemas.briefs import ProspectEnrichmentResponse
from agent.schemas.conversation import ConversationDecision
from agent.schemas.prospect import InboundMessageRequest
from agent.schemas.tools import ToolExecutionResult
from agent.seed.loader import seed_materials
from agent.scheduling.calcom import calcom_client
from agent.scheduling.context_brief import context_brief_generator
from agent.storage.repository import ProspectRepository
import re

# ---------------------------------------------------------------------------
# SMS eligibility policy
# ---------------------------------------------------------------------------
# SMS is only used after the thread is already warm AND the booking link has
# first been delivered by email on a prior turn. Explicit SMS requests do not
# bypass that sequencing rule.
#
# Practical effect:
#   1. First scheduling turn: share booking link by email.
#   2. Later turn: if the prospect asks for SMS/text and a phone number exists,
#      SMS may be attempted.
#
# SMS is never sent on initial outreach.
# SMS is never used to carry the first booking link.
# ---------------------------------------------------------------------------

_SMS_OPT_IN_TOKENS = ("sms", "text me", "whatsapp", "call me", "phone me")
_VOICE_OPT_IN_TOKENS = ("voice", "phone call", "give me a call", "ring me", "call me", "phone me")
_SCHEDULING_TOKENS = ("call", "calendar", "meet", "meeting", "schedule", "next week", "tomorrow", "book")
_SMS_OPT_IN_PATTERN = re.compile(
    r"\b(?:sms|text me|text now|send(?: me)?(?: an?)? (?:sms|text)|can (?:you|u) text|whatsapp|call me|phone me)\b",
    re.IGNORECASE,
)
_SMS_LOGISTICS_HINT_TOKENS = (
    "link",
    "booking",
    "book",
    "calendar",
    "slot",
    "time",
    "meeting",
    "call",
    "schedule",
)
_SMS_CONTENT_REQUEST_TOKENS = (
    "offer",
    "pricing",
    "price",
    "cost",
    "quote",
    "details",
    "detail",
    "overview",
    "information",
    "info",
    "proposal",
    "services",
    "what do you",
    "what offer",
    "what are you going",
)

# ---------------------------------------------------------------------------
# Pricing objection tokens — match before checking for scheduling intent
# ---------------------------------------------------------------------------
_PRICING_TOKENS = ("price", "pricing", "cost", "rate", "budget", "how much", "cheaper", "expensive")

# ---------------------------------------------------------------------------
# Offshore concern tokens — triggers transcript-grounded response
# ---------------------------------------------------------------------------
_OFFSHORE_CONCERN_TOKENS = (
    "offshore", "outsource", "india", "eastern europe", "quality concerns",
    "rotation", "vendor", "timezone", "time zone",
)

_SOFT_DEFER_TOKENS = (
    "not right now", "maybe later", "not the right time", "check back",
    "too busy", "reach out in", "q3", "q4", "next quarter", "next year",
    "not a priority", "come back", "not today", "another time",
)

_CURIOUS_TOKENS = (
    "tell me more", "what do you do", "how does it work", "what exactly",
    "more information", "can you elaborate", "what is tenacious",
    "how does this work", "what's included", "what does this look like",
    "interested in learning", "curious about",
)

_DIFFERENTIATION_TOKENS = (
    "what makes tenacious different", "what makes you different",
    "what makes this different", "why tenacious", "how are you different",
    "different from", "why are you different",
)

_CAPABILITY_TOKENS = (
    "capability gap",
    "ai/ml capability",
    "ai ml capability",
    "machine learning engineer",
    "ml engineer",
    "ai engineer",
    "need ml",
    "need ai",
)

_MODELING_FOCUS_TOKENS = (
    "modeling",
    "model gap",
    "model quality",
    "fine-tuning",
    "fine tuning",
    "training",
    "inference",
    "evaluation",
)

_MLOPS_FOCUS_TOKENS = (
    "mlops",
    "ml ops",
    "model ops",
    "deployment",
    "serving",
    "monitoring",
    "experiment tracking",
)

_DATA_PIPELINE_FOCUS_TOKENS = (
    "data pipeline",
    "data pipelines",
    "feature pipeline",
    "feature pipelines",
    "ingestion",
    "etl",
    "elt",
    "feature store",
    "training data",
)

_APPLIED_ML_FOCUS_TOKENS = (
    "applied ml",
    "ml feature",
    "ml features",
    "ai feature",
    "ai features",
    "recommendation",
    "forecasting",
    "classification",
    "document intelligence",
)

_UPDATE_TOKENS = (
    "any update", "do you have an update", "following do you have an update",
    "checking for an update", "checking on this", "where do things stand",
)

_LEGAL_HANDOFF_TOKENS = (
    "dpa",
    "data processing addendum",
    "msa",
    "redline",
    "redlines",
    "contract terms",
    "legal terms",
    "indemnity",
    "soc2",
    "hipaa",
    "security questionnaire",
    "security packet",
    "compliance proof",
    "client reference",
    "named reference",
)

_CUSTOM_PRICING_SCOPE_TOKENS = (
    "custom volume pricing",
    "volume pricing",
    "across phases",
    "multi-phase",
    "multiphase",
    "bulk pricing",
    "custom pricing",
    "enterprise pricing",
)

_URGENT_CONCESSION_TOKENS = (
    "best discount",
    "lock it today",
    "lock today",
    "today only",
    "urgent pricing",
    "special price now",
)

_IMPOSSIBLE_CAPACITY_PATTERN = re.compile(
    r"\b(?:promise|commit)\b.*\b\d{1,4}\b.*\b(?:senior|seniour|senoiur|senoir|staff|principal)\b.*\b(?:\d{1,3}\s*(?:day|days|week|weeks))\b.*\b(?:junior pricing|junior price|floor pricing|discount)\b",
    re.IGNORECASE,
)

_CAPACITY_HEADCOUNT_PATTERN = re.compile(
    r"\b(\d{1,4})\s+(?:senior|seniour|senoiur|senoir|staff|principal)\s+(?:engineer|engineers|developer|developers|dev|devs)\b",
    re.IGNORECASE,
)

_TIMELINE_PATTERN = re.compile(
    r"\b(\d{1,3})\s*(day|days|week|weeks)\b",
    re.IGNORECASE,
)

_HARD_NO_TOKENS = (
    "not interested",
    "remove me",
    "remove us",
    "stop contacting",
    "do not contact",
)

_GLOBAL_CORRECTION_MEMORY_SOURCES = [
    "week2_governance",
    "week8_handoff",
    "week11_judge",
]


class ChannelHandoffManager:
    """Centralized state machine for channel transitions and warm-lead gating."""

    def __init__(self, repository: ProspectRepository) -> None:
        self.repository = repository

    def current_state(self, prospect_id: str) -> str:
        if self.repository.has_interaction_event(prospect_id, "booking_confirmed"):
            return "booked"
        if self.repository.has_interaction_event(prospect_id, "voice_handoff_sent"):
            return "voice_handoff_active"
        if self.repository.has_interaction_event(prospect_id, "sms_handoff_sent"):
            return "sms_handoff_active"
        if self.repository.has_interaction_event(prospect_id, "email_reply_received"):
            return "warm_lead_ready_for_sms"
        if self.repository.has_interaction_event(prospect_id, "email_sent"):
            return "email_only"
        return "new"

    def can_send_sms(self, prospect_id: str) -> bool:
        """Base gate: returns True if the prospect has replied via email or SMS."""
        return self.repository.has_interaction_event(
            prospect_id, "email_reply_received"
        ) or self.repository.has_interaction_event(prospect_id, "sms_reply_received")

    def _booking_link_was_shared_by_email(self, prospect_id: str) -> bool:
        return self.repository.has_interaction_event(prospect_id, "booking_link_shared")

    def _has_sms_opt_in_request(self, message_body: str) -> bool:
        return bool(_SMS_OPT_IN_PATTERN.search(message_body))

    def _is_sms_content_request(self, message_body: str) -> bool:
        lowered = message_body.lower()
        return self._has_sms_opt_in_request(lowered) and any(
            token in lowered for token in _SMS_CONTENT_REQUEST_TOKENS
        )

    def _is_sms_booking_followup_request(self, prospect_id: str, message_body: str) -> bool:
        lowered = message_body.lower()
        if not self._has_sms_opt_in_request(lowered):
            return False
        if self._is_sms_content_request(lowered):
            return False
        return any(token in lowered for token in _SMS_LOGISTICS_HINT_TOKENS)

    def _is_generic_sms_request(self, message_body: str) -> bool:
        lowered = message_body.lower()
        return self._has_sms_opt_in_request(lowered) and not self._is_sms_content_request(
            lowered
        ) and not any(token in lowered for token in _SMS_LOGISTICS_HINT_TOKENS)

    def _sms_eligible(
        self,
        prospect_id: str,
        message_body: str,
        *,
        has_phone: bool,
        scheduling_intent: bool,
    ) -> tuple[bool, str]:
        """Full eligibility check for outbound SMS per the SMS eligibility policy above.

        Returns (eligible: bool, reason: str).
        """
        if not has_phone:
            return False, "no_phone_on_file"
        if not self._booking_link_was_shared_by_email(prospect_id):
            return False, "booking_link_not_yet_shared_by_email"
        if self._has_sms_opt_in_request(message_body):
            return True, "prospect_asked_for_sms"
        if scheduling_intent and has_phone:
            return True, "scheduling_intent_with_phone_on_file"
        if self.can_send_sms(prospect_id) and scheduling_intent:
            return True, "warm_lead_scheduling_focused"
        return False, "sms_gate_not_met"

    def _sms_booking_reply(
        self,
        snapshot: ProspectEnrichmentResponse,
        booking_link: str,
        *,
        sms_result: ToolExecutionResult | None,
        sms_reason: str,
    ) -> tuple[str, str]:
        name = snapshot.prospect.contact_name or "there"

        if sms_reason == "no_phone_on_file":
            return (
                f"Discovery Call — Booking Link for {snapshot.prospect.company_name}",
                (
                    f"Hi {name},\n\n"
                    "Happy to send the discovery-call details by SMS once you share the best mobile number for this thread. "
                    f"In the meantime, you can use the booking link here: {booking_link}\n\n"
                    "If you would rather reply with two windows that work next week, I can coordinate manually.\n\n"
                    "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
                ),
            )

        if sms_reason == "booking_link_not_yet_shared_by_email":
            return (
                f"Discovery Call — Booking Link for {snapshot.prospect.company_name}",
                (
                    f"Hi {name},\n\n"
                    "I need to share the booking link by email first before we switch this scheduling thread to SMS. "
                    f"You can confirm the best slot here: {booking_link}\n\n"
                    "If you still want the follow-up by SMS after this email, reply here once you've reviewed the link and I can continue from there.\n\n"
                    "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
                ),
            )

        if sms_result is None:
            return self._booking_reply(snapshot, booking_link)

        if sms_result.status == "executed":
            opener = "I sent the discovery-call booking link by SMS as requested."
        elif sms_result.status == "previewed":
            opener = "I prepared the discovery-call booking link for SMS delivery and I am including it here as well so you have it immediately."
        else:
            opener = "I could not complete the SMS handoff automatically, so I am including the booking link here by email now."

        return (
            f"Discovery Call — Booking Link for {snapshot.prospect.company_name}",
            (
                f"Hi {name},\n\n"
                f"{opener}\n\n"
                f"You can confirm the best slot here: {booking_link}\n\n"
                "If none of the times fit, reply with two windows that work for you next week and I will coordinate manually.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            ),
        )

    def _is_legal_handoff_request(self, body: str) -> bool:
        return any(token in body for token in _LEGAL_HANDOFF_TOKENS)

    def _is_custom_pricing_handoff_request(self, body: str) -> bool:
        return any(token in body for token in _CUSTOM_PRICING_SCOPE_TOKENS)

    def _is_urgent_concession_request(self, body: str) -> bool:
        return any(token in body for token in _URGENT_CONCESSION_TOKENS)

    def _is_impossible_capacity_pricing_request(self, body: str) -> bool:
        lowered = body.lower()
        if not any(token in lowered for token in ("junior pricing", "junior price", "floor pricing", "discount")):
            return False

        headcount_match = _CAPACITY_HEADCOUNT_PATTERN.search(lowered)
        timeline_match = _TIMELINE_PATTERN.search(lowered)
        if not headcount_match or not timeline_match:
            return bool(_IMPOSSIBLE_CAPACITY_PATTERN.search(lowered))

        headcount = int(headcount_match.group(1))
        timeline_value = int(timeline_match.group(1))
        timeline_unit = timeline_match.group(2)
        short_window = timeline_value <= 45 if timeline_unit.startswith("day") else timeline_value <= 6
        return headcount >= 10 and short_window

    # ------------------------------------------------------------------
    # Reply builders (seed-grounded)
    # ------------------------------------------------------------------

    def _pricing_reply(self, contact_name: str | None) -> tuple[str, str]:
        """Build a pricing objection reply grounded in pricing_sheet.md.

        Quotes the engagement minimum and starter floor from the seed file.
        Routes deeper pricing to a human. Does NOT invent specific total-contract values.
        Per pricing_sheet.md: 'Do not negotiate, do not offer discounts, do not commit
        to specific total contract values.'
        """
        p = seed_materials.pricing
        b = seed_materials.baseline
        name = contact_name or "there"
        concern_phrase = seed_materials.sales_deck_concerns.indian_vendor_burned
        return (
            "Tenacious Intelligence — Engagement Pricing Overview",
            f"Hi {name},\n\n"
            "Thank you for asking — happy to share an overview of how we structure engagements.\n\n"
            f"{p.quotable_talent_floor}\n\n"
            f"For fixed-scope project work: {p.quotable_project_floor}\n\n"
            f"{p.engagement_minimum} {p.extension_cadence}\n\n"
            f"On the cost-comparison question: {concern_phrase}\n\n"
            "A more specific number depends on scope and stack mix — I would not want to "
            "give you a figure without a brief scoping conversation first. I can arrange "
            "15 minutes with one of our delivery leads who can walk you through the options "
            "most relevant to your situation.\n\n"
            "Would that be useful?\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _offshore_concern_reply(self, contact_name: str | None) -> tuple[str, str]:
        """Build an offshore-concern objection reply grounded in transcript_05.

        Uses agent-usable phrases from the objection-heavy discovery transcript.
        Does NOT use banned phrases: 'We're not like other offshore vendors',
        'Guaranteed 40% cost savings', 'We can handle any stack'.
        """
        op = seed_materials.objection_patterns
        b = seed_materials.baseline
        name = contact_name or "there"
        accenture_phrase = seed_materials.sales_deck_concerns.accenture_slog
        return (
            "Tenacious Intelligence — Our Engineering Delivery Model",
            f"Hi {name},\n\n"
            "Thank you for raising this — it is a fair and important question.\n\n"
            f"{op.offshore_concern}\n\n"
            f"{accenture_phrase}\n\n"
            f"In practice: {b.tenure_months}-month average engineer tenure, "
            f"{b.overlap_hours_min}–{b.overlap_hours_max} hours of daily overlap with your time zone built into every engagement, "
            f"and a dedicated project manager on every account. "
            f"Our {b.bench_ready} bench engineers are employees, not contractors — salaried, with benefits and insurance.\n\n"
            f"{op.architecture_boundary}\n\n"
            "A 15-minute conversation with our delivery lead is the quickest way to assess "
            "whether this model fits your team's working style. Would you be open to that?\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _general_followup_reply(self, snapshot: ProspectEnrichmentResponse) -> tuple[str, str]:
        """Build a follow-up reply grounded in discovery transcript patterns.

        Asks a clarifying question rather than asserting a conclusion.
        Optionally references an approved case study if one matches the segment.
        """
        name = snapshot.prospect.contact_name or "there"
        segment = snapshot.prospect.primary_segment
        case_note = ""
        matched_case = seed_materials.find_case_study(segment)
        if matched_case:
            case_note = (
                f"\n\nFor context: {matched_case.quotable} "
                "Happy to share more detail on the discovery call."
            )
        signal_note = self._public_signal_note(snapshot)

        return (
            "Tenacious Intelligence — Thread Update",
            f"Hi {name},\n\n"
            "Thanks for checking in.\n\n"
            f"{signal_note}\n\n"
            "The useful next step is still to confirm which constraint is most pressing for "
            "your team right now: recruiting velocity, a specific AI or data capability gap, "
            "or cost structure.\n\n"
            f"Which of those is closest to where you are today?{case_note}\n\n"
            "If none of those is active, I can close the loop here.\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _public_signal_note(self, snapshot: ProspectEnrichmentResponse) -> str:
        signals = sorted(
            snapshot.hiring_signal_brief.signals,
            key=lambda signal: signal.confidence,
            reverse=True,
        )
        if signals and signals[0].confidence >= 0.5:
            return f"The strongest public signal I have is still this: {signals[0].summary}"
        return (
            "I do not have a stronger public signal than the one in the original note, "
            "so I would keep the conversation scoped as a research check rather than a claim."
        )

    def _differentiation_reply(self, snapshot: ProspectEnrichmentResponse) -> tuple[str, str]:
        """Answer differentiation questions without generic capacity overclaims."""
        name = snapshot.prospect.contact_name or "there"
        b = seed_materials.baseline
        signal_note = self._public_signal_note(snapshot)
        return (
            "Tenacious Intelligence — Difference",
            f"Hi {name},\n\n"
            "The short answer: Tenacious is built for managed delivery, not resume forwarding.\n\n"
            "The practical differences are named engineers, direct access to the people doing "
            "the work, a dedicated project manager for coordination, and a delivery model that "
            f"plans around {b.overlap_hours_min}–{b.overlap_hours_max} hours of daily time-zone overlap. "
            f"Our average engineer tenure is {b.tenure_months} months, so the model is designed "
            "around continuity rather than rotation.\n\n"
            f"{signal_note}\n\n"
            "The right test is whether your current constraint is delivery capacity, a specific "
            "platform or data gap, or something else entirely. Which is closest?\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _extract_capability_focus(self, body: str) -> str | None:
        lowered = body.lower()
        if any(token in lowered for token in _MODELING_FOCUS_TOKENS):
            return "modeling"
        if any(token in lowered for token in _MLOPS_FOCUS_TOKENS):
            return "MLOps"
        if any(token in lowered for token in _DATA_PIPELINE_FOCUS_TOKENS):
            return "data pipeline"
        if any(token in lowered for token in _APPLIED_ML_FOCUS_TOKENS):
            return "applied ML feature delivery"
        return None

    def _capability_gap_reply(
        self,
        snapshot: ProspectEnrichmentResponse,
        *,
        inbound_body: str,
    ) -> tuple[str, str]:
        """Respond directly to explicit AI/ML capability-gap intent."""
        name = snapshot.prospect.contact_name or "there"
        focus = self._extract_capability_focus(inbound_body)
        signal_note = self._public_signal_note(snapshot)
        matched_case = seed_materials.find_case_study(snapshot.prospect.primary_segment)
        case_line = (
            f"\n\nRelevant example: {matched_case.quotable}"
            if matched_case
            else ""
        )
        if focus == "modeling":
            return (
                "Tenacious Intelligence — Modeling Capability Gap",
                f"Hi {name},\n\n"
                "Understood — if the gap is on modeling specifically, the next useful step is to narrow "
                "where it is slowing you down most right now: model selection, training or fine-tuning, "
                "evaluation, or production inference.\n\n"
                "If you share which of those is the blocker, I can route this to a delivery lead and propose "
                "a focused 15-minute scoping call around that modeling workstream.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            )
        if focus == "MLOps":
            return (
                "Tenacious Intelligence — MLOps Capability Gap",
                f"Hi {name},\n\n"
                "Understood — if the gap is on MLOps, the next useful step is to narrow whether the blocker is "
                "deployment, monitoring, experiment tracking, or release workflow.\n\n"
                "If you share which part is creating the most drag, I can route this to a delivery lead and propose "
                "a focused scoping call around that MLOps workstream.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            )
        if focus == "data pipeline":
            return (
                "Tenacious Intelligence — Data Pipeline Gap",
                f"Hi {name},\n\n"
                "Understood — if the gap is in the data pipeline, the next useful step is to narrow whether the blocker is "
                "ingestion, training-data quality, feature pipelines, or upstream reliability.\n\n"
                "If you share which part is the main constraint, I can route this to a delivery lead and propose "
                "a focused scoping call around that pipeline workstream.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            )
        if focus == "applied ML feature delivery":
            return (
                "Tenacious Intelligence — Applied ML Delivery Gap",
                f"Hi {name},\n\n"
                "Understood — if the need is around applied ML feature delivery, the next useful step is to narrow "
                "the use case first: copilots or agents, ranking or recommendation, forecasting, or document intelligence.\n\n"
                "If you share which use case matters most, I can route this to a delivery lead and propose a focused "
                "scoping call around that workstream.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            )
        return (
            "Tenacious Intelligence — AI/ML Capability Gap",
            f"Hi {name},\n\n"
            "Understood — if your main need is an AI/ML capability gap, the most useful next step "
            "is to define the exact scope first (modeling, MLOps, data pipeline, or applied ML feature delivery).\n\n"
            f"{signal_note}{case_line}\n\n"
            "If you share your top priority, I can route this to a delivery lead and propose a "
            "focused 15-minute scoping call with concrete options.\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _bench_mismatch_reply(self, snapshot: ProspectEnrichmentResponse) -> tuple[str, str]:
        """Build a bench-mismatch reply. Does not over-promise capacity.

        Per bench_summary.json honesty constraint: 'If a prospect's stated need
        exceeds the available_engineers count for the required stack, the agent must
        flag the mismatch and route to a human.'
        """
        name = snapshot.prospect.contact_name or "there"
        # Identify which required stacks caused the mismatch, if readable
        required = snapshot.hiring_signal_brief.bench_match.required_stacks
        available = snapshot.hiring_signal_brief.bench_match.available_capacity
        gap_stacks = [s for s in required if available.get(s, 0) == 0]

        if gap_stacks:
            gap_note = (
                f"The public signal suggests a need for {', '.join(gap_stacks)} capacity. "
                "Our delivery lead can confirm whether current bench availability fits "
                "before I make any commitment."
            )
        else:
            gap_note = (
                "The delivery lead will verify current bench availability "
                "before any capacity is committed."
            )

        return (
            "Tenacious Intelligence — Engineering Capacity Review",
            f"Hi {name},\n\n"
            "Thank you for sharing the details of your requirements.\n\n"
            f"{gap_note}\n\n"
            "Rather than make a commitment I cannot stand behind, I would prefer to route "
            "this directly to our delivery lead for a proper capacity review. They will be "
            "best placed to give you an accurate and honest picture of what we can commit to.\n\n"
            "You can expect a follow-up from the delivery lead shortly. In the meantime, "
            "please do not hesitate to reach out if you have any questions.\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _soft_defer_reply(self, contact_name: str | None, body: str) -> tuple[str, str]:
        """Gracious close for 'not right now' replies. Names a specific re-engagement month."""
        import datetime
        name = contact_name or "there"
        # Calculate a re-engagement month ~3 months out
        future = datetime.date.today().replace(day=1)
        month_names = ["January","February","March","April","May","June",
                       "July","August","September","October","November","December"]
        future_month = month_names[(future.month + 2) % 12]
        future_year = future.year + ((future.month + 2) // 12)
        reeng = seed_materials.reengagement
        return (
            "Tenacious Intelligence — Noted, Will Follow Up Later",
            f"Hi {name},\n\n"
            "Understood — timing matters, and I appreciate the honest reply.\n\n"
            f"I'll set a reminder to reach back out in {future_month} {future_year} "
            "with fresh research on where your sector is at that point. "
            "No obligation, no pressure — just a relevant data point when the timing is better.\n\n"
            "Best of luck in the meantime.\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _curious_reply(self, snapshot: ProspectEnrichmentResponse) -> tuple[str, str]:
        """Targeted 3-sentence context + Cal link for 'tell me more' replies."""
        name = snapshot.prospect.contact_name or "there"
        segment = snapshot.prospect.primary_segment
        b = seed_materials.baseline
        pitch = seed_materials.get_pitch_language(segment, snapshot.prospect.ai_maturity_score or 0)
        bottleneck = seed_materials.get_bottleneck_sentence(segment)
        phrases = seed_materials.get_transcript_phrases(segment)
        deploy_phrase = phrases[0] if phrases else f"Engineers are deployed in {b.time_to_deploy_min_days}–{b.time_to_deploy_max_days} days."
        return (
            "Tenacious Intelligence — Quick Context",
            f"Hi {name},\n\n"
            "Glad this landed. Two-line version: Tenacious is a managed engineering delivery firm — "
            f"we run dedicated squads out of Addis Ababa for US and EU scale-ups, with "
            f"{b.overlap_hours_min}–{b.overlap_hours_max} hours of daily time-zone overlap. "
            f"We are most useful when in-house hiring is slower than the work needs.\n\n"
            f"{bottleneck}\n\n"
            f"{deploy_phrase} "
            f"We have {b.bench_ready} engineers ready to deploy and {b.bench_scalable} we can scale to within 3 months. "
            f"Engineers are full-time Tenacious employees — {b.tenure_months}-month average tenure, "
            f"salaried with benefits.\n\n"
            "Would 15 minutes this week work to walk through what this looks like for your specific situation?\n\n"
            "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
        )

    def _booking_reply(
        self,
        snapshot: ProspectEnrichmentResponse,
        booking_link: str,
    ) -> tuple[str, str]:
        b = seed_materials.baseline
        segment = snapshot.prospect.primary_segment
        phrases = seed_materials.get_transcript_phrases(segment)
        # Pick a relevant phrase for this segment (second one if available, else first)
        phase_phrase = phrases[1] if len(phrases) > 1 else (phrases[0] if phrases else "")
        phase_note = f"\n\n{phase_phrase}" if phase_phrase else ""
        return (
            f"Discovery Call — Booking Options for {snapshot.prospect.company_name}",
            (
                f"Hi {snapshot.prospect.contact_name or 'there'},\n\n"
                "Thank you for your interest — I have reserved two discovery-call slots "
                "with our delivery lead and would love to find a time that works for you.\n\n"
                f"You can confirm your preferred slot here: {booking_link}\n\n"
                "The call is 30 minutes and focused entirely on understanding your team's "
                "current priorities — no pitch, no pressure."
                f"{phase_note}\n\n"
                f"We have {b.bench_ready} engineers ready to deploy within "
                f"{b.time_to_deploy_min_days}–{b.time_to_deploy_max_days} days of a signed engagement, "
                f"with {b.overlap_hours_min}–{b.overlap_hours_max} hours of daily time-zone overlap and "
                f"an average engineer tenure of {b.tenure_months} months.\n\n"
                "If none of the available times suit you, simply reply with two windows "
                "that work on your end and I will coordinate accordingly.\n\n"
                "Looking forward to speaking with you.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            ),
        )

    def _rewrite_email_draft(
        self,
        *,
        snapshot: ProspectEnrichmentResponse,
        scenario: str,
        fallback_subject: str,
        fallback_body: str,
        extra_context: dict[str, object],
    ) -> str:
        recommendation_memory = self.repository.recent_recommendation_memory_blended(
            prospect_id=snapshot.prospect.prospect_id,
            limit=6,
            local_limit=6,
            global_limit=6,
            global_min_occurrences=1,
            global_sources=_GLOBAL_CORRECTION_MEMORY_SOURCES,
        )
        correction_history = self.repository.list_correction_history(
            prospect_id=snapshot.prospect.prospect_id,
            limit=6,
        )
        draft = generation_service.draft_email_from_scaffold(
            trace_id=getattr(snapshot, "trace_id", None),
            prospect_id=snapshot.prospect.prospect_id,
            scenario=scenario,
            company_name=snapshot.prospect.company_name,
            contact_name=snapshot.prospect.contact_name,
            fallback_subject=fallback_subject,
            fallback_body=fallback_body,
            context={
                "primary_segment": snapshot.prospect.primary_segment_label,
                "ai_maturity_score": snapshot.prospect.ai_maturity_score,
                "signals": [signal.summary for signal in snapshot.hiring_signal_brief.signals[:4]],
                "safe_gap_framing": snapshot.competitor_gap_brief.safe_gap_framing,
                "do_not_claim": snapshot.hiring_signal_brief.do_not_claim,
                "recommendation_memory": recommendation_memory,
                "correction_history": correction_history,
                **extra_context,
            },
        )
        return draft.as_reply_draft

    # ------------------------------------------------------------------
    # Warm SMS handoff
    # ------------------------------------------------------------------

    def prepare_warm_sms_handoff(
        self,
        snapshot: ProspectEnrichmentResponse,
        *,
        body: str | None = None,
        include_booking_link: bool = False,
        force_allow: bool = False,
        inbound_body: str | None = None,
    ) -> ToolExecutionResult:
        allow_warm_lead = force_allow or self.can_send_sms(snapshot.prospect.prospect_id)
        if include_booking_link:
            sms_result, _ = sms_channel.send_booking_options(
                phone_number=snapshot.prospect.contact_phone,
                prospect_id=snapshot.prospect.prospect_id,
                company_name=snapshot.prospect.company_name,
                contact_name=snapshot.prospect.contact_name,
                contact_email=snapshot.prospect.contact_email,
                allow_warm_lead=allow_warm_lead,
                inbound_body=inbound_body,
                prospect_context=snapshot.prospect.model_dump(mode="json"),
                hiring_signal_brief=snapshot.hiring_signal_brief.model_dump(mode="json"),
                competitor_gap_brief=snapshot.competitor_gap_brief.model_dump(mode="json"),
            )
        else:
            sms_result = sms_channel.send(
                phone_number=snapshot.prospect.contact_phone,
                body=body or "Warm-lead scheduling handoff for Tenacious.",
                prospect_id=snapshot.prospect.prospect_id,
                allow_warm_lead=allow_warm_lead,
                inbound_body=inbound_body,
                prospect_context=snapshot.prospect.model_dump(mode="json"),
                hiring_signal_brief=snapshot.hiring_signal_brief.model_dump(mode="json"),
                competitor_gap_brief=snapshot.competitor_gap_brief.model_dump(mode="json"),
            )
        if sms_result.status in {"executed", "previewed"}:
            self.repository.record_interaction_event(
                snapshot.prospect.prospect_id,
                "sms_handoff_sent",
                channel="sms",
                provider="africastalking" if sms_channel.status().configured else "mock",
                payload={"message": sms_result.message},
            )
        return sms_result

    def prepare_voice_handoff(
        self,
        snapshot: ProspectEnrichmentResponse,
        *,
        reason: str,
        booking_link: str | None = None,
        booking_status: str | None = None,
        force_allow: bool = False,
    ) -> ToolExecutionResult:
        allow_warm_lead = force_allow or self.can_send_sms(snapshot.prospect.prospect_id)
        events = self.repository.list_interaction_events(snapshot.prospect.prospect_id)
        context_brief = context_brief_generator.build(
            snapshot,
            events=events,
            reason=reason,
            booking_link=booking_link,
            booking_status=booking_status,
        )
        voice_result = voice_channel.prepare_handoff(
            phone_number=snapshot.prospect.contact_phone,
            prospect_id=snapshot.prospect.prospect_id,
            company_name=snapshot.prospect.company_name,
            contact_name=snapshot.prospect.contact_name,
            contact_email=snapshot.prospect.contact_email,
            allow_warm_lead=allow_warm_lead,
            booking_link=booking_link,
            context_brief=context_brief.markdown,
            context_brief_artifact_ref=context_brief.artifact_ref,
            reason=reason,
        )
        if voice_result.status in {"executed", "previewed"}:
            self.repository.record_interaction_event(
                snapshot.prospect.prospect_id,
                "voice_handoff_sent",
                channel="voice",
                provider="shared_voice_rig" if voice_channel.status().configured else "mock",
                payload={"message": voice_result.message, "reason": reason},
            )
        return voice_result

    # ------------------------------------------------------------------
    # Main routing
    # ------------------------------------------------------------------

    def route_inbound_message(
        self,
        snapshot: ProspectEnrichmentResponse,
        message: InboundMessageRequest,
    ) -> tuple[ConversationDecision, list[ToolExecutionResult]]:
        body = message.body.lower()
        risk_flags: list[str] = []
        side_effects: list[ToolExecutionResult] = []
        next_action = "send_email"
        channel = "email"
        reply = ""

        # ---- Opt-out ------------------------------------------------
        if any(token in body for token in ("stop", "unsubscribe", "unsub")):
            next_action = "handoff_human"
            channel = "human"
            risk_flags.append("opt_out")
            name = snapshot.prospect.contact_name or "there"
            reply = (
                f"Subject: You have been unsubscribed\n\n"
                f"Hi {name},\n\n"
                "We have received your request and you will no longer receive outreach "
                "from Tenacious Intelligence Corporation regarding this thread.\n\n"
                "If you change your mind or would like to reconnect in the future, "
                "you are always welcome to reach out to us at gettenacious.com.\n\n"
                "We appreciate the time you gave us and wish you and your team the very best.\n\n"
                "Best regards,\n"
                "The Tenacious Team\n"
                "Tenacious Intelligence Corporation\n"
                "gettenacious.com"
            )

        # ---- Hard no (route to suppression/human) -------------------
        elif any(token in body for token in _HARD_NO_TOKENS):
            next_action = "handoff_human"
            channel = "human"
            risk_flags.append("hard_no_route_human")
            name = snapshot.prospect.contact_name or "there"
            reply = (
                f"Subject: Preference noted\n\n"
                f"Hi {name},\n\n"
                "Thanks for the clear note. I will route this to our team to ensure "
                "your preference is handled correctly before any further outreach.\n\n"
                "Best regards,\n"
                "The Tenacious Team\n"
                "Tenacious Intelligence Corporation\n"
                "gettenacious.com"
            )

        # ---- Legal / contract / reference / compliance --------------
        elif self._is_legal_handoff_request(body):
            next_action = "handoff_human"
            channel = "human"
            risk_flags.append("legal_handoff_required")
            name = snapshot.prospect.contact_name or "there"
            reply = (
                f"Subject: Re: Policy and Terms Request\n\n"
                f"Hi {name},\n\n"
                "Thank you for the question. I should route this to a Tenacious delivery lead "
                "so we do not provide incomplete legal, compliance, or reference details by email.\n\n"
                "I will pass your request along with context and keep the thread on email.\n\n"
                "Best regards,\n"
                "The Tenacious Team\n"
                "Tenacious Intelligence Corporation\n"
                "gettenacious.com"
            )

        # ---- Custom scope pricing / urgent concessions --------------
        elif self._is_custom_pricing_handoff_request(body) or self._is_urgent_concession_request(body):
            next_action = "handoff_human"
            channel = "human"
            risk_flags.append("custom_pricing_handoff_required")
            name = snapshot.prospect.contact_name or "there"
            reply = (
                f"Subject: Re: Custom Pricing Request\n\n"
                f"Hi {name},\n\n"
                "Thanks for the pricing question. I can share public ranges, but custom multi-phase "
                "or concession terms need a delivery lead review before we quote specifics.\n\n"
                "I will route this for human follow-up with the right scope context.\n\n"
                "Best regards,\n"
                "The Tenacious Team\n"
                "Tenacious Intelligence Corporation\n"
                "gettenacious.com"
            )

        # ---- Impossible capacity + junior pricing demands -----------
        elif self._is_impossible_capacity_pricing_request(body):
            next_action = "handoff_human"
            channel = "human"
            risk_flags.append("impossible_capacity_pricing_claim_blocked")
            name = snapshot.prospect.contact_name or "there"
            reply = (
                f"Subject: Re: Capacity and Pricing Request\n\n"
                f"Hi {name},\n\n"
                "I cannot confirm that combination of timeline, seniority, and pricing in email. "
                "This requires a delivery lead capacity and scope review before any commitment.\n\n"
                "I will route this to human review immediately.\n\n"
                "Best regards,\n"
                "The Tenacious Team\n"
                "Tenacious Intelligence Corporation\n"
                "gettenacious.com"
            )

        # ---- Curious / "tell me more" ----------------------------------------
        elif any(token in body for token in _DIFFERENTIATION_TOKENS):
            subject, fallback_body = self._differentiation_reply(snapshot)
            reply = self._rewrite_email_draft(
                snapshot=snapshot,
                scenario="differentiation_reply",
                fallback_subject=subject,
                fallback_body=fallback_body,
                extra_context={"inbound_message": message.body, "reply_class": "differentiation"},
            )

        # ---- Explicit capability-gap intent -------------------------
        elif any(token in body for token in _CAPABILITY_TOKENS) or self._extract_capability_focus(body):
            risk_flags.append("capability_gap_intent")
            capability_focus = self._extract_capability_focus(body) or "unspecified"
            subject, fallback_body = self._capability_gap_reply(
                snapshot,
                inbound_body=message.body,
            )
            reply = self._rewrite_email_draft(
                snapshot=snapshot,
                scenario="capability_gap_reply",
                fallback_subject=subject,
                fallback_body=fallback_body,
                extra_context={
                    "inbound_message": message.body,
                    "reply_class": "capability_gap",
                    "capability_focus": capability_focus,
                    "progression_rule": "If the prospect already named the capability area, move one step deeper instead of reopening the broad scope split.",
                },
            )
            if capability_focus != "unspecified" and "define the exact scope first" in reply.lower():
                reply = f"Subject: {subject}\n\n{fallback_body}"

        # ---- Curious / "tell me more" ----------------------------------------
        elif any(token in body for token in _CURIOUS_TOKENS):
            subject, fallback_body = self._curious_reply(snapshot)
            reply = self._rewrite_email_draft(
                snapshot=snapshot,
                scenario="curious_reply",
                fallback_subject=subject,
                fallback_body=fallback_body,
                extra_context={"inbound_message": message.body, "reply_class": "curious"},
            )

        # ---- Soft defer ("not right now") ------------------------------------
        elif any(token in body for token in _SOFT_DEFER_TOKENS):
            next_action = "handoff_human"
            channel = "human"
            risk_flags.append("soft_defer")
            subject, fallback_body = self._soft_defer_reply(snapshot.prospect.contact_name, body)
            reply = f"Subject: {subject}\n\n{fallback_body}"

        # ---- Pricing objection (seed-grounded, no invented numbers) --
        elif any(token in body for token in _PRICING_TOKENS):
            risk_flags.append("pricing_guardrail")
            subject, fallback_body = self._pricing_reply(snapshot.prospect.contact_name)
            reply = self._rewrite_email_draft(
                snapshot=snapshot,
                scenario="pricing_reply",
                fallback_subject=subject,
                fallback_body=fallback_body,
                extra_context={
                    "inbound_message": message.body,
                    "pricing_guardrail": True,
                },
            )
            if "specific number depends on scope" not in reply.lower():
                reply = f"Subject: {subject}\n\n{fallback_body}"

        # ---- Offshore concern (transcript-grounded) -------------------
        elif any(token in body for token in _OFFSHORE_CONCERN_TOKENS):
            risk_flags.append("offshore_concern")
            subject, fallback_body = self._offshore_concern_reply(snapshot.prospect.contact_name)
            reply = self._rewrite_email_draft(
                snapshot=snapshot,
                scenario="offshore_reply",
                fallback_subject=subject,
                fallback_body=fallback_body,
                extra_context={
                    "inbound_message": message.body,
                    "objection_pattern": "offshore_concern",
                },
            )

        # ---- SMS is logistics-only; substantive content stays on email ----
        elif self._is_sms_content_request(body):
            risk_flags.append("sms_logistics_only")
            name = snapshot.prospect.contact_name or "there"
            reply = (
                f"Subject: Re: Tenacious follow-up\n\n"
                f"Hi {name},\n\n"
                "I can use SMS for booking logistics and scheduling follow-up, but I should keep offer, scope, and commercial details on email so the thread stays accurate and reviewable.\n\n"
                "If you want, reply here with the main question about the offer or scope and I will answer it directly on email.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            )

        elif self._is_generic_sms_request(body):
            risk_flags.append("sms_request_needs_specific_logistics")
            name = snapshot.prospect.contact_name or "there"
            reply = (
                f"Subject: Re: Tenacious scheduling follow-up\n\n"
                f"Hi {name},\n\n"
                "I already shared the booking link on email, so I do not need to resend the same link by SMS unless you want that specifically for scheduling logistics.\n\n"
                "If you want the booking link by SMS, say that directly. Otherwise, keep the scheduling thread on email and I will coordinate from there.\n\n"
                "Best regards,\nThe Tenacious Team\nTenacious Intelligence Corporation\ngettenacious.com"
            )

        # ---- Scheduling intent (book_meeting) ------------------------
        elif any(token in body for token in _SCHEDULING_TOKENS) or self._is_sms_booking_followup_request(
            snapshot.prospect.prospect_id,
            body,
        ):
            next_action = "book_meeting"
            channel = "calendar"
            requested_sms = self._has_sms_opt_in_request(body)
            scheduling_requested = any(token in body for token in _SCHEDULING_TOKENS) or self._is_sms_booking_followup_request(
                snapshot.prospect.prospect_id,
                body,
            )
            sms_result: ToolExecutionResult | None = None

            # SMS is only sent when eligibility criteria are met (see policy at top of file).
            sms_eligible, sms_reason = self._sms_eligible(
                snapshot.prospect.prospect_id,
                body,
                has_phone=bool(snapshot.prospect.contact_phone),
                scheduling_intent=scheduling_requested,
            )

            if requested_sms and sms_eligible:
                sms_result = self.prepare_warm_sms_handoff(
                    snapshot,
                    include_booking_link=True,
                    force_allow=True,
                    inbound_body=message.body,
                )
                side_effects.append(sms_result)
                if sms_result.status == "skipped":
                    sms_msg = str(sms_result.message or "").lower()
                    if "warm-lead gate" in sms_msg:
                        risk_flags.append("sms_warm_lead_gate_blocked")
                    elif "week 11" in sms_msg or "week 2" in sms_msg or "governance" in sms_msg or "human review" in sms_msg:
                        risk_flags.append("sms_blocked_by_policy")
                    else:
                        risk_flags.append("sms_handoff_skipped")
                elif sms_result.status == "error":
                    risk_flags.append("sms_handoff_failed")

            if requested_sms:
                booking_link, _ = calcom_client.generate_booking_link(
                    company_name=snapshot.prospect.company_name,
                    contact_email=snapshot.prospect.contact_email,
                    prospect_id=snapshot.prospect.prospect_id,
                    source_channel="email",
                )
                draft_subject, draft_body = self._sms_booking_reply(
                    snapshot,
                    booking_link,
                    sms_result=sms_result,
                    sms_reason=sms_reason,
                )
                reply = f"Subject: {draft_subject}\n\n{draft_body}"
            else:
                booking_link, _ = calcom_client.generate_booking_link(
                    company_name=snapshot.prospect.company_name,
                    contact_email=snapshot.prospect.contact_email,
                    prospect_id=snapshot.prospect.prospect_id,
                    source_channel="email",
                )
                subject, fallback_body = self._booking_reply(snapshot, booking_link)
                reply = self._rewrite_email_draft(
                    snapshot=snapshot,
                    scenario="booking_options",
                    fallback_subject=subject,
                    fallback_body=fallback_body,
                    extra_context={
                        "inbound_message": message.body,
                        "booking_link": booking_link,
                        "requested_voice": any(token in body for token in _VOICE_OPT_IN_TOKENS),
                    },
                )
                draft_subject = reply.splitlines()[0].split(":", 1)[1].strip() if reply.lower().startswith("subject:") else subject
                draft_body = "\n".join(reply.splitlines()[1:]).strip() if reply.lower().startswith("subject:") else fallback_body

            email_result = email_channel.send(
                recipient=snapshot.prospect.contact_email,
                subject=draft_subject,
                body=draft_body,
                prospect_id=snapshot.prospect.prospect_id,
                prospect_context=snapshot.prospect.model_dump(mode="json"),
                hiring_signal_brief=snapshot.hiring_signal_brief.model_dump(mode="json"),
                competitor_gap_brief=snapshot.competitor_gap_brief.model_dump(mode="json"),
                inbound_body=message.body,
            )
            side_effects.append(email_result)
            if email_result.status == "error":
                risk_flags.append("email_booking_send_failed")
            elif email_result.status == "executed":
                self.repository.record_interaction_event(
                    snapshot.prospect.prospect_id,
                    "booking_link_shared",
                    channel="email",
                    provider=email_channel.status().name,
                    payload={"subject": draft_subject},
                )

            if not sms_eligible:
                risk_flags.append(f"sms_skipped:{sms_reason}")

            if any(token in body for token in _VOICE_OPT_IN_TOKENS):
                voice_result = self.prepare_voice_handoff(
                    snapshot,
                    reason="prospect_requested_voice",
                )
                side_effects.append(voice_result)
                if voice_result.status == "skipped":
                    risk_flags.append("voice_warm_lead_gate_blocked")
                elif voice_result.status == "error":
                    risk_flags.append("voice_handoff_failed")

        # ---- Bench mismatch → human review (bench_summary.json gate) -
        elif not snapshot.hiring_signal_brief.bench_match.sufficient:
            next_action = "handoff_human"
            channel = "human"
            risk_flags.append("bench_mismatch_route_human")
            subject, fallback_body = self._bench_mismatch_reply(snapshot)
            reply = self._rewrite_email_draft(
                snapshot=snapshot,
                scenario="bench_mismatch_reply",
                fallback_subject=subject,
                fallback_body=fallback_body,
                extra_context={
                    "inbound_message": message.body,
                    "bench_match": snapshot.hiring_signal_brief.bench_match.model_dump(mode="json"),
                },
            )

        # ---- Update/check-in or general follow-up --------------------
        else:
            subject, fallback_body = self._general_followup_reply(snapshot)
            reply = self._rewrite_email_draft(
                snapshot=snapshot,
                scenario="update_reply" if any(token in body for token in _UPDATE_TOKENS) else "general_followup",
                fallback_subject=subject,
                fallback_body=fallback_body,
                extra_context={
                    "inbound_message": message.body,
                    "current_state": self.current_state(snapshot.prospect.prospect_id),
                    "reply_class": "update" if any(token in body for token in _UPDATE_TOKENS) else "general",
                },
            )

        decision = ConversationDecision(
            next_action=next_action,
            channel=channel,
            reply_draft=reply,
            needs_human=channel == "human",
            risk_flags=risk_flags,
            trace_tags=["inbound_reply", "channel_handoff_state_machine", "seed_grounded"],
        )
        return decision, side_effects
