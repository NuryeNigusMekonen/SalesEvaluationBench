from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "eval" / "ablation_harness.py"
SPEC = importlib.util.spec_from_file_location("ablation_harness", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
ablation_harness = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ablation_harness
SPEC.loader.exec_module(ablation_harness)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_instrument_task_execution_counts_tokens_latency_and_cost() -> None:
    pricing = ablation_harness.TokenPriceSpec(
        prompt_cost_per_1k=0.002,
        completion_cost_per_1k=0.004,
    )

    metrics = ablation_harness.instrument_task_execution(
        prompt_text="hello grounded world",
        completion_text="safe reply",
        started_at=10.0,
        finished_at=10.25,
        pricing=pricing,
        llm_calls=2,
    )

    assert metrics.prompt_tokens == 3
    assert metrics.completion_tokens == 2
    assert metrics.total_tokens == 5
    assert metrics.latency_ms == 250.0
    assert metrics.cost_usd == 0.000014
    assert metrics.llm_calls == 2


def test_harness_runs_delta_a_delta_b_delta_c_and_cost_pareto(tmp_path: Path) -> None:
    held_out = tmp_path / "held_out_traces.jsonl"
    baseline_md = tmp_path / "baseline.md"
    score_log = tmp_path / "score_log.json"

    _write_jsonl(
        held_out,
        [
            {"condition": "day1_baseline", "task_id": "t1", "passed": False, "latency_ms": 4000, "cost_usd": 0.02},
            {"condition": "day1_baseline", "task_id": "t2", "passed": False, "latency_ms": 4200, "cost_usd": 0.02},
            {"condition": "day1_baseline", "task_id": "t3", "passed": True, "latency_ms": 4100, "cost_usd": 0.02},
            {"condition": "day1_baseline", "task_id": "t4", "passed": False, "latency_ms": 4300, "cost_usd": 0.02},
            {"condition": "automated_optimization_budget_match", "task_id": "t1", "passed": True, "latency_ms": 5100, "cost_usd": 0.03},
            {"condition": "automated_optimization_budget_match", "task_id": "t2", "passed": False, "latency_ms": 5200, "cost_usd": 0.03},
            {"condition": "automated_optimization_budget_match", "task_id": "t3", "passed": True, "latency_ms": 5000, "cost_usd": 0.03},
            {"condition": "automated_optimization_budget_match", "task_id": "t4", "passed": False, "latency_ms": 5300, "cost_usd": 0.03},
            {"condition": "full_method", "task_id": "t1", "passed": True, "latency_ms": 4500, "cost_usd": 0.026},
            {"condition": "full_method", "task_id": "t2", "passed": True, "latency_ms": 4400, "cost_usd": 0.026},
            {"condition": "full_method", "task_id": "t3", "passed": True, "latency_ms": 4300, "cost_usd": 0.026},
            {"condition": "full_method", "task_id": "t4", "passed": False, "latency_ms": 4200, "cost_usd": 0.026},
        ],
    )
    baseline_md.write_text(
        "Program staff have provided the official baseline: the published tau2 retail reference pass@1 is approximately 0.42 (42%).\n",
        encoding="utf-8",
    )
    score_log.write_text(
        json.dumps(
            [
                {
                    "condition": "tau2_retail_deepseek_v3_proactive_tools",
                    "evaluated_tasks": 26,
                    "pass_at_1_mean": 0.462,
                    "prompt_tokens": 2600,
                    "completion_tokens": 260,
                    "total_tokens": 2860,
                    "recorded_cost_usd": 0.52,
                    "llm_calls": 34,
                }
            ]
        ),
        encoding="utf-8",
    )

    harness = ablation_harness.AblationHarness(
        condition_specs=ablation_harness.default_condition_specs(
            held_out,
            score_log,
            baseline_md,
        ),
        local_trace_runner=ablation_harness.LocalTraceConditionRunner(),
        tau2_reference_runner=ablation_harness.Tau2ReferenceRunner(
            score_log_path=score_log,
            baseline_md_path=baseline_md,
        ),
        bootstrap_samples=200,
        seed=7,
    )

    report = harness.run("all")

    delta_a = report["comparisons"]["delta_a"]
    delta_b = report["comparisons"]["delta_b"]
    delta_c = report["comparisons"]["delta_c"]

    assert delta_a["delta"] == 0.5
    assert delta_a["paired_task_count"] == 4
    assert delta_a["statistical_test"] == "paired_bootstrap_ci + exact_mcnemar"
    assert delta_a["ci95_low"] <= delta_a["delta"] <= delta_a["ci95_high"]

    assert delta_b["delta"] == 0.25
    assert delta_b["paired_task_count"] == 4

    assert delta_c["mode"] == "informational_only"
    assert delta_c["tau2_reference_pass_at_1"] == 0.42
    assert delta_c["recorded_tau2_pass_at_1"] == 0.462
    assert delta_c["delta"] == 0.042

    pareto_rows = report["comparisons"]["cost_pareto"]
    assert len(pareto_rows) == 3
    assert any(row["condition"] == "full_method" for row in pareto_rows)
    assert report["conditions"]["full_method"]["summary"]["prompt_token_coverage_pct"] == 0.0
    assert report["failures"] == []


def test_harness_reports_failure_when_required_condition_is_missing(tmp_path: Path) -> None:
    held_out = tmp_path / "held_out_traces.jsonl"
    baseline_md = tmp_path / "baseline.md"
    score_log = tmp_path / "score_log.json"

    _write_jsonl(
        held_out,
        [
            {"condition": "day1_baseline", "task_id": "t1", "passed": False, "latency_ms": 4000, "cost_usd": 0.02},
        ],
    )
    baseline_md.write_text(
        "approximately 0.42 (42%)\n",
        encoding="utf-8",
    )
    score_log.write_text("[]", encoding="utf-8")

    harness = ablation_harness.AblationHarness(
        condition_specs=ablation_harness.default_condition_specs(
            held_out,
            score_log,
            baseline_md,
        ),
        local_trace_runner=ablation_harness.LocalTraceConditionRunner(),
        tau2_reference_runner=ablation_harness.Tau2ReferenceRunner(
            score_log_path=score_log,
            baseline_md_path=baseline_md,
        ),
        bootstrap_samples=50,
        seed=11,
    )

    report = harness.run("delta_a")

    assert report["comparisons"]["delta_a"] is None
    assert report["failures"]
    assert "full_method" in report["failures"][0]["message"] or "full_method" in report["failures"][0]["item"]


def test_paired_delta_requires_overlapping_task_ids() -> None:
    control = [
        ablation_harness.TaskOutcome(
            task_id="a",
            condition="day1_baseline",
            passed=False,
            instrumentation=ablation_harness.TaskInstrumentation(),
        )
    ]
    treatment = [
        ablation_harness.TaskOutcome(
            task_id="b",
            condition="full_method",
            passed=True,
            instrumentation=ablation_harness.TaskInstrumentation(),
        )
    ]

    try:
        ablation_harness.paired_pass_rate_delta(
            control,
            treatment,
            bootstrap_samples=50,
            seed=3,
        )
    except ablation_harness.AblationHarnessError as exc:
        assert "no overlapping task_ids" in str(exc)
    else:
        raise AssertionError("expected AblationHarnessError for non-overlapping task ids")


def test_local_trace_runner_derives_tokens_and_cost_from_richer_rows(tmp_path: Path) -> None:
    held_out = tmp_path / "held_out_traces.jsonl"
    _write_jsonl(
        held_out,
        [
            {
                "condition": "full_method",
                "task_id": "t1",
                "passed": True,
                "latency_ms": 2400,
                "prompt_text": "judge this grounded prompt",
                "completion_text": "safe grounded answer",
                "prompt_cost_per_1k": 0.002,
                "completion_cost_per_1k": 0.004,
                "llm_calls": 2,
            }
        ],
    )

    spec = ablation_harness.ConditionSpec(
        name="full_method",
        source_kind="local_trace",
        description="test",
        backbone_id="Qwen/Qwen2.5-3B-Instruct",
        intervention="trained_judge_guardrail",
        trained_component=True,
        artifact_path=held_out,
    )
    result = ablation_harness.LocalTraceConditionRunner().run(
        spec,
        bootstrap_samples=10,
        seed=5,
    )

    outcome = result.outcomes[0]
    assert outcome.instrumentation.prompt_tokens == 4
    assert outcome.instrumentation.completion_tokens == 3
    assert outcome.instrumentation.total_tokens == 7
    assert outcome.instrumentation.cost_usd == 0.00002
    assert result.summary is not None
    assert result.summary.prompt_token_coverage_pct == 100.0
    assert result.summary.completion_token_coverage_pct == 100.0
