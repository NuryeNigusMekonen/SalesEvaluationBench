import json

from agent.evaluation import tenacious_judge_adapter as judge_adapter


def _candidate() -> dict:
    return {
        "prospect_id": "pros_judge_001",
        "channel": "email",
        "action_type": "email",
        "prospect_context": {
            "prospect_id": "pros_judge_001",
            "company_name": "ClearMint",
        },
        "hiring_signal_brief": {"summary": "Hiring signal is source-backed."},
        "competitor_gap_brief": {"safe_gap_framing": "Use the gap carefully."},
        "agent_output": "Hi Amara, I noticed the public engineering hiring signal.",
    }


def test_judge_disabled_allows_action(monkeypatch) -> None:
    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)

    result = judge_adapter.review_before_action(_candidate())

    assert result["allow"] is True
    assert result["route_to_review"] is False
    assert result["reason"] == "judge disabled"


def test_pass_verdict_allows_action(monkeypatch) -> None:
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    result = judge_adapter.review_before_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "pass",
            "reason": "Grounded in the supplied hiring signal.",
            "confidence": 0.91,
            "model_path": "local-adapter",
            "mode": "model",
        },
    )

    assert result["allow"] is True
    assert result["route_to_review"] is False


def test_fail_verdict_blocks_action(monkeypatch) -> None:
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    result = judge_adapter.review_before_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "fail",
            "reason": "Candidate overclaims an unverified funding signal.",
            "confidence": 0.88,
            "model_path": "local-adapter",
            "mode": "model",
        },
    )

    assert result["allow"] is False
    assert result["route_to_review"] is False
    assert "overclaims" in result["reason"]


def test_needs_human_review_blocks_and_routes(monkeypatch) -> None:
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    result = judge_adapter.review_before_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "needs_human_review",
            "reason": "Missing consent context for SMS escalation.",
            "confidence": 0.42,
            "model_path": "local-adapter",
            "mode": "model",
        },
    )

    assert result["allow"] is False
    assert result["route_to_review"] is True


def test_missing_adapter_returns_needs_human_review(tmp_path) -> None:
    result = judge_adapter.judge_candidate(
        prospect_context={},
        hiring_signal_brief={},
        competitor_gap_brief={},
        agent_output="Candidate output",
        adapter_path=str(tmp_path / "missing-adapter"),
    )

    assert result["verdict"] == "needs_human_review"
    assert result["mode"] == "fallback"
    assert result["confidence"] == 0.0


def test_runtime_status_reports_env_path_deps_and_last_error(monkeypatch, tmp_path) -> None:
    adapter_path = tmp_path / "adapter"
    adapter_path.mkdir()
    log_path = tmp_path / "judge_reviews.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "timestamp_utc": "2026-04-30T12:00:00+00:00",
                "reason": "Judge ML dependencies are unavailable.",
                "mode": "fallback",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    monkeypatch.setenv("TENACIOUS_COMPARISON_MODE", "true")
    monkeypatch.setenv("TENACIOUS_COMPARISON_DRY_RUN", "false")
    monkeypatch.setenv("TENACIOUS_JUDGE_ADAPTER_PATH", str(adapter_path))
    monkeypatch.setattr(judge_adapter, "REVIEW_LOG_PATH", log_path)
    monkeypatch.setattr(
        judge_adapter,
        "_dependency_available",
        lambda name: name in {"torch", "transformers", "peft", "unsloth"},
    )

    status = judge_adapter.runtime_status()

    assert status["tenacious_judge_enabled"] is True
    assert status["tenacious_comparison_mode"] is True
    assert status["tenacious_comparison_dry_run"] is False
    assert status["adapter_path"] == str(adapter_path)
    assert status["adapter_path_exists"] is True
    assert status["required_ml_deps_available"]["torch"] is True
    assert status["required_ml_deps_available"]["unsloth"] is True
    assert status["runtime_mode"] == "real_model"
    assert "Judge ML dependencies are unavailable" in status["last_judge_error"]


def test_runtime_status_defaults_comparison_dry_run_to_true(monkeypatch) -> None:
    monkeypatch.delenv("TENACIOUS_COMPARISON_DRY_RUN", raising=False)

    status = judge_adapter.runtime_status()

    assert status["tenacious_comparison_dry_run"] is True


def test_invalid_json_model_output_returns_needs_human_review(monkeypatch, tmp_path) -> None:
    adapter_path = tmp_path / "adapter"
    adapter_path.mkdir()
    monkeypatch.setattr(
        judge_adapter,
        "_generate_judge_output",
        lambda prompt, *, adapter_path, base_model: "I think this is fine, but no JSON.",
    )

    result = judge_adapter.judge_candidate(
        prospect_context={},
        hiring_signal_brief={},
        competitor_gap_brief={},
        agent_output="Candidate output",
        adapter_path=str(adapter_path),
    )

    assert result["verdict"] == "needs_human_review"
    assert result["mode"] == "fallback"
    assert result["raw_output"] == "I think this is fine, but no JSON."


def test_runtime_status_warns_when_outbound_live_judge_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OUTBOUND_ENABLED", "true")
    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)

    status = judge_adapter.runtime_status()

    assert status["outbound_is_live"] is True
    assert status["judge_disabled_with_live_outbound_warning"] is True
    assert status["judge_disabled_warning"] is not None
    assert "Week 11 judge is disabled" in status["judge_disabled_warning"]
    assert "guardrail" in status["judge_disabled_warning"]


def test_runtime_status_no_warning_when_judge_enabled(monkeypatch) -> None:
    monkeypatch.setenv("OUTBOUND_ENABLED", "true")
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")

    status = judge_adapter.runtime_status()

    assert status["outbound_is_live"] is True
    assert status["judge_disabled_with_live_outbound_warning"] is False
    assert status["judge_disabled_warning"] is None


def test_runtime_status_no_warning_when_outbound_disabled(monkeypatch) -> None:
    monkeypatch.delenv("OUTBOUND_ENABLED", raising=False)
    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)

    status = judge_adapter.runtime_status()

    assert status["outbound_is_live"] is False
    assert status["judge_disabled_with_live_outbound_warning"] is False
    assert status["judge_disabled_warning"] is None


def test_judge_review_log_writes_one_jsonl_record(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    log_path = tmp_path / "judge_reviews.jsonl"
    monkeypatch.setattr(judge_adapter, "REVIEW_LOG_PATH", log_path)

    judge_adapter.review_before_action(
        _candidate(),
        judge_func=lambda **kwargs: {
            "verdict": "fail",
            "reason": "Unsupported claim.",
            "risk_focus": "overclaimed_signal_or_maturity_claim",
            "confidence": 0.77,
            "model_path": "local-adapter",
            "mode": "model",
        },
    )

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["prospect_id"] == "pros_judge_001"
    assert record["company_name"] == "ClearMint"
    assert record["verdict"] == "fail"
    assert record["risk_focus"] == "overclaimed_signal_or_maturity_claim"
