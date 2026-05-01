from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from agent.config import settings
from agent.observability.langfuse import langfuse_client
from agent.schemas.tools import ToolStatus
from agent.seed.loader import seed_materials
from agent.utils.http import request_json

logger = logging.getLogger(__name__)

_OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
_STANDARD_SIGNATURE = (
    "Best regards,\n"
    "The Tenacious Team\n"
    "Tenacious Intelligence Corporation\n"
    "gettenacious.com"
)


@dataclass(frozen=True)
class EmailDraft:
    subject: str
    body: str
    source: str
    model: str | None = None
    error: str | None = None

    @property
    def as_reply_draft(self) -> str:
        return f"Subject: {self.subject}\n\n{self.body}"


class GenerationService:
    def status(self) -> ToolStatus:
        configured = bool(settings.openrouter_api_key and settings.openrouter_model)
        return ToolStatus(
            name="llm_generation",
            label="OpenRouter Draft Generation",
            mode="configured" if configured else "mock",
            configured=configured,
            available=True,
            details=(
                "Uses OpenRouter to rewrite outreach and reply drafts, with deterministic fallback when "
                "OPENROUTER_API_KEY / OPENROUTER_MODEL are not configured."
            ),
        )

    def draft_email_from_scaffold(
        self,
        *,
        trace_id: str | None,
        prospect_id: str,
        scenario: str,
        company_name: str,
        contact_name: str | None,
        fallback_subject: str,
        fallback_body: str,
        context: dict[str, object],
    ) -> EmailDraft:
        fallback = EmailDraft(
            subject=fallback_subject,
            body=fallback_body,
            source="deterministic_fallback",
        )
        status = self.status()
        if not status.configured:
            return fallback

        input_payload = {
            "scenario": scenario,
            "company_name": company_name,
            "contact_name": contact_name,
            "context": context,
            "fallback_subject": fallback_subject,
            "fallback_body": fallback_body,
        }

        def _operation() -> tuple[EmailDraft, dict, dict[str, int] | None, dict[str, float] | None]:
            response = self._chat_completion(
                messages=self._messages_for_scenario(
                    scenario=scenario,
                    company_name=company_name,
                    contact_name=contact_name,
                    fallback_subject=fallback_subject,
                    fallback_body=fallback_body,
                    context=context,
                ),
            )
            content = self._response_content(response)
            parsed = self._extract_email_json(content)
            subject = self._normalize_subject(parsed.get("subject") or fallback_subject)
            body = self._normalize_body(
                parsed.get("body") or fallback_body,
                fallback_body=fallback_body,
            )
            violations = seed_materials.validate_email_style(
                subject,
                self._body_without_signature(body),
            )
            if violations:
                raise ValueError(
                    "Generated draft violated the Tenacious style guide: "
                    + ", ".join(violations)
                )

            result = EmailDraft(
                subject=subject,
                body=body,
                source="openrouter",
                model=response.get("model") or settings.openrouter_model,
            )
            return (
                result,
                {
                    "subject": subject,
                    "body": body,
                    "source": result.source,
                    "prospect_id": prospect_id,
                },
                self._usage_details(response),
                self._cost_details(response),
            )

        try:
            return langfuse_client.run_generation(
                trace_id=trace_id,
                name=f"email_draft_{scenario}",
                model=settings.openrouter_model,
                input_payload=input_payload,
                metadata={"prospect_id": prospect_id, "scenario": scenario},
                model_parameters={"temperature": 0.2},
                operation=_operation,
            )
        except Exception as exc:
            logger.warning(
                "OpenRouter draft generation failed for prospect=%s scenario=%s: %s",
                prospect_id,
                scenario,
                exc,
            )
            return EmailDraft(
                subject=fallback_subject,
                body=fallback_body,
                source="deterministic_fallback",
                error=str(exc),
            )

    def _chat_completion(self, *, messages: list[dict[str, object]]) -> dict:
        _, response, _ = request_json(
            "POST",
            _OPENROUTER_CHAT_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "HTTP-Referer": settings.app_base_url,
                "X-Title": "The Conversion Engine",
            },
            payload={
                "model": settings.openrouter_model,
                "messages": messages,
                "temperature": 0.2,
            },
            timeout=12,
        )
        return response

    def _messages_for_scenario(
        self,
        *,
        scenario: str,
        company_name: str,
        contact_name: str | None,
        fallback_subject: str,
        fallback_body: str,
        context: dict[str, object],
    ) -> list[dict[str, object]]:
        banned_cliches = sorted(seed_materials.style.banned_vendor_cliches)
        system_prompt = (
            "You are the Tenacious email drafting copilot. Rewrite the provided safe scaffold into a stronger "
            "prospect-facing email while staying strictly grounded in the supplied facts. "
            "Never invent funding, hiring, layoffs, leadership changes, competitor practices, pricing, or bench capacity. "
            "Never repeat, echo, or acknowledge pricing requests (fixed price, discount, savings) from the prospect — "
            "instead redirect to understanding their constraints without using any pricing language. "
            "If a competitor gap is mentioned, frame it as a question or research finding rather than a claim that the prospect is behind. "
            "Keep the subject under 60 characters. Keep the body under 120 words excluding the signature. "
            "Preserve the Tenacious signature block. Avoid these banned phrases: "
            + ", ".join(banned_cliches)
            + ". Respond with valid JSON only in the shape {\"subject\": \"...\", \"body\": \"...\"}."
        )
        user_prompt = {
            "scenario": scenario,
            "company_name": company_name,
            "contact_name": contact_name,
            "context": context,
            "safe_scaffold": {
                "subject": fallback_subject,
                "body": fallback_body,
            },
        }
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=True, indent=2)},
        ]

    def _response_content(self, response: dict) -> str:
        choices = response.get("choices") or []
        if not choices:
            raise ValueError("OpenRouter returned no choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            rendered = "".join(text_parts).strip()
            if rendered:
                return rendered
        raise ValueError("OpenRouter returned an empty message content.")

    def _extract_email_json(self, raw: str) -> dict[str, str]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items() if v is not None}
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(raw[start : end + 1])
                if isinstance(parsed, dict):
                    return {str(k): str(v) for k, v in parsed.items() if v is not None}
        raise ValueError("OpenRouter did not return a valid JSON email draft.")

    def _normalize_subject(self, subject: str) -> str:
        cleaned = " ".join(subject.strip().split())
        if cleaned.lower().startswith("subject:"):
            cleaned = cleaned.split(":", 1)[1].strip()
        return cleaned or "Tenacious research note"

    def _normalize_body(self, body: str, *, fallback_body: str) -> str:
        cleaned = body.strip().replace("\r\n", "\n")
        signature = self._signature_from_fallback(fallback_body)
        if signature not in cleaned:
            base = self._body_without_signature(cleaned).strip()
            cleaned = f"{base}\n\n{signature}".strip()
        return cleaned

    def _signature_from_fallback(self, fallback_body: str) -> str:
        for prefix in ("\n\nBest regards,", "\nBest regards,", "\n\nBest,", "\nBest,"):
            if prefix in fallback_body:
                keyword = prefix.lstrip("\n")
                suffix = fallback_body.split(prefix, 1)[1].strip()
                return f"{keyword}\n{suffix}" if suffix else _STANDARD_SIGNATURE
        return _STANDARD_SIGNATURE

    def _body_without_signature(self, body: str) -> str:
        for marker in ("\n\nBest regards,", "\nBest regards,", "\n\nBest,", "\nBest,"):
            if marker in body:
                return body.split(marker, 1)[0].strip()
        return body.strip()

    def _usage_details(self, response: dict) -> dict[str, int] | None:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return None
        details: dict[str, int] = {}
        for src_key, dst_key in (
            ("prompt_tokens", "input"),
            ("completion_tokens", "output"),
            ("total_tokens", "total"),
        ):
            value = usage.get(src_key)
            if isinstance(value, int):
                details[dst_key] = value
        return details or None

    def _cost_details(self, response: dict) -> dict[str, float] | None:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            return None
        cost_value = usage.get("cost")
        if isinstance(cost_value, (int, float)):
            return {"total": float(cost_value)}
        return None


generation_service = GenerationService()
