import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from agent.channels.email import email_channel
from agent.channels.sms import sms_channel
from agent.channels.voice import voice_channel
from agent.config import settings
from agent.crm.hubspot import hubspot_client
from agent.enrichment.service import enrichment_service
from agent.enrichment.connectors import (
    crunchbase_connector,
    job_posts_connector,
    layoffs_connector,
    leadership_connector,
)
from agent.evaluation.tenacious_judge_adapter import review_before_action
from agent.evaluation.tau2 import tau2_adapter
from agent.generation.service import generation_service
from agent.observability.langfuse import langfuse_client
from agent.observability.tracing import TraceLogger
from agent.orchestration.handoff import ChannelHandoffManager
from agent.policies.service import policy_service
from agent.schemas.briefs import ProspectEnrichmentResponse
from agent.schemas.conversation import ConversationDecision
from agent.schemas.dashboard import (
    DashboardArtifact,
    DashboardFlowSummary,
    DashboardInteractionEvent,
    DashboardStateResponse,
    RecentTrace,
)
from agent.schemas.prospect import InboundMessageRequest, LeadIntakeRequest, ProspectRecord
from agent.schemas.tools import ToolExecutionResult, ToolStatus, ToolchainReport
from agent.scheduling.calcom import calcom_client
from agent.storage.repository import ProspectRepository

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


def _with_retries(
    fn: Callable[[], _T],
    *,
    max_attempts: int = 3,
    delay_secs: float = 0.5,
) -> _T:
    """Bounded exponential-backoff retry for safe idempotent tool calls.

    Use only for idempotent operations (HubSpot contact upsert, Langfuse mirror).
    Never use for email or SMS sends — those are not idempotent without verified
    idempotency keys and a retry would result in duplicate outbound messages.

    A result is considered failed when it is a ToolExecutionResult with status="error",
    or a list where any element has status="error".
    """
    last: _T | None = None
    for attempt in range(max_attempts):
        last = fn()
        failed = (
            any(r.status == "error" for r in last)  # type: ignore[union-attr]
            if isinstance(last, list)
            else (isinstance(last, ToolExecutionResult) and last.status == "error")
        )
        if not failed or attempt == max_attempts - 1:
            return last  # type: ignore[return-value]
        time.sleep(delay_secs * (2**attempt))
    return last  # type: ignore[return-value]


class Orchestrator:
    def __init__(self) -> None:
        self.repository = ProspectRepository()
        self.trace_logger = TraceLogger()
        self.handoff_manager = ChannelHandoffManager(self.repository)

    # ------------------------------------------------------------------
    # Tool failure handling
    # ------------------------------------------------------------------

    def _handle_tool_result(
        self,
        result: ToolExecutionResult | list[ToolExecutionResult],
        prospect_id: str,
        context: str,
        *,
        critical: bool = False,
    ) -> bool:
        """Inspect result(s), log failures to trace JSONL and SQLite.

        Returns True when all results are healthy (executed/previewed/skipped).
        Returns False when any result has status="error".

        critical=True signals that a failure should route to human review upstream.
        """
        results = result if isinstance(result, list) else [result]
        all_ok = True
        for r in results:
            if r.status == "error":
                all_ok = False
                logger.error(
                    "Tool failure: tool=%s context=%s prospect=%s message=%s critical=%s",
                    r.name,
                    context,
                    prospect_id,
                    r.message,
                    critical,
                )
                self.trace_logger.log(
                    "tool_failure",
                    {
                        "prospect_id": prospect_id,
                        "tool": r.name,
                        "context": context,
                        "message": r.message,
                        "artifact_ref": r.artifact_ref,
                        "critical": critical,
                    },
                )
                self.repository.record_interaction_event(
                    prospect_id,
                    "tool_failure",
                    channel=r.name,
                    provider=r.name,
                    payload={
                        "context": context,
                        "message": r.message,
                        "critical": critical,
                    },
                )
        return all_ok

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------

    def intake_and_enrich(self, intake: LeadIntakeRequest) -> ProspectEnrichmentResponse:
        prospect, hiring_signal_brief, competitor_gap_brief = enrichment_service.enrich(intake)
        trace_id = self.trace_logger.new_trace_id()
        decision = policy_service.draft_initial_decision(
            prospect=prospect,
            hiring_signal_brief=hiring_signal_brief,
            competitor_gap_brief=competitor_gap_brief,
            trace_id=trace_id,
        )

        self.trace_logger.log(
            "prospect_enriched",
            {
                "prospect_id": prospect.prospect_id,
                "company_name": prospect.company_name,
                "primary_segment": prospect.primary_segment,
                "ai_maturity_score": prospect.ai_maturity_score,
                "risk_flags": decision.risk_flags,
            },
            trace_id=trace_id,
        )

        return self.repository.save_snapshot(
            prospect=prospect,
            hiring_signal_brief=hiring_signal_brief,
            competitor_gap_brief=competitor_gap_brief,
            initial_decision=decision,
            trace_id=trace_id,
        )

    def run_toolchain(self, intake: LeadIntakeRequest) -> ProspectEnrichmentResponse:
        snapshot = self.intake_and_enrich(intake)
        decision = snapshot.initial_decision
        subject, body = self._extract_email_payload(decision.reply_draft if decision else "")
        company_record = crunchbase_connector.lookup(intake.company_name, intake.company_domain)
        jobs_record = job_posts_connector.lookup(intake.company_name, intake.company_domain)
        layoffs_record = layoffs_connector.lookup(intake.company_name, intake.company_domain)
        leadership_record = leadership_connector.lookup(intake.company_name, intake.company_domain)

        email_result = email_channel.send(
            recipient=snapshot.prospect.contact_email,
            subject=subject,
            body=body,
            prospect_id=snapshot.prospect.prospect_id,
            prospect_context=snapshot.prospect.model_dump(mode="json"),
            hiring_signal_brief=snapshot.hiring_signal_brief.model_dump(mode="json"),
            competitor_gap_brief=snapshot.competitor_gap_brief.model_dump(mode="json"),
        )
        self._handle_tool_result(email_result, snapshot.prospect.prospect_id, "initial_email_send", critical=True)
        self.repository.record_interaction_event(
            snapshot.prospect.prospect_id,
            "email_sent",
            channel="email",
            provider=settings.email_provider,
            payload={"subject": subject, "result": email_result.message},
        )

        # SMS is gated by can_send_sms() which requires email_reply_received.
        # On initial outreach this always returns "skipped" — that is correct behaviour.
        sms_result = self.handoff_manager.prepare_warm_sms_handoff(
            snapshot,
            body="Warm-lead scheduling preview for Tenacious discovery-call coordination.",
        )
        self._handle_tool_result(sms_result, snapshot.prospect.prospect_id, "initial_sms_preview")

        calcom_result = calcom_client.book_preview(
            company_name=snapshot.prospect.company_name,
            contact_email=snapshot.prospect.contact_email,
            prospect_id=snapshot.prospect.prospect_id,
        )
        self._handle_tool_result(calcom_result, snapshot.prospect.prospect_id, "scheduling_preview")

        # Langfuse mirror — idempotent, safe to retry.
        langfuse_result = _with_retries(
            lambda: langfuse_client.mirror_trace(
                trace_id=snapshot.trace_id or "pending",
                payload={
                    "company_name": snapshot.prospect.company_name,
                    "segment": snapshot.prospect.primary_segment,
                    "status": snapshot.prospect.status,
                },
                prospect_id=snapshot.prospect.prospect_id,
            ),
            max_attempts=3,
        )
        self._handle_tool_result(langfuse_result, snapshot.prospect.prospect_id, "langfuse_mirror")

        # HubSpot contact upsert + enrichment write — idempotent, safe to retry.
        # Note: record_conversation_event also creates an activity note, which is not
        # idempotent; a retry may produce a duplicate note in HubSpot but that is
        # preferable to silently dropping the CRM sync on a transient error.
        def _signal_summary(name: str) -> str | None:
            for s in snapshot.hiring_signal_brief.signals:
                if s.name == name:
                    return s.summary
            return None

        hubspot_results = _with_retries(
            lambda: hubspot_client.record_conversation_event(
                {
                    "company_name": snapshot.prospect.company_name,
                    "company_domain": snapshot.prospect.company_domain,
                    "email": snapshot.prospect.contact_email,
                    "contact_name": snapshot.prospect.contact_name,
                    "phone": snapshot.prospect.contact_phone,
                    "segment": snapshot.prospect.primary_segment_label,
                    "segment_confidence": snapshot.prospect.segment_confidence,
                    "ai_maturity_score": snapshot.prospect.ai_maturity_score,
                    "bench_match": snapshot.hiring_signal_brief.bench_match.model_dump(mode="json"),
                    "trace_id": snapshot.trace_id,
                    "funding_signal": _signal_summary("funding_event"),
                    "job_post_velocity": _signal_summary("job_post_velocity"),
                    "layoff_signal": _signal_summary("layoff_signal"),
                    "leadership_change": _signal_summary("leadership_change"),
                    "company_size": company_record.get("employee_count") if company_record else None,
                    "industry": company_record.get("sector") if company_record else None,
                    "enrichment_timestamp": snapshot.hiring_signal_brief.generated_at,
                },
                snapshot.prospect.prospect_id,
                activity_type="initial_outreach_prepared",
                activity_summary=f"Initial outreach prepared for {snapshot.prospect.company_name} — segment: {snapshot.prospect.primary_segment_label}, AI maturity: {snapshot.prospect.ai_maturity_score}/3.",
                metadata={
                    "channel_state": self.handoff_manager.current_state(snapshot.prospect.prospect_id),
                    "signals": [s.model_dump(mode="json") for s in snapshot.hiring_signal_brief.signals],
                    "funding_signal": _signal_summary("funding_event"),
                    "job_post_velocity": _signal_summary("job_post_velocity"),
                    "layoff_signal": _signal_summary("layoff_signal"),
                    "leadership_change": _signal_summary("leadership_change"),
                    "company_size": company_record.get("employee_count") if company_record else None,
                    "industry": company_record.get("sector") if company_record else None,
                    "enrichment_timestamp": snapshot.hiring_signal_brief.generated_at,
                    "ai_maturity_score": snapshot.prospect.ai_maturity_score,
                    "segment": snapshot.prospect.primary_segment_label,
                    "segment_confidence": snapshot.prospect.segment_confidence,
                    "bench_match": snapshot.hiring_signal_brief.bench_match.model_dump(mode="json"),
                },
            ),
            max_attempts=2,  # bounded to 2 to limit duplicate activity notes
        )
        self._handle_tool_result(hubspot_results, snapshot.prospect.prospect_id, "hubspot_crm_sync")

        results = [
            crunchbase_connector.run(snapshot.prospect.prospect_id, matched=company_record is not None),
            job_posts_connector.run(snapshot.prospect.prospect_id, matched=jobs_record is not None),
            layoffs_connector.run(snapshot.prospect.prospect_id, matched=layoffs_record is not None),
            leadership_connector.run(snapshot.prospect.prospect_id, matched=leadership_record is not None),
            email_result,
            sms_result,
            calcom_result,
            langfuse_result,
            tau2_adapter.readiness_check(),
        ]
        results.extend(hubspot_results)
        toolchain_report = ToolchainReport(
            statuses=self.tool_statuses(),
            results=results,
        )

        self._write_context_brief(snapshot, company_record, jobs_record, layoffs_record, leadership_record)

        trace_id = snapshot.trace_id or self.trace_logger.new_trace_id()
        self.trace_logger.log(
            "toolchain_run",
            {
                "prospect_id": snapshot.prospect.prospect_id,
                "company_name": snapshot.prospect.company_name,
                "results": [result.model_dump(mode="json") for result in results],
            },
            trace_id=trace_id,
        )

        return self.repository.save_snapshot(
            prospect=snapshot.prospect,
            hiring_signal_brief=snapshot.hiring_signal_brief,
            competitor_gap_brief=snapshot.competitor_gap_brief,
            initial_decision=snapshot.initial_decision,
            trace_id=trace_id,
            toolchain_report=toolchain_report,
        )

    def _write_context_brief(
        self,
        snapshot: ProspectEnrichmentResponse,
        company_record: dict | None,
        jobs_record: dict | None,
        layoffs_record: dict | None,
        leadership_record: dict | None,
    ) -> None:
        """Write a human-readable discovery-call brief to the outbox as {prospect_id}_context_brief.md."""
        p = snapshot.prospect
        hsb = snapshot.hiring_signal_brief
        cgb = snapshot.competitor_gap_brief

        def _sig(name: str) -> str:
            for s in hsb.signals:
                if s.name == name:
                    return f"{s.summary} (confidence {s.confidence:.0%})"
            return "No signal found."

        bench = hsb.bench_match
        bench_line = (
            f"Sufficient — {bench.available_capacity} available for {bench.required_stacks}"
            if bench.sufficient
            else f"Mismatch — required {bench.required_stacks}, available {bench.available_capacity}. Route to human."
        )

        company_size = company_record.get("employee_count", "unknown") if company_record else "unknown"
        industry = company_record.get("sector", "unknown") if company_record else "unknown"
        funding = company_record.get("funding_musd") if company_record else None
        funding_line = f"${funding}M" if funding else "Not found in snapshot."

        pitch = snapshot.initial_decision.reply_draft if snapshot.initial_decision else ""

        md = f"""# Discovery Call Context Brief

**Prospect:** {p.company_name}
**Contact:** {p.contact_name or "Unknown"} &lt;{p.contact_email or "unknown"}&gt;
**Phone:** {p.contact_phone or "Not provided"}
**Generated:** {hsb.generated_at}
**Prospect ID:** {p.prospect_id}

---

## ICP Segment

**Segment:** {hsb.primary_segment}
**Confidence:** {hsb.segment_confidence:.0%}
**AI Maturity Score:** {hsb.ai_maturity_score}/3
**Recommended Pitch:** {hsb.recommended_pitch_angle}

---

## Company Profile

| Field | Value |
|---|---|
| Company | {p.company_name} |
| Domain | {p.company_domain or "unknown"} |
| Industry / Sector | {industry} |
| Size | {company_size} employees |
| Funding | {funding_line} |

---

## Enrichment Signals

| Signal | Finding |
|---|---|
| Funding Event | {_sig("funding_event")} |
| Job Post Velocity | {_sig("job_post_velocity")} |
| Layoff Signal | {_sig("layoff_signal")} |
| Leadership Change | {_sig("leadership_change")} |

---

## Bench Match

{bench_line}

---

## Competitor Gap

**Sector position:** {cgb.safe_gap_framing}
**Confidence:** {cgb.confidence:.0%}
{"**Peer companies:** " + ", ".join(cgb.peer_companies[:3]) if cgb.peer_companies else "Sparse sector — no direct peers found."}

---

## Suggested Outreach Draft

```
{pitch[:800]}
```

---

*This brief was generated automatically by the Tenacious Conversion Engine. Do not share externally.*
"""
        brief_path = settings.outbox_dir / f"{p.prospect_id}_context_brief.md"
        settings.outbox_dir.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(md, encoding="utf-8")

    def handle_inbound_message(self, message: InboundMessageRequest) -> ConversationDecision:
        snapshot = None
        if message.prospect_id:
            snapshot = self.repository.get_snapshot(message.prospect_id)
        if snapshot is None:
            snapshot = self.repository.find_snapshot_by_contact(
                contact_email=message.contact_email,
                contact_phone=message.contact_phone,
            )
        if snapshot is None:
            decision = ConversationDecision(
                next_action="handoff_human",
                channel="human",
                reply_draft=(
                    "I could not match this reply to a saved prospect thread. "
                    "Route to a human before sending a response."
                ),
                needs_human=True,
                risk_flags=["unknown_thread"],
                trace_tags=["inbound_reply", "handoff"],
            )
            self.trace_logger.log("inbound_reply_unmatched", message.model_dump(mode="json"))
            return decision

        body = message.body.lower()
        event_type = {
            "email": "email_reply_received",
            "sms": "sms_reply_received",
            "voice": "voice_reply_received",
        }.get(message.channel, "inbound_reply_received")
        self.repository.record_interaction_event(
            snapshot.prospect.prospect_id,
            event_type,
            channel=message.channel,
            provider=message.channel,
            payload={"body": body},
        )

        raw_decision, side_effects = self.handoff_manager.route_inbound_message(snapshot, message)

        # ------------------------------------------------------------------
        # Reply-send gap fix: when the handoff manager returns next_action="send_email",
        # the reply_draft must be sent — not just returned to the caller as a string.
        # If the send fails we flag it but still return the decision so the caller
        # can route to human review via the risk_flags list.
        # ------------------------------------------------------------------
        additional_risk_flags: list[str] = []
        if raw_decision.next_action in {"send_email", "handoff_human"} and raw_decision.reply_draft:
            subject, reply_body = self._extract_email_payload(raw_decision.reply_draft)
            reply_subject = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
            reply_email_result = email_channel.send(
                recipient=snapshot.prospect.contact_email,
                subject=reply_subject,
                body=reply_body,
                prospect_id=snapshot.prospect.prospect_id,
                prospect_context=snapshot.prospect.model_dump(mode="json"),
                hiring_signal_brief=snapshot.hiring_signal_brief.model_dump(mode="json"),
                competitor_gap_brief=snapshot.competitor_gap_brief.model_dump(mode="json"),
            )
            ok = self._handle_tool_result(
                reply_email_result,
                snapshot.prospect.prospect_id,
                "inbound_reply_email_send",
                critical=True,
            )
            if not ok:
                additional_risk_flags.append("reply_email_send_failed")
            else:
                self.repository.record_interaction_event(
                    snapshot.prospect.prospect_id,
                    "reply_email_sent",
                    channel="email",
                    provider=settings.email_provider,
                    payload={"subject": reply_subject, "result": reply_email_result.message},
                )

        decision = ConversationDecision(
            next_action=raw_decision.next_action,
            channel=raw_decision.channel,
            reply_draft=raw_decision.reply_draft,
            needs_human=raw_decision.needs_human or bool(additional_risk_flags),
            risk_flags=raw_decision.risk_flags + additional_risk_flags,
            trace_tags=["inbound_reply", "policy_guarded", "central_handoff_manager"],
        )

        reply_decision_path = settings.outbox_dir / f"{snapshot.prospect.prospect_id}_reply_decision.json"
        settings.outbox_dir.mkdir(parents=True, exist_ok=True)
        reply_decision_path.write_text(
            json.dumps(
                {
                    "prospect_id": snapshot.prospect.prospect_id,
                    "channel": message.channel,
                    "inbound_body_preview": message.body[:200],
                    "decision": decision.model_dump(mode="json"),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        self.trace_logger.log(
            "inbound_reply_handled",
            {
                "prospect_id": snapshot.prospect.prospect_id,
                "company_name": snapshot.prospect.company_name,
                "channel": message.channel,
                "next_action": decision.next_action,
                "risk_flags": decision.risk_flags,
            },
            trace_id=snapshot.trace_id,
        )
        if decision.next_action == "book_meeting":
            self.repository.record_interaction_event(
                snapshot.prospect.prospect_id,
                "booking_link_shared",
                channel="calendar",
                provider="calcom",
                payload={"source_channel": message.channel},
            )

        # HubSpot sync — single attempt on reply path; initial enrichment already persisted.
        hubspot_results = _with_retries(
            lambda: hubspot_client.record_conversation_event(
                {
                    "company_name": snapshot.prospect.company_name,
                    "company_domain": snapshot.prospect.company_domain,
                    "email": snapshot.prospect.contact_email,
                    "contact_name": snapshot.prospect.contact_name,
                    "phone": snapshot.prospect.contact_phone,
                    "segment": snapshot.prospect.primary_segment_label,
                    "segment_confidence": snapshot.prospect.segment_confidence,
                    "ai_maturity_score": snapshot.prospect.ai_maturity_score,
                    "bench_match": snapshot.hiring_signal_brief.bench_match.model_dump(mode="json"),
                    "last_inbound_channel": message.channel,
                    "last_reply_next_action": decision.next_action,
                    "trace_id": snapshot.trace_id,
                    "booking_status": "pending_confirmation" if decision.next_action == "book_meeting" else None,
                },
                snapshot.prospect.prospect_id,
                activity_type=f"{message.channel}_reply_received",
                activity_summary=f"Inbound {message.channel} reply processed with next action {decision.next_action}.",
                metadata={
                    "risk_flags": decision.risk_flags,
                    "side_effects": [effect.model_dump(mode="json") for effect in side_effects],
                    "channel_state": self.handoff_manager.current_state(snapshot.prospect.prospect_id),
                },
            ),
            max_attempts=1,
        )
        self._handle_tool_result(hubspot_results, snapshot.prospect.prospect_id, "hubspot_inbound_sync")

        return decision

    def handle_calendar_confirmation(self, confirmation: dict[str, str]) -> dict[str, object]:
        snapshot = self.repository.find_snapshot_by_contact(contact_email=confirmation["contact_email"])
        if snapshot is None:
            self.trace_logger.log("calendar_confirmation_unmatched", confirmation)
            return {"ok": False, "matched": False, "reason": "No prospect matched the booking confirmation."}

        review = review_before_action(
            {
                "prospect_context": snapshot.prospect.model_dump(mode="json"),
                "hiring_signal_brief": snapshot.hiring_signal_brief.model_dump(mode="json"),
                "competitor_gap_brief": snapshot.competitor_gap_brief.model_dump(mode="json"),
                "agent_output": json.dumps(confirmation, ensure_ascii=False),
                "action_type": "calendar_action",
                "channel": "calendar",
                "prospect_id": snapshot.prospect.prospect_id,
            }
        )
        if not review["allow"]:
            return {
                "ok": False,
                "matched": True,
                "prospect_id": snapshot.prospect.prospect_id,
                "route_to_review": review["route_to_review"],
                "reason": review["reason"],
            }

        self.repository.record_interaction_event(
            snapshot.prospect.prospect_id,
            "booking_confirmed",
            channel="calendar",
            provider="calcom",
            payload=confirmation,
        )
        self.repository.update_status(snapshot.prospect.prospect_id, "booked")
        voice_result = self.handoff_manager.prepare_voice_handoff(
            snapshot,
            reason="calendar_booking_confirmed",
            booking_status=confirmation["booking_status"],
            force_allow=True,
        )
        self._handle_tool_result(
            voice_result,
            snapshot.prospect.prospect_id,
            "voice_booking_handoff",
        )
        hubspot_results = _with_retries(
            lambda: hubspot_client.record_conversation_event(
                {
                    "company_name": snapshot.prospect.company_name,
                    "company_domain": snapshot.prospect.company_domain,
                    "email": snapshot.prospect.contact_email,
                    "contact_name": snapshot.prospect.contact_name,
                    "phone": snapshot.prospect.contact_phone,
                    "segment": snapshot.prospect.primary_segment_label,
                    "segment_confidence": snapshot.prospect.segment_confidence,
                    "ai_maturity_score": snapshot.prospect.ai_maturity_score,
                    "bench_match": snapshot.hiring_signal_brief.bench_match.model_dump(mode="json"),
                    "trace_id": snapshot.trace_id,
                    "booking_status": confirmation["booking_status"],
                },
                snapshot.prospect.prospect_id,
                activity_type="calendar_booking_confirmed",
                activity_summary="Cal.com booking confirmation received and prospect marked as booked.",
                metadata={
                    **confirmation,
                    "side_effects": [voice_result.model_dump(mode="json")],
                    "channel_state": self.handoff_manager.current_state(snapshot.prospect.prospect_id),
                },
            ),
            max_attempts=2,
        )
        self._handle_tool_result(hubspot_results, snapshot.prospect.prospect_id, "hubspot_booking_confirmed_sync")
        trace_id = snapshot.trace_id or self.trace_logger.new_trace_id()
        self.trace_logger.log(
            "calendar_booking_confirmed",
            {
                "prospect_id": snapshot.prospect.prospect_id,
                "company_name": snapshot.prospect.company_name,
                "booking_external_id": confirmation["booking_external_id"],
                "booking_status": confirmation["booking_status"],
                "hubspot_results": [result.model_dump(mode="json") for result in hubspot_results],
            },
            trace_id=trace_id,
        )
        return {
            "ok": True,
            "matched": True,
            "prospect_id": snapshot.prospect.prospect_id,
            "trace_id": trace_id,
        }

    def list_prospects(self) -> list[ProspectRecord]:
        return self.repository.list_all()

    def get_snapshot(self, prospect_id: str) -> ProspectEnrichmentResponse | None:
        return self.repository.get_snapshot(prospect_id)

    def dashboard_state(self, limit: int = 6) -> DashboardStateResponse:
        recent_snapshots = self.repository.list_recent_snapshots(limit=limit)
        traces = [
            RecentTrace(
                trace_id=entry["trace_id"],
                event_type=entry["event_type"],
                timestamp=entry["timestamp"],
                company_name=entry["payload"].get("company_name"),
                prospect_id=entry["payload"].get("prospect_id"),
            )
            for entry in self.trace_logger.recent(limit=limit)
        ]
        latest_snapshot = recent_snapshots[0] if recent_snapshots else None
        latest_events: list[DashboardInteractionEvent] = []
        latest_artifacts: list[DashboardArtifact] = []
        latest_flow: DashboardFlowSummary | None = None
        if latest_snapshot is not None:
            raw_events = self.repository.list_interaction_events(latest_snapshot.prospect.prospect_id)
            latest_events = [
                DashboardInteractionEvent(
                    event_type=event["event_type"],
                    channel=event["channel"],
                    provider=event["provider"],
                    created_at=event["created_at"],
                    payload_summary=self._summarize_event_payload(event["payload"]),
                )
                for event in raw_events[-10:]
            ]
            latest_artifacts = self._artifacts_for_prospect(latest_snapshot.prospect.prospect_id)
            latest_flow = DashboardFlowSummary(
                prospect_id=latest_snapshot.prospect.prospect_id,
                company_name=latest_snapshot.prospect.company_name,
                status=latest_snapshot.prospect.status,
                current_state=self.handoff_manager.current_state(latest_snapshot.prospect.prospect_id),
                latest_event=raw_events[-1]["event_type"] if raw_events else None,
                booking_status=(
                    raw_events[-1]["payload"].get("booking_status")
                    if raw_events and raw_events[-1]["event_type"] == "booking_confirmed"
                    else (
                        "confirmed"
                        if any(event["event_type"] == "booking_confirmed" for event in raw_events)
                        else "pending"
                        if any(event["event_type"] == "booking_link_shared" for event in raw_events)
                        else "not_started"
                    )
                ),
                voice_handoff_ready=any(event["event_type"] == "voice_handoff_sent" for event in raw_events),
                crm_logged=any(artifact.name == "hubspot" for artifact in latest_artifacts),
            )
        return DashboardStateResponse(
            total_prospects=self.repository.count(),
            total_traces=self.trace_logger.count(),
            tool_statuses=self.tool_statuses(),
            recent_snapshots=recent_snapshots,
            recent_traces=traces,
            latest_flow=latest_flow,
            latest_interaction_events=latest_events,
            latest_artifacts=latest_artifacts,
        )

    def tool_statuses(self) -> list[ToolStatus]:
        return [
            crunchbase_connector.status(),
            job_posts_connector.status(),
            layoffs_connector.status(),
            leadership_connector.status(),
            email_channel.status(),
            sms_channel.status(),
            voice_channel.status(),
            hubspot_client.status(),
            calcom_client.status(),
            generation_service.status(),
            langfuse_client.status(),
            tau2_adapter.status(),
        ]

    def _extract_email_payload(self, draft: str) -> tuple[str, str]:
        lines = [line for line in draft.splitlines() if line.strip()]
        if lines and lines[0].lower().startswith("subject:"):
            subject = lines[0].split(":", 1)[1].strip() or "Tenacious research note"
            body = "\n".join(lines[1:]).strip()
            return subject, body
        return "Tenacious research note", draft

    def _summarize_event_payload(self, payload: dict) -> str | None:
        if not payload:
            return None
        for key in ("subject", "message", "body", "result", "source_channel", "booking_status"):
            value = payload.get(key)
            if value:
                text = str(value).strip()
                return text if len(text) <= 180 else f"{text[:177]}..."
        rendered = str(payload)
        return rendered if len(rendered) <= 180 else f"{rendered[:177]}..."

    def _artifact_preview(self, path: Path, *, max_chars: int = 220) -> str | None:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None
        compact = " ".join(text.strip().split())
        if not compact:
            return None
        return compact if len(compact) <= max_chars else f"{compact[: max_chars - 3]}..."

    def _artifacts_for_prospect(self, prospect_id: str) -> list[DashboardArtifact]:
        artifacts: list[DashboardArtifact] = []
        suffix_map = {
            "email": ("json", "application/json"),
            "sms": ("json", "application/json"),
            "voice": ("json", "application/json"),
            "hubspot": ("json", "application/json"),
            "langfuse": ("json", "application/json"),
            "calcom": ("json", "application/json"),
            "context_brief": ("md", "text/markdown"),
        }
        for name, (extension, content_type) in suffix_map.items():
            path = settings.outbox_dir / f"{prospect_id}_{name}.{extension}"
            if not path.exists():
                continue
            artifacts.append(
                DashboardArtifact(
                    name=name,
                    path=str(path),
                    exists=True,
                    preview=self._artifact_preview(path),
                    content_type=content_type,
                    route=f"/artifacts/{prospect_id}/{name}",
                )
            )
        return artifacts


orchestrator = Orchestrator()
