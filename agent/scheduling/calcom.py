import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from agent.config import settings
from agent.evaluation.tenacious_judge_adapter import review_before_action
from agent.schemas.tools import ToolExecutionResult, ToolStatus


class CalComWebhookError(RuntimeError):
    pass


class CalComClient:
    def status(self) -> ToolStatus:
        configured = bool(settings.calcom_api_key and settings.calcom_event_type_id)
        return ToolStatus(
            name="calcom",
            label="Cal.com Scheduling",
            mode="configured" if configured else "mock",
            configured=configured,
            available=True,
            details="Booking flow creates live bookings when CALCOM_API_KEY and CALCOM_EVENT_TYPE_ID are configured.",
        )

    def _write_artifact(self, payload: dict, prospect_id: str) -> str:
        settings.outbox_dir.mkdir(parents=True, exist_ok=True)
        slot_a = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=1, hours=14)
        slot_b = slot_a + timedelta(hours=2)
        artifact_path = settings.outbox_dir / f"{prospect_id}_calcom.json"
        payload.setdefault("suggested_slots_utc", [slot_a.isoformat(), slot_b.isoformat()])
        artifact_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(artifact_path)

    def generate_booking_link(
        self,
        *,
        company_name: str,
        contact_email: str | None,
        prospect_id: str,
        source_channel: str,
    ) -> tuple[str, str]:
        base_url = "https://cal.com"
        if settings.calcom_username:
            base_url = f"{base_url}/{settings.calcom_username}/{settings.calcom_event_type_slug}"
        else:
            base_url = f"{base_url}/{settings.calcom_event_type_slug}"
        query = urlencode(
            {
                key: value
                for key, value in {
                    "email": contact_email or "",
                    "name": company_name,
                    "source": source_channel,
                    "utm_source": "conversion-engine",
                }.items()
                if value
            }
        )
        booking_link = f"{base_url}?{query}" if query else base_url
        artifact_ref = self._write_artifact(
            {
                "event_type_slug": settings.calcom_event_type_slug,
                "company_name": company_name,
                "contact_email": contact_email,
                "source_channel": source_channel,
                "booking_link": booking_link,
            },
            prospect_id,
        )
        return booking_link, artifact_ref

    def book_preview(self, company_name: str, contact_email: str | None, prospect_id: str) -> ToolExecutionResult:
        """Generate a scheduling preview artifact and booking link for the outbound pipeline.

        This method is intentionally non-mutating. It never creates a real Cal.com booking.
        Real bookings are confirmed only when the Cal.com webhook fires (booking.created /
        booking.rescheduled) and reaches POST /webhooks/calcom → handle_confirmation_webhook().

        The prospect receives the booking_link and self-selects a slot. Only after that
        webhook confirmation does the orchestrator call handle_calendar_confirmation() and
        mark the prospect as "booked" in SQLite.
        """
        review = review_before_action(
            {
                "prospect_context": {
                    "prospect_id": prospect_id,
                    "company_name": company_name,
                    "contact_email": contact_email,
                },
                "hiring_signal_brief": {},
                "competitor_gap_brief": {},
                "agent_output": (
                    "Generate a Cal.com scheduling preview and booking link for "
                    f"{company_name}."
                ),
                "action_type": "calendar_action",
                "channel": "calendar",
                "prospect_id": prospect_id,
            }
        )
        if not review["allow"]:
            return ToolExecutionResult(
                name="calcom",
                mode=self.status().mode,
                status="skipped",
                message=f"Calendar action blocked by Tenacious judge: {review['reason']}",
            )

        booking_link, artifact_ref = self.generate_booking_link(
            company_name=company_name,
            contact_email=contact_email,
            prospect_id=prospect_id,
            source_channel="calendar",
        )
        status = self.status()
        return ToolExecutionResult(
            name="calcom",
            mode=status.mode,
            status="previewed",
            message=(
                f"Scheduling preview generated. Booking link: {booking_link}. "
                "Real bookings are created only from Cal.com webhook confirmation."
            ),
            artifact_ref=artifact_ref,
        )

    def handle_confirmation_webhook(self, payload: dict) -> dict[str, str]:
        body = payload.get("body") if isinstance(payload.get("body"), dict) else payload
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        attendee = data.get("attendee") if isinstance(data.get("attendee"), dict) else {}
        contact_email = attendee.get("email") or data.get("email") or body.get("email")
        booking_external_id = (
            data.get("uid")
            or data.get("bookingUid")
            or data.get("booking_id")
            or data.get("id")
            or body.get("uid")
        )
        booking_status = (
            data.get("status")
            or body.get("status")
            or body.get("triggerEvent")
            or "confirmed"
        )
        if not contact_email or not booking_external_id:
            raise CalComWebhookError(
                "Cal.com confirmation webhook is missing attendee email or booking identifier."
            )
        return {
            "contact_email": str(contact_email).strip().lower(),
            "booking_external_id": str(booking_external_id),
            "booking_status": str(booking_status),
            "company_name": str(
                attendee.get("name") or data.get("title") or body.get("title") or "Unknown company"
            ),
        }


calcom_client = CalComClient()
