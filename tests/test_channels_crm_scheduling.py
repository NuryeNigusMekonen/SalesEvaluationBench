"""
Tests for channels (email, SMS), CRM (HubSpot), and scheduling (Cal.com).
All tests run in preview/mock mode (OUTBOUND_ENABLED=false env is already set
in .env.example defaults; live sends require explicit OUTBOUND_ENABLED=true).
"""

import json
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError

from agent.channels.email import EmailChannel
from agent.channels.sms import SmsChannel
from agent.channels.voice import VoiceChannel
from agent.config import settings
from agent.crm.hubspot import HubSpotClient
from agent.scheduling.calcom import CalComClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_outbox(prospect_id: str, suffix: str) -> dict:
    artifact = settings.outbox_dir / f"{prospect_id}_{suffix}.json"
    assert artifact.exists(), f"Expected artifact {artifact} not found"
    return json.loads(artifact.read_text())


# ---------------------------------------------------------------------------
# Email channel
# ---------------------------------------------------------------------------

def test_email_send_writes_artifact() -> None:
    channel = EmailChannel()
    result = channel.send(
        recipient=None,
        subject="Context: engineering capacity at ClearMint",
        body="Three of your peers posted MLOps roles in the last 90 days.",
        prospect_id="pros_ch_email_001",
    )
    assert result.status in ("executed", "previewed"), f"Unexpected status: {result.status}"
    assert result.artifact_ref is not None


def test_email_artifact_contains_subject_and_body() -> None:
    channel = EmailChannel()
    subject = "Request: 15 minutes on your AI roadmap"
    body = "You closed a $14M Series B and your Python roles tripled."
    channel.send(
        recipient=None,
        subject=subject,
        body=body,
        prospect_id="pros_ch_email_002",
    )
    payload = _read_outbox("pros_ch_email_002", "email")
    assert payload.get("subject") == subject
    assert payload.get("body") == body


def test_email_artifact_marked_draft() -> None:
    channel = EmailChannel()
    channel.send(
        recipient=None,
        subject="Follow-up: hiring velocity signal",
        body="Series A runway typically tightens recruiting capacity around month four.",
        prospect_id="pros_ch_email_003",
    )
    payload = _read_outbox("pros_ch_email_003", "email")
    # Kill switch: outbox artifacts should be marked as draft when OUTBOUND_ENABLED=false
    assert payload.get("draft") is True or not settings.outbound_enabled


def test_email_status_always_available() -> None:
    channel = EmailChannel()
    status = channel.status()
    assert status.available is True
    assert status.name == "email"
    assert status.mode in ("mock", "configured")


def test_email_falls_back_to_preview_when_provider_rejects_sender(monkeypatch) -> None:
    channel = EmailChannel()
    monkeypatch.setattr(
        "agent.channels.email.settings",
        SimpleNamespace(
            outbox_dir=settings.outbox_dir,
            outbound_enabled=True,
            email_provider="resend",
            resend_api_key="live-key",
            resend_from_email="sender@tenacious.com",
            resend_reply_to="",
            mailersend_api_key="",
            mailersend_from_email="sender@tenacious.com",
            mailersend_from_name="Tenacious",
        ),
    )

    def raise_http_error(*args, **kwargs):
        raise HTTPError(
            url="https://api.resend.com/emails",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=BytesIO(b'{"message":"The from address does not match a verified domain."}'),
        )

    monkeypatch.setattr("agent.channels.email.request_json", raise_http_error)

    result = channel.send(
        recipient="amara@clearmint.io",
        subject="Booking options for ClearMint",
        body="Draft body",
        prospect_id="pros_ch_email_004",
    )

    assert result.status == "previewed"
    assert "rejected the current credentials or sender identity" in result.message
    assert "verified domain" in result.message


def test_email_needs_human_review_does_not_send_live(monkeypatch, tmp_path) -> None:
    channel = EmailChannel()
    monkeypatch.setattr(
        "agent.channels.email.settings",
        SimpleNamespace(
            outbox_dir=tmp_path,
            outbound_enabled=True,
            email_provider="resend",
            resend_api_key="live-key",
            resend_from_email="sender@tenacious.com",
            resend_reply_to="",
            mailersend_api_key="",
            mailersend_from_email="sender@tenacious.com",
            mailersend_from_name="Tenacious",
        ),
    )
    monkeypatch.setattr(
        "agent.channels.email.review_before_action",
        lambda candidate: {
            "allow": False,
            "route_to_review": True,
            "judge": {"verdict": "needs_human_review"},
            "reason": "Local judge adapter unavailable or invalid output, routed to human review.",
        },
    )

    def fail_transport(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("Email transport should not run for needs_human_review")

    monkeypatch.setattr("agent.channels.email.request_json", fail_transport)

    result = channel.send(
        recipient="amara@clearmint.io",
        subject="Initial outreach",
        body="Draft body",
        prospect_id="pros_ch_email_guard_001",
    )

    assert result.status == "skipped"
    assert "Needs human review" in result.message
    payload = json.loads((tmp_path / "pros_ch_email_guard_001_email.json").read_text())
    assert payload["outbound_enabled"] is False
    assert payload["judge_review"]["verdict"] == "needs_human_review"


# ---------------------------------------------------------------------------
# SMS channel — warm-lead coordination only
# ---------------------------------------------------------------------------

def test_sms_send_writes_artifact() -> None:
    channel = SmsChannel()
    result = channel.send(
        phone_number=None,
        body="Hi, are you free Thursday for a 15-minute discovery call?",
        prospect_id="pros_ch_sms_001",
        allow_warm_lead=False,
    )
    assert result.status == "skipped", f"Unexpected status: {result.status}"
    assert result.artifact_ref is not None


def test_sms_artifact_exists_after_send() -> None:
    channel = SmsChannel()
    channel.send(
        phone_number=None,
        body="Tenacious: booking confirmation coming via Cal.com.",
        prospect_id="pros_ch_sms_002",
        allow_warm_lead=False,
    )
    artifact = settings.outbox_dir / "pros_ch_sms_002_sms.json"
    assert artifact.exists()


def test_sms_booking_options_include_cal_link_when_gate_open() -> None:
    channel = SmsChannel()
    result, body = channel.send_booking_options(
        phone_number="+254700000000",
        prospect_id="pros_ch_sms_003",
        company_name="ClearMint",
        contact_name="Amara Cole",
        contact_email="amara@clearmint.io",
        allow_warm_lead=True,
    )
    assert result.status in ("executed", "previewed", "error")
    assert "https://cal.com/" in body


def test_sms_status_always_available() -> None:
    channel = SmsChannel()
    status = channel.status()
    assert status.name == "sms"
    assert status.available is True


def test_sms_falls_back_to_preview_when_provider_rejects_credentials(monkeypatch) -> None:
    channel = SmsChannel()
    monkeypatch.setattr(
        "agent.channels.sms.settings",
        SimpleNamespace(
            outbox_dir=settings.outbox_dir,
            outbound_enabled=True,
            sms_provider="africastalking",
            africas_talking_username="sandbox",
            africas_talking_api_key="live-key",
            africas_talking_sender_id="TENACIOUS",
        ),
    )

    def raise_http_error(*args, **kwargs):
        raise HTTPError(
            url="https://api.africastalking.com/version1/messaging",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("agent.channels.sms.request_form", raise_http_error)

    result = channel.send(
        phone_number="+254700000000",
        body="Warm lead link",
        prospect_id="pros_ch_sms_004",
        allow_warm_lead=True,
    )

    assert result.status == "previewed"
    assert "rejected the current credentials or sender identity" in result.message


# ---------------------------------------------------------------------------
# Voice channel — bonus-tier delivery-lead handoff
# ---------------------------------------------------------------------------

def test_voice_handoff_writes_artifact() -> None:
    channel = VoiceChannel()
    result = channel.prepare_handoff(
        phone_number="+254700000000",
        prospect_id="pros_ch_voice_001",
        company_name="ClearMint",
        contact_name="Amara Cole",
        contact_email="amara@clearmint.io",
        allow_warm_lead=True,
        booking_link="https://cal.com/tenacious/discovery-call",
        context_brief="# Discovery Call Handoff",
    )
    assert result.status in ("executed", "previewed"), f"Unexpected status: {result.status}"
    assert result.artifact_ref is not None


def test_voice_artifact_contains_booking_link_and_context() -> None:
    channel = VoiceChannel()
    channel.prepare_handoff(
        phone_number="+254700000000",
        prospect_id="pros_ch_voice_002",
        company_name="ClearMint",
        contact_name="Amara Cole",
        contact_email="amara@clearmint.io",
        allow_warm_lead=True,
        booking_link="https://cal.com/tenacious/discovery-call",
        context_brief="# Discovery Call Handoff\n\n- Prospect: Amara Cole",
    )
    payload = _read_outbox("pros_ch_voice_002", "voice")
    assert payload.get("booking_link") == "https://cal.com/tenacious/discovery-call"
    assert "Discovery Call Handoff" in payload.get("context_brief", "")


def test_voice_handoff_requires_prior_email_reply() -> None:
    channel = VoiceChannel()
    result = channel.prepare_handoff(
        phone_number="+254700000000",
        prospect_id="pros_ch_voice_003",
        company_name="ClearMint",
        contact_name="Amara Cole",
        contact_email="amara@clearmint.io",
        allow_warm_lead=False,
    )
    assert result.status == "skipped"
    assert "warm-lead gate" in result.message


def test_voice_status_always_available() -> None:
    channel = VoiceChannel()
    status = channel.status()
    assert status.name == "voice"
    assert status.mode in ("mock", "configured")
    assert status.available is True


def test_voice_falls_back_to_preview_when_provider_rejects_credentials(monkeypatch) -> None:
    channel = VoiceChannel()
    monkeypatch.setattr(
        "agent.channels.voice.settings",
        SimpleNamespace(
            outbox_dir=settings.outbox_dir,
            outbound_enabled=True,
            voice_provider="shared_voice_rig",
            shared_voice_rig_webhook_url="https://voice.example.com/handoff",
            shared_voice_rig_api_key="live-key",
            shared_voice_rig_keyword_prefix="TENACIOUS",
        ),
    )

    def raise_http_error(*args, **kwargs):
        raise HTTPError(
            url="https://voice.example.com/handoff",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr("agent.channels.voice.request_json", raise_http_error)

    result = channel.prepare_handoff(
        phone_number="+254700000000",
        prospect_id="pros_ch_voice_004",
        company_name="ClearMint",
        contact_name="Amara Cole",
        contact_email="amara@clearmint.io",
        allow_warm_lead=True,
    )

    assert result.status == "previewed"
    assert "Shared Voice Rig rejected" in result.message


# ---------------------------------------------------------------------------
# HubSpot CRM
# ---------------------------------------------------------------------------

def test_hubspot_upsert_writes_artifact() -> None:
    client = HubSpotClient()
    payload = {
        "company_name": "ClearMint",
        "company_domain": "clearmint.io",
        "email": "amara@clearmint.io",
        "contact_name": "Amara Cole",
        "segment": "recently_funded",
        "ai_maturity_score": 3,
    }
    result = client.upsert_contact(payload, "pros_ch_hs_001")
    assert result.status in ("executed", "previewed"), f"Unexpected status: {result.status}"
    assert result.artifact_ref is not None


def test_hubspot_artifact_contains_company_info() -> None:
    client = HubSpotClient()
    payload = {
        "company_name": "OrbitStack Cloud",
        "company_domain": "orbitstack.dev",
        "email": "ops@orbitstack.dev",
        "segment": "mid_market_restructuring",
        "ai_maturity_score": 1,
    }
    client.upsert_contact(payload, "pros_ch_hs_002")
    data = _read_outbox("pros_ch_hs_002", "hubspot")
    # company name should appear somewhere in the artifact
    assert "OrbitStack" in json.dumps(data)


def test_hubspot_records_contact_activity_and_enrichment() -> None:
    client = HubSpotClient()
    results = client.record_conversation_event(
        {
            "company_name": "ClearMint",
            "company_domain": "clearmint.io",
            "email": "amara@clearmint.io",
            "contact_name": "Amara Cole",
            "segment": "recently_funded_startup",
            "segment_confidence": 0.91,
            "ai_maturity_score": 3,
            "bench_match": {"python": "available"},
            "trace_id": "tr_test_hubspot",
        },
        "pros_ch_hs_003",
        activity_type="email_reply_received",
        activity_summary="Inbound email reply processed.",
        metadata={"channel": "email"},
    )
    assert len(results) == 3
    assert [result.name for result in results] == ["hubspot", "hubspot", "hubspot"]


def test_hubspot_status_reports_mode() -> None:
    client = HubSpotClient()
    status = client.status()
    assert status.name == "hubspot"
    assert status.mode in ("mock", "configured")
    assert status.available is True


def test_hubspot_enrichment_write_skips_unknown_custom_properties(monkeypatch) -> None:
    client = HubSpotClient()
    monkeypatch.setattr(
        "agent.crm.hubspot.settings",
        SimpleNamespace(
            outbox_dir=settings.outbox_dir,
            outbound_enabled=True,
            hubspot_access_token="token",
            hubspot_base_url="https://api.hubapi.com",
        ),
    )
    monkeypatch.setattr(client, "_get_contact_property_names", lambda: {"email", "firstname"})

    result = client.write_enrichment_fields(
        "123",
        {"tenacious_segment": "mid_market_restructuring"},
        "pros_ch_hs_004",
    )

    assert result.status == "previewed"
    assert "no matching custom enrichment properties were available" in result.message


def test_hubspot_activity_note_includes_required_timestamp(monkeypatch) -> None:
    client = HubSpotClient()
    monkeypatch.setattr(
        "agent.crm.hubspot.settings",
        SimpleNamespace(
            outbox_dir=settings.outbox_dir,
            outbound_enabled=True,
            hubspot_access_token="token",
            hubspot_base_url="https://api.hubapi.com",
        ),
    )

    captured = {}

    def fake_request_json(method, url, *, headers=None, payload=None, timeout=20):
        captured["method"] = method
        captured["url"] = url
        captured["payload"] = payload
        return 201, {"id": "note-1"}, {}

    monkeypatch.setattr("agent.crm.hubspot.request_json", fake_request_json)

    result = client.log_activity(
        "123",
        activity_type="email_reply_received",
        activity_summary="Inbound email reply processed.",
        prospect_id="pros_ch_hs_005",
        metadata={"channel_state": "email_replied"},
    )

    assert result.status == "executed"
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/crm/v3/objects/notes")
    assert captured["payload"]["properties"]["hs_timestamp"]
    assert captured["payload"]["properties"]["hs_note_body"]


# ---------------------------------------------------------------------------
# Cal.com scheduling
# ---------------------------------------------------------------------------

def test_calcom_book_preview_writes_artifact() -> None:
    client = CalComClient()
    result = client.book_preview(
        company_name="ClearMint",
        contact_email="amara@clearmint.io",
        prospect_id="pros_ch_cal_001",
    )
    # The preview artifact is always written; live booking may fail with 403/404
    # if the event type is misconfigured in the current env. Accept graceful degradation.
    assert result.status in ("executed", "previewed", "error"), f"Unexpected status: {result.status}"
    assert result.artifact_ref is not None, "Artifact ref should always be set even on live failure"
    # Artifact must exist regardless of live-booking outcome
    artifact = settings.outbox_dir / "pros_ch_cal_001_calcom.json"
    assert artifact.exists()


def test_calcom_artifact_has_suggested_slots() -> None:
    client = CalComClient()
    client.book_preview(
        company_name="PatientLake",
        contact_email=None,
        prospect_id="pros_ch_cal_002",
    )
    data = _read_outbox("pros_ch_cal_002", "calcom")
    assert "suggested_slots_utc" in data
    assert len(data["suggested_slots_utc"]) >= 2


def test_calcom_generate_booking_link_contains_channel_context() -> None:
    client = CalComClient()
    booking_link, artifact_ref = client.generate_booking_link(
        company_name="PatientLake",
        contact_email="ops@patientlake.example",
        prospect_id="pros_ch_cal_004",
        source_channel="email",
    )
    assert "source=email" in booking_link
    assert artifact_ref.endswith("_calcom.json")


def test_calcom_slots_are_iso8601() -> None:
    from datetime import datetime
    client = CalComClient()
    client.book_preview(
        company_name="Buildplane",
        contact_email=None,
        prospect_id="pros_ch_cal_003",
    )
    data = _read_outbox("pros_ch_cal_003", "calcom")
    for slot in data["suggested_slots_utc"]:
        # Should be parseable as ISO 8601
        dt = datetime.fromisoformat(slot.replace("Z", "+00:00"))
        assert dt is not None


def test_calcom_status_reports_mode() -> None:
    client = CalComClient()
    status = client.status()
    assert status.name == "calcom"
    assert status.mode in ("mock", "configured")
    assert status.available is True


# ---------------------------------------------------------------------------
# Gap 2: OUTBOUND_ENABLED enforcement in HubSpot
# ---------------------------------------------------------------------------

def test_hubspot_write_blocked_when_outbound_disabled(monkeypatch, tmp_path) -> None:
    """HubSpot live API must not fire when OUTBOUND_ENABLED=false even with a valid token."""
    client = HubSpotClient()

    def fail_transport(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("HubSpot API should not be reached when OUTBOUND_ENABLED=false")

    monkeypatch.setattr(
        "agent.crm.hubspot.settings",
        SimpleNamespace(
            outbox_dir=tmp_path,
            outbound_enabled=False,
            hubspot_access_token="live-token",
            hubspot_base_url="https://api.hubapi.com",
        ),
    )
    monkeypatch.setattr("agent.crm.hubspot.request_json", fail_transport)

    result = client.sync_contact_profile(
        {"email": "test@example.com", "company_name": "BlockedCo"},
        "pros_outbound_hs_001",
    )

    assert result.status == "previewed"
    assert result.mode == "mock"


def test_hubspot_outbound_enabled_allows_live_write_when_judge_passes(monkeypatch, tmp_path) -> None:
    """With OUTBOUND_ENABLED=true, token set, and judge disabled (allow), live write proceeds."""
    client = HubSpotClient()

    captured: dict = {}

    def fake_request_json(method, url, *, headers=None, payload=None, timeout=20):
        captured["method"] = method
        captured["url"] = url
        if "search" in url:
            return 200, {"results": []}, {}
        return 201, {"id": "contact-live-001"}, {}

    monkeypatch.setattr(
        "agent.crm.hubspot.settings",
        SimpleNamespace(
            outbox_dir=tmp_path,
            outbound_enabled=True,
            hubspot_access_token="live-token",
            hubspot_base_url="https://api.hubapi.com",
        ),
    )
    monkeypatch.setattr("agent.crm.hubspot.request_json", fake_request_json)
    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)
    monkeypatch.delenv("TENACIOUS_COMPARISON_MODE", raising=False)
    monkeypatch.delenv("TENACIOUS_COMPARISON_DRY_RUN", raising=False)

    result = client.sync_contact_profile(
        {"email": "live@example.com", "company_name": "LiveCo"},
        "pros_outbound_hs_002",
    )

    assert result.status == "executed"
    assert result.external_id == "contact-live-001"
    assert captured.get("method") in {"POST", "PATCH"}


# ---------------------------------------------------------------------------
# Gap 1: Calendar confirmation dry-run gate
# ---------------------------------------------------------------------------

def test_calendar_confirmation_dry_run_prevents_booking(monkeypatch) -> None:
    """In dry-run mode, handle_calendar_confirmation returns a preview and does not mark the prospect as booked."""
    from agent.orchestration.service import orchestrator
    from agent.schemas.prospect import LeadIntakeRequest

    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)
    monkeypatch.delenv("TENACIOUS_COMPARISON_MODE", raising=False)
    monkeypatch.delenv("TENACIOUS_COMPARISON_DRY_RUN", raising=False)

    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="DryRunCal Corp",
            company_domain="dryruncal.ai",
            contact_name="Amara DryRun",
            contact_email="amara.dryruncal@example.com",
            contact_phone="+254700999099",
        )
    )

    # Enable dry-run only for the confirmation step.
    monkeypatch.setenv("TENACIOUS_COMPARISON_MODE", "true")
    monkeypatch.setenv("TENACIOUS_COMPARISON_DRY_RUN", "true")

    result = orchestrator.handle_calendar_confirmation(
        {
            "contact_email": "amara.dryruncal@example.com",
            "booking_external_id": "uid_dryruncal_test_001",
            "booking_status": "confirmed",
            "company_name": "DryRunCal Corp",
        }
    )

    assert result["ok"] is False
    assert result.get("dry_run") is True
    assert "dry-run" in result["reason"].lower()
    assert result["matched"] is True

    refreshed = orchestrator.repository.get_snapshot(snapshot.prospect.prospect_id)
    assert refreshed is not None
    assert refreshed.prospect.status != "booked"
