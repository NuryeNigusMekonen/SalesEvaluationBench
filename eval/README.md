# Eval Artifacts

This directory contains the local evaluation artifacts for the Tenacious challenge:

- `score_log.json`
- `trace_log.jsonl`
- `baseline.md`
- `tau2-bench/`
- `run_tau2_retail.sh`

The official Sierra `tau2-bench` repository is checked out at `eval/tau2-bench`. The upstream project now presents itself as tau-three/tau2 version 1.0.0, but the text-mode `retail` domain is still available and is the challenge anchor.

## Run the Retail Baseline

Install `uv`, configure the provider API keys required by the model you choose, then run. The wrapper loads the project-root `.env`; if you set `OPENROUTER_MODEL=google/gemini-2.0-flash-001`, it passes `openrouter/google/gemini-2.0-flash-001` to LiteLLM automatically.

```bash
TAU2_AGENT_LLM=gpt-4.1 TAU2_USER_LLM=gpt-4.1 ./eval/run_tau2_retail.sh
```

With the project `.env` OpenRouter settings, a small smoke run is:

```bash
TAU2_NUM_TRIALS=1 TAU2_NUM_TASKS=1 ./eval/run_tau2_retail.sh --max-concurrency 1
```

For the challenge, replace both model values with the program-pinned dev-tier model. The wrapper now defaults to `--max-concurrency 1` for more stable OpenRouter runs, and it also points the evaluator helpers at the same model family unless you override `TAU2_EVAL_LLM`, `TAU2_NL_ASSERTIONS_LLM`, or `TAU2_EVAL_USER_SIMULATOR_LLM`. You can also control run size:

```bash
TAU2_NUM_TRIALS=5 TAU2_NUM_TASKS=30 ./eval/run_tau2_retail.sh
```

Results are written by tau2 into `eval/tau2-bench/data/simulations/`. The existing `score_log.json` and `trace_log.jsonl` remain labeled as local surrogate artifacts until a real tau2 run is completed with credentials.

## Run The Ablation Harness

The Week 11 ablation harness lives at `eval/ablation_harness.py`. It exposes one shared interface for:

- `delta_a`: trained Path B guardrail vs Week 10 baseline on Tenacious held-out
- `delta_b`: same-backbone prompt-engineered intervention only vs trained component
- `delta_c`: informational tau2 reference handling from recorded artifacts only
- `cost_pareto`: pass@1, cost, and latency tradeoff summary

Run the full report:

```bash
python3 eval/ablation_harness.py \
  --comparison all \
  --bootstrap-samples 5000 \
  --output outputs/reports/ablation_harness_report.json
```

For a grader who wants to inspect the paired statistical implementation only:

```bash
python3 eval/ablation_harness.py \
  --comparison delta_a \
  --bootstrap-samples 5000 \
  --output outputs/reports/ablation_delta_a_report.json
```

The harness uses a paired bootstrap confidence interval and an exact paired test (`exact_mcnemar`) for Delta A and Delta B. Delta C never re-runs tau2; it reads `eval/score_log.json` and `eval/baseline.md` informationally.

## Richer Held-Out Trace Rows

`held_out_traces.jsonl` may contain only the minimal recorded fields:

- `condition`
- `task_id`
- `passed`
- `latency_ms`
- `cost_usd`
- `failure_mode`

If richer instrumentation is available, the same harness will also consume:

- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `llm_calls`
- `prompt_text`
- `completion_text` or `model_output`
- `prompt_cost_per_1k`
- `completion_cost_per_1k`

When token counts are omitted but raw text is present, the harness derives token counts from the text. When `cost_usd` is omitted but per-1K pricing fields are present, it computes per-task cost directly in the harness. The JSON report also surfaces prompt/completion token coverage percentages so instrumentation gaps are visible rather than hidden.
