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
