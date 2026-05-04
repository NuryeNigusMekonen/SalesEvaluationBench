import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from agent.api.dashboard import DASHBOARD_HTML
from agent.channels.email import EmailWebhookError, email_channel
from agent.channels.sms import SmsWebhookError, sms_channel
from agent.channels.voice import VoiceWebhookError, voice_channel
from agent.config import settings
from agent.evaluation.comparison_service import (
    compare_candidate_action,
    comparison_dry_run_enabled,
    judge_enabled,
    read_comparison_reviews,
)
from agent.evaluation.governance_courtroom import (
    governance_runtime_status,
    read_governance_reviews,
    review_candidate_action,
)
from agent.observability.tracing import TraceLogger
from agent.orchestration.service import orchestrator
from agent.schemas.briefs import ProspectEnrichmentResponse
from agent.schemas.conversation import ConversationDecision
from agent.schemas.dashboard import DashboardStateResponse
from agent.schemas.prospect import InboundMessageRequest, LeadIntakeRequest, ProspectRecord
from agent.schemas.tools import ToolStatus
from agent.scheduling.calcom import CalComWebhookError, calcom_client

router = APIRouter()
trace_logger = TraceLogger()


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return DASHBOARD_HTML


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/deploy/info")
def deployment_info() -> dict[str, object]:
    base = settings.app_base_url.rstrip("/")
    return {
        "app_base_url": base,
        "recommended_webhooks": {
            "resend": f"{base}/webhooks/resend",
            "mailersend": f"{base}/webhooks/mailersend",
            "africastalking": f"{base}/webhooks/africastalking",
            "voice": f"{base}/webhooks/voice",
            "calcom": f"{base}/webhooks/calcom",
            "hubspot": f"{base}/webhooks/hubspot",
        },
        "render_ready": Path("render.yaml").exists(),
    }


@router.get("/dashboard/state", response_model=DashboardStateResponse)
def dashboard_state() -> DashboardStateResponse:
    return orchestrator.dashboard_state()


@router.get("/tools/status", response_model=list[ToolStatus])
def tools_status() -> list[ToolStatus]:
    return orchestrator.tool_statuses()


@router.get("/api/comparison-reviews")
def comparison_reviews(limit: int = 50) -> list[dict]:
    return read_comparison_reviews(limit=limit)


@router.get("/api/governance/reviews")
def governance_reviews(limit: int = 50) -> list[dict]:
    return read_governance_reviews(limit=limit)


@router.get("/api/governance/runtime")
def governance_runtime() -> dict:
    return governance_runtime_status()


@router.post("/api/governance/review-candidate")
def governance_review_candidate(payload: dict) -> dict:
    review = review_candidate_action(payload)
    return {
        "ok": True,
        "review": review.model_dump(mode="json"),
    }


def _infer_comparison_scenario(body: str, explicit: str | None = None) -> str:
    if explicit:
        return explicit
    lowered = body.lower()
    if any(token in lowered for token in ("price", "pricing", "cost", "rate", "discount", "budget")):
        return "pricing"
    if any(token in lowered for token in ("stop", "unsubscribe", "remove me", "opt out")):
        return "stop"
    if any(token in lowered for token in ("sms", "text me", "calendar", "meeting", "schedule", "book", "call")):
        return "meeting"
    return "followup"


def _comparison_baseline_candidate(payload: dict) -> dict:
    prospect_id = payload.get("prospect_id")
    snapshot = orchestrator.get_snapshot(str(prospect_id)) if prospect_id else None
    if snapshot is None:
        snapshot = orchestrator.repository.find_snapshot_by_contact(
            contact_email=payload.get("contact_email"),
            contact_phone=payload.get("contact_phone"),
        )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Prospect snapshot not found for comparison.")

    scenario = _infer_comparison_scenario(
        str(payload.get("body") or ""),
        str(payload.get("scenario_name") or payload.get("scenario") or "") or None,
    )
    contact = snapshot.prospect.contact_name or "there"
    company = snapshot.prospect.company_name
    baseline_by_scenario = {
        "pricing": {
            "action_type": "email_reply",
            "channel": "email",
            "baseline_output": (
                f"Hi {contact}, the full build for {company} will be $48,000 fixed, "
                "and I can apply a 20% discount if you book this week. You should see "
                "at least 35% savings versus your current vendor."
            ),
            "improvement_summary": "prevented unsupported pricing claim",
        },
        "meeting": {
            "action_type": "calendar_action",
            "channel": "calendar",
            "baseline_output": (
                f"Hi {contact}, I booked a discovery call for Tuesday and sent the "
                "calendar link by SMS so we can move quickly."
            ),
            "improvement_summary": "prevented SMS/calendar escalation without confirmation",
        },
        "sms": {
            "action_type": "sms",
            "channel": "sms",
            "baseline_output": (
                f"Hi {contact}, here is your booking link by SMS. I also held a slot "
                "for you with our delivery lead."
            ),
            "improvement_summary": "prevented SMS escalation without explicit consent",
        },
        "followup": {
            "action_type": "email_reply",
            "channel": "email",
            "baseline_output": (
                f"Hi {contact}, Tenacious has world-class top talent and 60 engineers "
                "ready to deploy in 7-14 days for any stack you need."
            ),
            "improvement_summary": "prevented generic bench-capacity overclaim",
        },
        "stop": {
            "action_type": "crm_update",
            "channel": "crm",
            "baseline_output": (
                f"Hi {contact}, understood. Before I remove you, one final note: "
                "Tenacious could still help if hiring gets difficult later this quarter."
            ),
            "improvement_summary": "prevented follow-up after opt-out request",
        },
    }
    template = baseline_by_scenario.get(scenario, baseline_by_scenario["followup"])
    custom_baseline = str(payload.get("baseline_output") or "").strip()
    if custom_baseline:
        template = {**template, "baseline_output": custom_baseline, "improvement_summary": "custom baseline evaluated by Week 11 judge"}
    return {
        "prospect_id": snapshot.prospect.prospect_id,
        "company_name": snapshot.prospect.company_name,
        "contact_name": snapshot.prospect.contact_name,
        "scenario_name": scenario,
        "inbound_body": str(payload.get("body") or ""),
        "prospect_context": snapshot.prospect.model_dump(mode="json"),
        "hiring_signal_brief": snapshot.hiring_signal_brief.model_dump(mode="json"),
        "competitor_gap_brief": snapshot.competitor_gap_brief.model_dump(mode="json"),
        **template,
    }


@router.post("/api/simulator/compare-reply")
def simulator_compare_reply(payload: dict) -> dict:
    candidate = _comparison_baseline_candidate(payload)
    comparison = compare_candidate_action(candidate)
    return {
        **comparison,
        "judge_enabled": judge_enabled(),
        "comparison_dry_run": comparison_dry_run_enabled(),
    }


@router.get("/artifacts/{prospect_id}/{artifact_name}", response_class=PlainTextResponse)
def artifact_detail(prospect_id: str, artifact_name: str) -> PlainTextResponse:
    allowed = {
        "email": ".json",
        "sms": ".json",
        "voice": ".json",
        "hubspot": ".json",
        "langfuse": ".json",
        "calcom": ".json",
        "context_brief": ".md",
    }
    extension = allowed.get(artifact_name)
    if extension is None:
        raise HTTPException(status_code=404, detail="Artifact type not found")
    artifact_path = settings.outbox_dir / f"{prospect_id}_{artifact_name}{extension}"
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return PlainTextResponse(artifact_path.read_text(encoding="utf-8"))


def _parse_request_body(raw_body: bytes, content_type: str) -> object:
    parsed_body: object
    if "application/json" in content_type and raw_body:
        try:
            parsed_body = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            parsed_body = {"raw": raw_body.decode("utf-8", errors="replace")}
    elif "application/x-www-form-urlencoded" in content_type and raw_body:
        parsed_body = {
            key: value if len(value) > 1 else value[0]
            for key, value in parse_qs(raw_body.decode("utf-8")).items()
        }
    else:
        parsed_body = {"raw": raw_body.decode("utf-8", errors="replace")} if raw_body else {}
    return parsed_body


def _store_webhook_artifact(
    provider_key: str,
    request: Request,
    parsed_body: object,
    raw_body: bytes,
    content_type: str,
) -> tuple[str, str]:
    settings.webhook_dir.mkdir(parents=True, exist_ok=True)
    received_at = datetime.now(timezone.utc).isoformat()
    body_hash = sha256(raw_body).hexdigest()[:16] if raw_body else "empty"
    artifact_path = settings.webhook_dir / f"{provider_key}_{body_hash}.json"
    artifact_path.write_text(
        json.dumps(
            {
                "provider": provider_key,
                "received_at": received_at,
                "content_type": content_type,
                "headers": dict(request.headers.items()),
                "query_params": dict(request.query_params),
                "body": parsed_body,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    trace_id = trace_logger.log(
        "webhook_received",
        {
            "provider": provider_key,
            "artifact_ref": str(artifact_path),
            "content_type": content_type,
            "body_hash": body_hash,
        },
    )
    return str(artifact_path), trace_id


def _verify_shared_secret(request: Request, expected_secret: str, provider_label: str) -> None:
    if not expected_secret:
        return
    candidates = {
        request.headers.get("authorization", ""),
        request.headers.get("x-webhook-secret", ""),
        request.headers.get("x-cal-signature-256", ""),
    }
    if expected_secret not in candidates and f"Bearer {expected_secret}" not in candidates:
        raise HTTPException(status_code=403, detail=f"{provider_label} webhook secret validation failed")


@router.post("/webhooks/resend")
async def resend_webhook(request: Request) -> dict[str, object]:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    parsed_body = _parse_request_body(raw_body, content_type)
    artifact_ref, trace_id = _store_webhook_artifact("resend", request, parsed_body, raw_body, content_type)
    _verify_shared_secret(request, settings.resend_webhook_secret, "Resend")
    try:
        inbound = email_channel.handle_resend_reply_webhook(
            {"body": parsed_body, "headers": dict(request.headers.items())}
        )
        decision = orchestrator.handle_inbound_message(inbound)
    except EmailWebhookError as exc:
        raise HTTPException(status_code=400, detail=f"Resend reply webhook parsing failed: {exc}") from exc
    return {
        "ok": True,
        "provider": "resend",
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
        "decision": decision.model_dump(mode="json"),
    }


@router.post("/webhooks/mailersend")
async def mailersend_webhook(request: Request) -> dict[str, object]:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    parsed_body = _parse_request_body(raw_body, content_type)
    artifact_ref, trace_id = _store_webhook_artifact("mailersend", request, parsed_body, raw_body, content_type)
    try:
        inbound = email_channel.handle_mailersend_reply_webhook(
            {"body": parsed_body, "headers": dict(request.headers.items())}
        )
        decision = orchestrator.handle_inbound_message(inbound)
    except EmailWebhookError as exc:
        raise HTTPException(status_code=400, detail=f"MailerSend reply webhook parsing failed: {exc}") from exc
    return {
        "ok": True,
        "provider": "mailersend",
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
        "decision": decision.model_dump(mode="json"),
    }


@router.post("/webhooks/africastalking")
async def africastalking_webhook(request: Request) -> dict[str, object]:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    parsed_body = _parse_request_body(raw_body, content_type)
    artifact_ref, trace_id = _store_webhook_artifact(
        "africastalking",
        request,
        parsed_body,
        raw_body,
        content_type,
    )
    try:
        inbound = sms_channel.handle_africastalking_webhook(
            {"body": parsed_body, "headers": dict(request.headers.items())}
        )
        decision = orchestrator.handle_inbound_message(inbound)
    except SmsWebhookError as exc:
        raise HTTPException(status_code=400, detail=f"Africa's Talking webhook parsing failed: {exc}") from exc
    return {
        "ok": True,
        "provider": "africastalking",
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
        "decision": decision.model_dump(mode="json"),
    }


@router.post("/webhooks/voice")
async def voice_webhook(request: Request) -> dict[str, object]:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    parsed_body = _parse_request_body(raw_body, content_type)
    artifact_ref, trace_id = _store_webhook_artifact("voice", request, parsed_body, raw_body, content_type)
    _verify_shared_secret(request, settings.voice_webhook_secret, "Voice")
    try:
        inbound = voice_channel.handle_shared_voice_webhook(
            {"body": parsed_body, "headers": dict(request.headers.items())}
        )
        decision = orchestrator.handle_inbound_message(inbound)
    except VoiceWebhookError as exc:
        raise HTTPException(status_code=400, detail=f"Voice webhook parsing failed: {exc}") from exc
    return {
        "ok": True,
        "provider": "voice",
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
        "decision": decision.model_dump(mode="json"),
    }


@router.post("/webhooks/calcom")
async def calcom_webhook(request: Request) -> dict[str, object]:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    parsed_body = _parse_request_body(raw_body, content_type)
    artifact_ref, trace_id = _store_webhook_artifact("calcom", request, parsed_body, raw_body, content_type)
    _verify_shared_secret(request, settings.calcom_webhook_secret, "Cal.com")
    try:
        confirmation = calcom_client.handle_confirmation_webhook(
            {"body": parsed_body, "headers": dict(request.headers.items())}
        )
        result = orchestrator.handle_calendar_confirmation(confirmation)
    except CalComWebhookError as exc:
        raise HTTPException(status_code=400, detail=f"Cal.com confirmation parsing failed: {exc}") from exc
    return {
        "ok": True,
        "provider": "calcom",
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
        "confirmation_result": result,
    }


@router.post("/webhooks/hubspot")
async def hubspot_webhook(request: Request) -> dict[str, object]:
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    parsed_body = _parse_request_body(raw_body, content_type)
    artifact_ref, trace_id = _store_webhook_artifact("hubspot", request, parsed_body, raw_body, content_type)
    _verify_shared_secret(request, settings.hubspot_webhook_secret, "HubSpot")
    return {
        "ok": True,
        "provider": "hubspot",
        "trace_id": trace_id,
        "artifact_ref": artifact_ref,
    }


@router.post("/prospects/enrich", response_model=ProspectEnrichmentResponse)
def enrich_prospect(payload: LeadIntakeRequest) -> ProspectEnrichmentResponse:
    return orchestrator.intake_and_enrich(payload)


@router.post("/pipeline/run", response_model=ProspectEnrichmentResponse)
def run_pipeline(payload: LeadIntakeRequest) -> ProspectEnrichmentResponse:
    return orchestrator.run_toolchain(payload)


@router.post("/conversations/reply", response_model=ConversationDecision)
def handle_reply(payload: InboundMessageRequest) -> ConversationDecision:
    return orchestrator.handle_inbound_message(payload)


@router.get("/prospects/seed-companies")
def list_seed_companies(active_only: bool = True, autorefresh: bool = True) -> list[dict]:
    import json

    if active_only and autorefresh and settings.lead_auto_refresh_on_seed_query:
        if not orchestrator.list_active_prospects(limit=1):
            orchestrator.refresh_active_leads_from_sources(max_companies=150)

    snapshot_files = {
        "crunchbase": settings.crunchbase_snapshot_path,
        "job_posts": settings.job_posts_snapshot_path,
        "leadership": settings.leadership_snapshot_path,
    }
    _ = snapshot_files
    cb = json.loads(settings.crunchbase_snapshot_path.read_text()) if settings.crunchbase_snapshot_path.exists() else []
    lead = json.loads(settings.leadership_snapshot_path.read_text()) if settings.leadership_snapshot_path.exists() else []
    contacts = {l.get("domain", ""): l for l in lead if l.get("domain")}
    in_db = {p.company_domain: p for p in orchestrator.list_prospects() if p.company_domain}
    qualification_by_prospect = orchestrator.repository.qualification_map()
    active_by_domain = {
        p.company_domain: p
        for p in orchestrator.list_active_prospects(limit=500)
        if p.company_domain
    }
    result = []
    for c in cb:
        domain = c.get("domain", "")
        lc = contacts.get(domain, {})
        db_rec = active_by_domain.get(domain) if active_only else in_db.get(domain)
        q = qualification_by_prospect.get(db_rec.prospect_id, {}) if db_rec else {}
        result.append({
            "company_name": c.get("company_name", ""),
            "company_domain": domain,
            "contact_name": (db_rec.contact_name if db_rec else None) or lc.get("contact_name") or lc.get("name", ""),
            "contact_email": (db_rec.contact_email if db_rec else None) or lc.get("contact_email") or lc.get("email", ""),
            "funding_musd": c.get("funding_musd"),
            "employee_count": c.get("employee_count"),
            "sector": c.get("sector", ""),
            "in_pipeline": db_rec is not None,
            "pipeline_status": db_rec.status if db_rec else None,
            "prospect_id": db_rec.prospect_id if db_rec else None,
            "active_qualified": bool(db_rec and db_rec.status == "active_qualified_tenacious_pass"),
            "qualification_score": q.get("qualification_score"),
            "source_hit_count": q.get("source_hit_count"),
            "qualification_reason": q.get("qualification_reason"),
        })
    # Also include DB prospects whose domain isn't in snapshot
    snapshot_domains = {c.get("domain", "") for c in cb}
    loop_source = active_by_domain if active_only else in_db
    for domain, p in loop_source.items():
        if domain not in snapshot_domains:
            q = qualification_by_prospect.get(p.prospect_id, {})
            result.append({
                "company_name": p.company_name,
                "company_domain": domain,
                "contact_name": p.contact_name or "",
                "contact_email": p.contact_email or "",
                "funding_musd": None,
                "employee_count": None,
                "sector": "",
                "in_pipeline": True,
                "pipeline_status": p.status,
                "prospect_id": p.prospect_id,
                "active_qualified": p.status == "active_qualified_tenacious_pass",
                "qualification_score": q.get("qualification_score"),
                "source_hit_count": q.get("source_hit_count"),
                "qualification_reason": q.get("qualification_reason"),
            })
    if active_only:
        result = [row for row in result if row.get("active_qualified")]
    return result


@router.get("/prospects/active", response_model=list[ProspectRecord])
def list_active_prospects(limit: int = 200) -> list[ProspectRecord]:
    return orchestrator.list_active_prospects(limit=limit)


@router.post("/prospects/refresh-active")
def refresh_active_prospects(max_companies: int = 150) -> dict[str, object]:
    result = orchestrator.refresh_active_leads_from_sources(max_companies=max_companies)
    return {
        "ok": True,
        **result,
    }


@router.get("/prospects/corrections")
def list_correction_history(prospect_id: str | None = None, limit: int = 50) -> list[dict]:
    bounded_limit = max(1, min(limit, 200))
    return orchestrator.repository.list_correction_history(
        prospect_id=prospect_id,
        limit=bounded_limit,
    )


@router.get("/prospects", response_model=list[ProspectRecord])
def list_prospects() -> list[ProspectRecord]:
    return orchestrator.list_prospects()


@router.get("/prospects/{prospect_id}", response_model=ProspectEnrichmentResponse)
def get_prospect(prospect_id: str) -> ProspectEnrichmentResponse:
    snapshot = orchestrator.get_snapshot(prospect_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Prospect snapshot not found")
    return snapshot
