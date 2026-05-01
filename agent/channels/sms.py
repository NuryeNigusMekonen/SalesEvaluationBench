import json
from urllib.error import HTTPError

from agent.config import settings
from agent.evaluation.comparison_service import comparison_dry_run_enabled, comparison_mode_enabled
from agent.evaluation.tenacious_judge_adapter import review_before_action
from agent.schemas.prospect import InboundMessageRequest
from agent.schemas.tools import ToolExecutionResult, ToolStatus
from agent.scheduling.calcom import calcom_client
from agent.utils.http import request_form


class SmsWebhookError(RuntimeError):
    pass


class SmsChannel:
    def status(self) -> ToolStatus:
        configured = bool(
            settings.outbound_enabled
            and settings.sms_provider.lower() == "africastalking"
            and settings.africas_talking_username
            and settings.africas_talking_api_key
        )
        return ToolStatus(
            name="sms",
            label="Africa's Talking SMS",
            mode="configured" if configured else "mock",
            configured=configured,
            available=True,
            details="Warm-lead SMS handoff uses Africa's Talking only when OUTBOUND_ENABLED=true and credentials are present; otherwise a local preview artifact.",
        )

    def _write_artifact(self, payload: dict, prospect_id: str) -> str:
        settings.outbox_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = settings.outbox_dir / f"{prospect_id}_sms.json"
        artifact_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        return str(artifact_path)

    def send(
        self,
        phone_number: str | None,
        body: str,
        prospect_id: str,
        *,
        allow_warm_lead: bool = False,
        booking_link: str | None = None,
        prospect_context: dict | None = None,
        hiring_signal_brief: dict | None = None,
        competitor_gap_brief: dict | None = None,
    ) -> ToolExecutionResult:
        review = review_before_action(
            {
                "prospect_context": prospect_context
                or {"prospect_id": prospect_id, "contact_phone": phone_number},
                "hiring_signal_brief": hiring_signal_brief or {},
                "competitor_gap_brief": competitor_gap_brief or {},
                "agent_output": body,
                "action_type": "sms",
                "channel": "sms",
                "prospect_id": prospect_id,
            }
        )
        if not review["allow"]:
            judge = review.get("judge") or {}
            verdict = judge.get("verdict")
            preview_label = (
                "Needs human review"
                if review.get("route_to_review") or verdict == "needs_human_review"
                else "Blocked by Week 11 judge"
            )
            artifact_ref = self._write_artifact(
                {
                    "provider": settings.sms_provider,
                    "draft": True,
                    "outbound_enabled": False,
                    "comparison_mode": comparison_mode_enabled(),
                    "comparison_dry_run": comparison_dry_run_enabled(),
                    "phone_number": phone_number or "warm-lead-preview",
                    "body": body,
                    "warm_lead_gate_passed": allow_warm_lead,
                    "booking_link": booking_link,
                    "week11_status": preview_label,
                    "judge_review": {
                        "verdict": verdict,
                        "reason": review["reason"],
                    },
                },
                prospect_id,
            )
            return ToolExecutionResult(
                name="sms",
                mode=self.status().mode,
                status="skipped",
                message=f"{preview_label}: {review['reason']}",
                artifact_ref=artifact_ref,
            )

        payload = {
            "provider": settings.sms_provider,
            "draft": True,
            "outbound_enabled": (
                settings.outbound_enabled
                and not (comparison_mode_enabled() and comparison_dry_run_enabled())
            ),
            "comparison_mode": comparison_mode_enabled(),
            "comparison_dry_run": comparison_dry_run_enabled(),
            "week11_status": (
                "Would send"
                if comparison_mode_enabled() and comparison_dry_run_enabled()
                else "Allowed by Week 11 judge"
            ),
            "phone_number": phone_number or "warm-lead-preview",
            "body": body,
            "warm_lead_gate_passed": allow_warm_lead,
            "booking_link": booking_link,
        }
        artifact_ref = self._write_artifact(payload, prospect_id)
        status = self.status()
        if not allow_warm_lead:
            return ToolExecutionResult(
                name="sms",
                mode=status.mode,
                status="skipped",
                message="SMS send blocked by warm-lead gate because no prior email reply is recorded.",
                artifact_ref=artifact_ref,
            )
        if comparison_mode_enabled() and comparison_dry_run_enabled():
            return ToolExecutionResult(
                name="sms",
                mode="mock",
                status="previewed",
                message="Would send SMS; comparison dry-run is enabled.",
                artifact_ref=artifact_ref,
            )
        if status.configured and phone_number:
            try:
                is_sandbox = getattr(settings, "africas_talking_env", "production").lower() == "sandbox" or settings.africas_talking_username.lower() == "sandbox"
                at_base = "https://api.sandbox.africastalking.com" if is_sandbox else "https://api.africastalking.com"
                at_payload: dict = {
                    "username": settings.africas_talking_username,
                    "to": phone_number,
                    "message": body,
                }
                if settings.africas_talking_sender_id:
                    at_payload["from"] = settings.africas_talking_sender_id
                _, response_text, _ = request_form(
                    "POST",
                    f"{at_base}/version1/messaging",
                    headers={
                        "apiKey": settings.africas_talking_api_key,
                        "Accept": "application/json",
                    },
                    payload=at_payload,
                )
                return ToolExecutionResult(
                    name="sms",
                    mode="configured",
                    status="executed",
                    message="Live SMS request submitted to Africa's Talking.",
                    artifact_ref=artifact_ref,
                    external_id=response_text[:120],
                )
            except HTTPError as exc:
                if exc.code in {401, 403}:
                    return ToolExecutionResult(
                        name="sms",
                        mode="mock",
                        status="previewed",
                        message=(
                            "Live SMS provider rejected the current credentials or sender identity; "
                            f"kept a warm-lead preview artifact instead ({exc})."
                        ),
                        artifact_ref=artifact_ref,
                    )
                return ToolExecutionResult(
                    name="sms",
                    mode="configured",
                    status="error",
                    message=f"Live SMS call failed: {exc}",
                    artifact_ref=artifact_ref,
                )
            except Exception as exc:
                return ToolExecutionResult(
                    name="sms",
                    mode="configured",
                    status="error",
                    message=f"Live SMS call failed: {exc}",
                    artifact_ref=artifact_ref,
                )
        return ToolExecutionResult(
            name="sms",
            mode=status.mode,
            status="executed" if status.configured and phone_number else "previewed",
            message=(
                "SMS handoff prepared for a warm lead."
                if phone_number
                else "SMS handoff preview captured because no phone number was provided."
            ),
            artifact_ref=artifact_ref,
        )

    def send_booking_options(
        self,
        *,
        phone_number: str | None,
        prospect_id: str,
        company_name: str,
        contact_name: str | None,
        contact_email: str | None,
        allow_warm_lead: bool = False,
        prospect_context: dict | None = None,
        hiring_signal_brief: dict | None = None,
        competitor_gap_brief: dict | None = None,
    ) -> tuple[ToolExecutionResult, str]:
        booking_link, _ = calcom_client.generate_booking_link(
            company_name=company_name,
            contact_email=contact_email,
            prospect_id=prospect_id,
            source_channel="sms",
        )
        body = (
            f"Hi {contact_name or 'there'}, your discovery-call link is ready: {booking_link}. "
            "Reply here if you want me to coordinate a different time."
        )
        result = self.send(
            phone_number=phone_number,
            body=body,
            prospect_id=prospect_id,
            allow_warm_lead=allow_warm_lead,
            booking_link=booking_link,
            prospect_context=prospect_context
            or {
                "prospect_id": prospect_id,
                "company_name": company_name,
                "contact_name": contact_name,
                "contact_email": contact_email,
                "contact_phone": phone_number,
            },
            hiring_signal_brief=hiring_signal_brief,
            competitor_gap_brief=competitor_gap_brief,
        )
        return result, body

    def handle_africastalking_webhook(self, payload: dict) -> InboundMessageRequest:
        body = payload.get("body") if isinstance(payload.get("body"), dict) else payload
        sender = body.get("from") or body.get("phoneNumber") or body.get("msisdn")
        message_body = body.get("text") or body.get("body") or body.get("message")
        if not sender or not message_body:
            raise SmsWebhookError(
                "Africa's Talking inbound webhook is missing sender phone number or message body."
            )
        return InboundMessageRequest(
            contact_phone=str(sender).strip(),
            channel="sms",
            body=str(message_body).strip(),
        )


sms_channel = SmsChannel()
