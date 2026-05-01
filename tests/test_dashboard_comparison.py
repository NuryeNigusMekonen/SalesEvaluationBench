from fastapi.testclient import TestClient

from agent.main import app
from agent.orchestration.service import orchestrator
from agent.schemas.prospect import LeadIntakeRequest


def test_dashboard_contains_week11_comparison_toggle() -> None:
    client = TestClient(app)
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Week 11 Judge Comparison" in response.text
    assert "Show baseline vs judge-reviewed output" in response.text
    assert "Week 11 Judge Runtime" in response.text
    assert "Week 11 Initial Outreach Review" in response.text
    assert "TENACIOUS_JUDGE_ENABLED" in response.text
    assert "required ML deps available" in response.text


def test_dashboard_state_exposes_week11_judge_runtime_status(monkeypatch, tmp_path) -> None:
    adapter_path = tmp_path / "adapter"
    adapter_path.mkdir()
    monkeypatch.setenv("TENACIOUS_JUDGE_ENABLED", "true")
    monkeypatch.setenv("TENACIOUS_COMPARISON_MODE", "true")
    monkeypatch.setenv("TENACIOUS_COMPARISON_DRY_RUN", "true")
    monkeypatch.setenv("TENACIOUS_JUDGE_ADAPTER_PATH", str(adapter_path))

    client = TestClient(app)
    response = client.get("/dashboard/state")

    assert response.status_code == 200
    runtime = response.json()["tenacious_judge_runtime"]
    assert runtime["tenacious_judge_enabled"] is True
    assert runtime["tenacious_comparison_mode"] is True
    assert runtime["tenacious_comparison_dry_run"] is True
    assert runtime["adapter_path"] == str(adapter_path)
    assert runtime["adapter_path_exists"] is True
    assert set(runtime["required_ml_deps_available"]) == {
        "torch",
        "transformers",
        "peft",
        "unsloth",
    }
    assert runtime["runtime_mode"] in {"real_model", "openrouter_fallback", "fallback"}


def test_simulator_compare_reply_endpoint_returns_comparison(monkeypatch) -> None:
    monkeypatch.delenv("TENACIOUS_JUDGE_ENABLED", raising=False)
    snapshot = orchestrator.run_toolchain(
        LeadIntakeRequest(
            company_name="Comparison Dashboard Labs",
            company_domain="comparison-dashboard.ai",
            contact_name="Amina",
            contact_email="amina.comparison@example.com",
            contact_phone="+254700555111",
        )
    )

    client = TestClient(app)
    response = client.post(
        "/api/simulator/compare-reply",
        json={
            "prospect_id": snapshot.prospect.prospect_id,
            "scenario_name": "pricing",
            "body": "Can you give me a fixed total?",
            "channel": "email",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["prospect_id"] == snapshot.prospect.prospect_id
    assert data["action_type"] == "email_reply"
    assert "Week 11" in data["improvement_summary"] or data["final_decision"] == "allow"
