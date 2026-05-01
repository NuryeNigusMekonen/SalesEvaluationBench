import json
from types import SimpleNamespace

from agent.evaluation import comparison_service


def _candidate() -> dict:
    return {
        "prospect_id": "pros_cmp_001",
        "company_name": "ClearMint",
        "contact_name": "Amina",
        "channel": "email",
        "action_type": "email_reply",
        "baseline_output": "Hi Amina, this is a grounded follow-up.",
        "prospect_context": {
            "prospect_id": "pros_cmp_001",
            "company_name": "ClearMint",
            "contact_name": "Amina",
        },
        "hiring_signal_brief": {"summary": "Grounded public hiring signal."},
        "competitor_gap_brief": {"safe_gap_framing": "Use carefully."},
        "scenario_name": "safe_followup",
    }


def _set_log(monkeypatch, tmp_path):
    log_path = tmp_path / "comparison_reviews.jsonl"
    monkeypatch.setattr(comparison_service, "COMPARISON_LOG_PATH", log_path)
    return log_path


def test_pass_baseline_remains_allowed(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    result = comparison_service.compare_candidate_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "pass",
            "reason": "Grounded in the supplied signal.",
            "confidence": 0.91,
        },
    )

    assert result["final_decision"] == "allow"
    assert result["final_output"] == result["baseline_output"]
    assert result["changed_by_week11"] is False


def test_fail_blocks_sending(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    result = comparison_service.compare_candidate_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "fail",
            "reason": "Unsupported pricing claim.",
            "confidence": 0.88,
        },
    )

    assert result["final_decision"] == "block"
    assert result["final_output"] == ""
    assert result["changed_by_week11"] is True


def test_needs_human_review_blocks_sending(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    result = comparison_service.compare_candidate_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "needs_human_review",
            "reason": "Missing consent context for SMS escalation.",
            "confidence": 0.42,
        },
    )

    assert result["final_decision"] == "human_review"
    assert result["final_output"] == ""
    assert result["changed_by_week11"] is True


def test_policy_override_blocks_calendar_sms_even_if_judge_passes(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    candidate = {
        **_candidate(),
        "action_type": "calendar_action",
        "channel": "calendar",
        "baseline_output": (
            "Hi Amina, I booked a discovery call for Tuesday and sent the "
            "calendar link by SMS so we can move quickly."
        ),
    }

    result = comparison_service.compare_candidate_action(
        candidate,
        judge_func=lambda **kwargs: {
            "verdict": "pass",
            "reason": "Model thought this was acceptable.",
            "confidence": 0.77,
        },
    )

    assert result["judge_verdict"] == "fail"
    assert result["final_decision"] == "block"
    assert result["final_output"] == ""
    assert "commits a meeting or slot" in result["judge_reason"]


def test_policy_override_blocks_generic_capacity_overclaim(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    candidate = {
        **_candidate(),
        "baseline_output": (
            "Hi Amina, Tenacious has world-class top talent and 60 engineers ready "
            "to deploy in 7-14 days for any stack you need."
        ),
    }

    result = comparison_service.compare_candidate_action(
        candidate,
        judge_func=lambda **kwargs: {
            "verdict": "pass",
            "reason": "Model thought this was acceptable.",
            "confidence": 0.77,
        },
    )

    assert result["judge_verdict"] == "fail"
    assert result["final_decision"] == "block"
    assert result["final_output"] == ""
    assert "unsupported all-stack" in result["judge_reason"]


def test_policy_override_replaces_model_fail_reason(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    candidate = {
        **_candidate(),
        "baseline_output": (
            "Hi Amina, Tenacious has world-class top talent and 60 engineers ready "
            "to deploy in 7-14 days for any stack you need."
        ),
    }

    result = comparison_service.compare_candidate_action(
        candidate,
        judge_func=lambda **kwargs: {
            "verdict": "fail",
            "reason": "The verified bench facts indicate 60 engineers, so this is inconsistent.",
            "confidence": 0.77,
        },
    )

    assert result["judge_verdict"] == "fail"
    assert result["final_decision"] == "block"
    assert result["judge_reason"] == (
        "Generic vendor language and unsupported all-stack or bench-capacity framing."
    )


def test_policy_override_blocks_known_failure_even_when_model_uncertain(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    candidate = {
        **_candidate(),
        "baseline_output": (
            "Hi Amina, the full build will be $48,000 fixed, and I can apply a "
            "20% discount if you book this week."
        ),
    }

    result = comparison_service.compare_candidate_action(
        candidate,
        judge_func=lambda **kwargs: {
            "verdict": "needs_human_review",
            "reason": "Local judge adapter unavailable or invalid output.",
            "confidence": 0.0,
        },
    )

    assert result["judge_verdict"] == "fail"
    assert result["final_decision"] == "block"
    assert result["judge_reason"] == "Unsupported pricing, discount, or savings claim."


def test_sms_opt_in_reason_focuses_on_unconfirmed_slot(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    candidate = {
        **_candidate(),
        "action_type": "sms",
        "channel": "sms",
        "inbound_body": "Can you text me the booking details?",
        "baseline_output": (
            "Hi Amina, here is your booking link by SMS. I also held a slot for "
            "you with our delivery lead."
        ),
    }

    result = comparison_service.compare_candidate_action(
        candidate,
        judge_func=lambda **kwargs: {
            "verdict": "fail",
            "reason": "SMS escalation without consent or warm-lead gating is not allowed.",
            "confidence": 0.77,
        },
    )

    assert result["judge_verdict"] == "fail"
    assert result["final_decision"] == "block"
    assert "SMS opt-in is present" in result["judge_reason"]
    assert "without consent" not in result["judge_reason"]


def test_comparison_record_is_written(monkeypatch, tmp_path) -> None:
    log_path = _set_log(monkeypatch, tmp_path)
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    comparison_service.compare_candidate_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "fail",
            "reason": "Unsupported claim.",
            "confidence": 0.8,
        },
    )

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["prospect_id"] == "pros_cmp_001"
    assert records[0]["company_name"] == "ClearMint"
    assert records[0]["final_decision"] == "block"


def test_disabled_comparison_preserves_old_behavior(monkeypatch, tmp_path) -> None:
    _set_log(monkeypatch, tmp_path)
    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)
    monkeypatch.delenv("TENACIOUS_COMPARISON_MODE", raising=False)

    result = comparison_service.compare_candidate_action(_candidate())

    assert comparison_service.comparison_mode_enabled() is False
    assert result["final_decision"] == "allow"
    assert result["final_output"] == result["baseline_output"]
    assert result["changed_by_week11"] is False
    assert result["judge_reason"] == "judge disabled"


def test_dry_run_does_not_call_email_sms_crm_or_calendar_transports(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TENACIOUS_COMPARISON_MODE", "true")
    monkeypatch.setenv("TENACIOUS_COMPARISON_DRY_RUN", "true")
    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)

    from agent.channels import email as email_mod
    from agent.channels import sms as sms_mod
    from agent.crm import hubspot as hubspot_mod
    from agent.scheduling import calcom as calcom_mod

    def fail_transport(*args, **kwargs):  # pragma: no cover - should never run
        raise AssertionError("external transport should not be called during comparison dry-run")

    monkeypatch.setattr(email_mod, "request_json", fail_transport)
    monkeypatch.setattr(sms_mod, "request_form", fail_transport)
    monkeypatch.setattr(hubspot_mod, "request_json", fail_transport)

    email_settings = SimpleNamespace(
        email_provider="resend",
        outbound_enabled=True,
        resend_api_key="key",
        resend_from_email="sales@example.com",
        resend_reply_to="",
        mailersend_api_key="",
        mailersend_from_email="sales@example.com",
        mailersend_from_name="Tenacious",
        outbox_dir=tmp_path,
    )
    sms_settings = SimpleNamespace(
        sms_provider="africastalking",
        outbound_enabled=True,
        africas_talking_username="user",
        africas_talking_api_key="key",
        africas_talking_sender_id="TENACIOUS",
        africas_talking_env="production",
        outbox_dir=tmp_path,
    )
    hubspot_settings = SimpleNamespace(
        outbound_enabled=True,
        hubspot_access_token="token",
        hubspot_base_url="https://api.hubapi.com",
        outbox_dir=tmp_path,
    )
    calcom_settings = SimpleNamespace(
        calcom_api_key="key",
        calcom_event_type_id="evt",
        calcom_username="tenacious",
        calcom_event_type_slug="discovery-call",
        outbox_dir=tmp_path,
    )
    monkeypatch.setattr(email_mod, "settings", email_settings)
    monkeypatch.setattr(sms_mod, "settings", sms_settings)
    monkeypatch.setattr(hubspot_mod, "settings", hubspot_settings)
    monkeypatch.setattr(calcom_mod, "settings", calcom_settings)

    email_result = email_mod.email_channel.send(
        recipient="amina@example.com",
        subject="Hello",
        body="Allowed email",
        prospect_id="pros_dry_001",
    )
    sms_result = sms_mod.sms_channel.send(
        phone_number="+254700000000",
        body="Allowed SMS",
        prospect_id="pros_dry_001",
        allow_warm_lead=True,
    )
    crm_result = hubspot_mod.hubspot_client.sync_contact_profile(
        {"email": "amina@example.com", "company_name": "ClearMint"},
        "pros_dry_001",
    )
    calendar_result = calcom_mod.calcom_client.book_preview(
        company_name="ClearMint",
        contact_email="amina@example.com",
        prospect_id="pros_dry_001",
    )

    assert email_result.status == "previewed"
    assert "Would send" in email_result.message
    assert sms_result.status == "previewed"
    assert "Would send" in sms_result.message
    assert crm_result.status == "previewed"
    assert "Would commit" in crm_result.message
    assert calendar_result.status == "previewed"
    assert "comparison dry-run" in calendar_result.message
