import json

from agent.channels.email import email_channel
from agent.channels.sms import sms_channel
from agent.channels.voice import voice_channel
from agent.config import settings
from agent.enrichment.service import enrichment_service
from agent.orchestration.service import orchestrator
from agent.schemas.prospect import InboundMessageRequest, LeadIntakeRequest


def test_layoff_plus_funding_routes_to_restructuring() -> None:
    prospect, brief, _ = enrichment_service.enrich(
        LeadIntakeRequest(
            company_name="OrbitStack Cloud",
            company_domain="orbitstack.dev",
        )
    )

    assert prospect.primary_segment == "mid_market_restructuring"
    assert brief.primary_segment == "Mid-market platforms restructuring cost"
    assert prospect.segment_confidence >= 0.8


def test_unknown_prospect_abstains() -> None:
    prospect, brief, _ = enrichment_service.enrich(
        LeadIntakeRequest(company_name="Unknown Co", company_domain="unknown.example")
    )

    assert prospect.primary_segment == "abstain"
    assert "segment-specific pitch" in " ".join(brief.do_not_claim)


def test_inbound_pricing_reply_does_not_invent_total() -> None:
    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="ClearMint",
            company_domain="clearmint.io",
            contact_name="Amara",
            contact_email="amara@clearmint.io",
        )
    )
    decision = orchestrator.handle_inbound_message(
        InboundMessageRequest(
            prospect_id=snapshot.prospect.prospect_id,
            channel="email",
            body="What would this cost for a team?",
        )
    )

    assert decision.next_action == "send_email"
    assert "specific number depends on scope" in decision.reply_draft
    assert "pricing_guardrail" in decision.risk_flags


def test_sms_handoff_requires_prior_email_reply() -> None:
    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="ClearMint",
            company_domain="clearmint.io",
            contact_name="Amara",
            contact_email="amara@clearmint.io",
            contact_phone="+254700000000",
        )
    )
    result = orchestrator.handoff_manager.prepare_warm_sms_handoff(
        snapshot,
        body="Following up with scheduling options.",
    )
    assert result.status == "skipped"
    assert "warm-lead gate" in result.message


def test_email_reply_opens_sms_handoff_gate_for_meeting_requests() -> None:
    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="ClearMint",
            company_domain="clearmint.io",
            contact_name="Amara",
            contact_email="amara@clearmint.io",
            contact_phone="+254700000000",
        )
    )
    decision = orchestrator.handle_inbound_message(
        InboundMessageRequest(
            prospect_id=snapshot.prospect.prospect_id,
            contact_email="amara@clearmint.io",
            channel="email",
            body="Can we meet next week?",
        )
    )
    assert decision.next_action == "book_meeting"
    assert orchestrator.repository.has_interaction_event(
        snapshot.prospect.prospect_id,
        "email_reply_received",
    )


def test_voice_request_prepares_voice_handoff_for_warm_lead() -> None:
    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="ClearMint",
            company_domain="clearmint.io",
            contact_name="Amara",
            contact_email="amara@clearmint.io",
            contact_phone="+254700000000",
        )
    )
    decision = orchestrator.handle_inbound_message(
        InboundMessageRequest(
            prospect_id=snapshot.prospect.prospect_id,
            contact_email="amara@clearmint.io",
            channel="email",
            body="Can we meet next week? Please call me.",
        )
    )
    assert decision.next_action == "book_meeting"
    assert orchestrator.repository.has_interaction_event(
        snapshot.prospect.prospect_id,
        "voice_handoff_sent",
    )
    payload = json.loads(
        (settings.outbox_dir / f"{snapshot.prospect.prospect_id}_voice.json").read_text()
    )
    brief_path = settings.outbox_dir / f"{snapshot.prospect.prospect_id}_context_brief.md"
    assert payload["context_brief_artifact_ref"] == str(brief_path)
    assert brief_path.exists()
    assert "## 1. Segment and confidence" in brief_path.read_text()


def test_booking_confirmation_prepares_voice_handoff() -> None:
    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="Northstar Labs Voice",
            company_domain="northstarlabs.ai",
            contact_name="Jordan",
            contact_email="jordan.voice@example.com",
            contact_phone="+254700000001",
        )
    )
    orchestrator.handle_inbound_message(
        InboundMessageRequest(
            prospect_id=snapshot.prospect.prospect_id,
            contact_email="jordan.voice@example.com",
            channel="email",
            body="Thursday works, book me in.",
        )
    )
    result = orchestrator.handle_calendar_confirmation(
        {
            "contact_email": "jordan.voice@example.com",
            "booking_external_id": "booking-voice-001",
            "booking_status": "confirmed",
            "company_name": "Northstar Labs Voice",
        }
    )
    assert result["ok"] is True
    assert orchestrator.repository.has_interaction_event(
        snapshot.prospect.prospect_id,
        "voice_handoff_sent",
    )
    brief_path = settings.outbox_dir / f"{snapshot.prospect.prospect_id}_context_brief.md"
    assert brief_path.exists()
    assert "booking-voice-001" not in brief_path.read_text()
    assert "confirmed" in brief_path.read_text().lower()


def test_handle_inbound_message_writes_reply_decision_artifact() -> None:
    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="ClearMint",
            company_domain="clearmint.io",
            contact_name="Amara",
            contact_email="amara.reply.artifact@clearmint.io",
        )
    )
    orchestrator.handle_inbound_message(
        InboundMessageRequest(
            prospect_id=snapshot.prospect.prospect_id,
            contact_email="amara.reply.artifact@clearmint.io",
            channel="email",
            body="Sounds interesting, can we set up a call?",
        )
    )

    artifact_path = settings.outbox_dir / f"{snapshot.prospect.prospect_id}_reply_decision.json"
    assert artifact_path.exists(), f"Expected reply decision artifact at {artifact_path}"

    data = json.loads(artifact_path.read_text())
    assert data["prospect_id"] == snapshot.prospect.prospect_id
    assert data["channel"] == "email"
    assert "inbound_body_preview" in data
    assert "Sounds interesting" in data["inbound_body_preview"]
    assert "decision" in data
    assert data["decision"]["next_action"] in {"send_email", "book_meeting", "handoff_human"}
    assert "reply_draft" in data["decision"]
    assert "risk_flags" in data["decision"]
    assert "needs_human" in data["decision"]
    assert "recorded_at" in data


def test_provider_webhook_parsers_build_inbound_messages() -> None:
    resend_inbound = email_channel.handle_resend_reply_webhook(
        {
            "body": {
                "data": {
                    "from": {"email": "reply@example.com"},
                    "text": "Can we book time?",
                }
            }
        }
    )
    sms_inbound = sms_channel.handle_africastalking_webhook(
        {
            "body": {
                "from": "+254700000000",
                "text": "Thursday works for me",
            }
        }
    )
    voice_inbound = voice_channel.handle_shared_voice_webhook(
        {
            "body": {
                "from": "+254700000000",
                "transcript": "Please call me tomorrow morning.",
            }
        }
    )
    assert resend_inbound.channel == "email"
    assert resend_inbound.contact_email == "reply@example.com"
    assert sms_inbound.channel == "sms"
    assert sms_inbound.contact_phone == "+254700000000"
    assert voice_inbound.channel == "voice"
    assert voice_inbound.contact_phone == "+254700000000"
