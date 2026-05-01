import json
from urllib.error import HTTPError

from agent.config import settings
from agent.evaluation.comparison_service import comparison_dry_run_enabled, comparison_mode_enabled
from agent.evaluation.tenacious_judge_adapter import review_before_action
from agent.schemas.prospect import InboundMessageRequest
from agent.schemas.tools import ToolExecutionResult, ToolStatus
from agent.scheduling.calcom import calcom_client
from agent.utils.http import request_json


class EmailWebhookError(RuntimeError):
    pass


class EmailChannel:
    def _http_error_detail(self, exc: HTTPError) -> str:
        try:
            raw = exc.read().decode("utf-8").strip()
        except Exception:
            return ""
        if not raw:
            return ""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        for key in ("message", "error", "detail"):
            value = parsed.get(key)
            if value:
                return str(value)
        return raw

    def _sender_is_live_ready(self) -> bool:
        provider = settings.email_provider.lower()
        sender = (
            settings.resend_from_email
            if provider == "resend"
            else settings.mailersend_from_email
        )
        if not sender:
            return False
        lowered = sender.lower()
        return not (lowered.endswith(".local") or lowered.endswith(".example"))

    def status(self) -> ToolStatus:
        provider = settings.email_provider.lower()
        if provider == "resend":
            configured = bool(
                settings.outbound_enabled
                and settings.resend_api_key
                and self._sender_is_live_ready()
            )
            return ToolStatus(
                name="email",
                label="Resend Email",
                mode="configured" if configured else "mock",
                configured=configured,
                available=True,
                details=(
                    "Uses Resend only when OUTBOUND_ENABLED=true, API credentials are present, "
                    "and the sender address is a real provider-ready address; otherwise writes draft outbox artifacts."
                ),
            )
        if provider == "mailersend":
            configured = bool(
                settings.outbound_enabled
                and settings.mailersend_api_key
                and self._sender_is_live_ready()
            )
            return ToolStatus(
                name="email",
                label="MailerSend Email",
                mode="configured" if configured else "mock",
                configured=configured,
                available=True,
                details=(
                    "Uses MailerSend only when OUTBOUND_ENABLED=true, API credentials are present, "
                    "and the sender address is a real provider-ready address; otherwise writes draft outbox artifacts."
                ),
            )
        return ToolStatus(
            name="email",
            label="Email Draft Outbox",
            mode="mock",
            configured=False,
            available=True,
            details="No live provider selected, so outbound email is captured locally.",
        )

    def _write_artifact(self, payload: dict, prospect_id: str) -> str:
        settings.outbox_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = settings.outbox_dir / f"{prospect_id}_email.json"
        artifact_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        return str(artifact_path)

    def send(
        self,
        recipient: str | None,
        subject: str,
        body: str,
        prospect_id: str,
        *,
        prospect_context: dict | None = None,
        hiring_signal_brief: dict | None = None,
        competitor_gap_brief: dict | None = None,
    ) -> ToolExecutionResult:
        review = review_before_action(
            {
                "prospect_context": prospect_context
                or {"prospect_id": prospect_id, "contact_email": recipient},
                "hiring_signal_brief": hiring_signal_brief or {},
                "competitor_gap_brief": competitor_gap_brief or {},
                "agent_output": f"Subject: {subject}\n\n{body}",
                "action_type": "email",
                "channel": "email",
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
                    "provider": settings.email_provider,
                    "draft": True,
                    "outbound_enabled": False,
                    "comparison_mode": comparison_mode_enabled(),
                    "comparison_dry_run": comparison_dry_run_enabled(),
                    "recipient": recipient or settings.resend_from_email,
                    "subject": subject,
                    "body": body,
                    "week11_status": preview_label,
                    "judge_review": {
                        "verdict": verdict,
                        "reason": review["reason"],
                    },
                },
                prospect_id,
            )
            return ToolExecutionResult(
                name="email",
                mode=self.status().mode,
                status="skipped",
                message=f"{preview_label}: {review['reason']}",
                artifact_ref=artifact_ref,
            )

        payload = {
            "provider": settings.email_provider,
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
            "judge_review": {
                "verdict": (review.get("judge") or {}).get("verdict"),
                "reason": review.get("reason"),
            },
            "recipient": recipient or settings.resend_from_email,
            "subject": subject,
            "body": body,
        }
        artifact_ref = self._write_artifact(payload, prospect_id)
        status = self.status()
        if comparison_mode_enabled() and comparison_dry_run_enabled():
            return ToolExecutionResult(
                name="email",
                mode="mock",
                status="previewed",
                message=f"Would send email to {recipient or 'local sink'}; comparison dry-run is enabled.",
                artifact_ref=artifact_ref,
            )
        if recipient and status.configured:
            try:
                if settings.email_provider.lower() == "resend":
                    _, response, _ = request_json(
                        "POST",
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {settings.resend_api_key}",
                        },
                        payload={
                            "from": settings.resend_from_email,
                            "to": [recipient],
                            "subject": subject,
                            "text": body,
                            "html": f"<pre>{body}</pre>",
                            **(
                                {"reply_to": settings.resend_reply_to}
                                if settings.resend_reply_to
                                else {}
                            ),
                        },
                    )
                    external_id = response.get("id")
                else:
                    _, _, response_headers = request_json(
                        "POST",
                        "https://api.mailersend.com/v1/email",
                        headers={
                            "Authorization": f"Bearer {settings.mailersend_api_key}",
                        },
                        payload={
                            "from": {
                                "email": settings.mailersend_from_email,
                                "name": settings.mailersend_from_name,
                            },
                            "to": [{"email": recipient}],
                            "subject": subject,
                            "text": body,
                            "html": f"<pre>{body}</pre>",
                        },
                    )
                    external_id = response_headers.get("x-message-id")
                return ToolExecutionResult(
                    name="email",
                    mode="configured",
                    status="executed",
                    message=f"Live email submitted for delivery to {recipient}.",
                    artifact_ref=artifact_ref,
                    external_id=external_id,
                )
            except HTTPError as exc:
                detail = self._http_error_detail(exc)
                if exc.code in {401, 403}:
                    return ToolExecutionResult(
                        name="email",
                        mode="mock",
                        status="previewed",
                        message=(
                            "Live email provider rejected the current credentials or sender identity; "
                            f"kept a draft artifact instead ({exc}{f': {detail}' if detail else ''})."
                        ),
                        artifact_ref=artifact_ref,
                    )
                return ToolExecutionResult(
                    name="email",
                    mode="configured",
                    status="error",
                    message=f"Live email call failed: {exc}{f': {detail}' if detail else ''}",
                    artifact_ref=artifact_ref,
                )
            except Exception as exc:
                return ToolExecutionResult(
                    name="email",
                    mode="configured",
                    status="error",
                    message=f"Live email call failed: {exc}",
                    artifact_ref=artifact_ref,
                )
        return ToolExecutionResult(
            name="email",
            mode=status.mode,
            status="executed" if status.configured else "previewed",
            message=(
                f"Email payload prepared for {recipient or 'local sink'} via {status.label}."
            ),
            artifact_ref=artifact_ref,
        )

    def send_booking_options(
        self,
        *,
        recipient: str | None,
        prospect_id: str,
        company_name: str,
        contact_name: str | None,
        contact_email: str | None,
    ) -> tuple[ToolExecutionResult, str]:
        booking_link, _ = calcom_client.generate_booking_link(
            company_name=company_name,
            contact_email=contact_email,
            prospect_id=prospect_id,
            source_channel="email",
        )
        body = (
            f"Hi {contact_name or 'there'},\n\n"
            "I set aside two discovery-call options for the delivery lead. "
            f"You can confirm the best slot here: {booking_link}\n\n"
            "If you prefer, reply with two windows and I will line it up manually.\n\n"
            "Best,\nTenacious research workflow"
        )
        result = self.send(
            recipient=recipient,
            subject=f"Booking options for {company_name}",
            body=body,
            prospect_id=prospect_id,
            prospect_context={
                "prospect_id": prospect_id,
                "company_name": company_name,
                "contact_name": contact_name,
                "contact_email": contact_email,
            },
        )
        return result, body

    def handle_resend_reply_webhook(self, payload: dict) -> InboundMessageRequest:
        body = payload.get("body") if isinstance(payload.get("body"), dict) else payload
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        sender = data.get("from") or data.get("reply_to") or body.get("from")
        if isinstance(sender, list):
            sender = sender[0] if sender else None
        if isinstance(sender, dict):
            sender = sender.get("email") or sender.get("from")
        message_body = (
            data.get("text")
            or data.get("textBody")
            or body.get("text")
            or body.get("textBody")
            or data.get("html")
            or body.get("html")
        )
        if not sender or not message_body:
            raise EmailWebhookError(
                "Resend reply webhook is missing sender email or reply body."
            )
        return InboundMessageRequest(
            contact_email=str(sender).strip().lower(),
            channel="email",
            body=str(message_body).strip(),
        )

    def handle_mailersend_reply_webhook(self, payload: dict) -> InboundMessageRequest:
        body = payload.get("body") if isinstance(payload.get("body"), dict) else payload
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        sender = data.get("from") or body.get("from") or data.get("sender")
        if isinstance(sender, list):
            sender = sender[0] if sender else None
        if isinstance(sender, dict):
            sender = sender.get("email") or sender.get("address")
        message_body = (
            data.get("text")
            or data.get("text_plain")
            or body.get("text")
            or body.get("text_plain")
            or data.get("html")
            or body.get("html")
        )
        if not sender or not message_body:
            raise EmailWebhookError(
                "MailerSend reply webhook is missing sender email or reply body."
            )
        return InboundMessageRequest(
            contact_email=str(sender).strip().lower(),
            channel="email",
            body=str(message_body).strip(),
        )


email_channel = EmailChannel()
