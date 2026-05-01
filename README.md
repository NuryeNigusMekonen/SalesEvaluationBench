# The Conversion Engine

## Overview

Week 10 built the Tenacious sales agent. Week 11 adds the interim evaluation bench package on top of that existing agent, traces, probes, and seed materials.

![Dashboard Screenshot](screenshoot/dashboard.png)

The Week 11 deliverable is `Tenacious-Bench v0.1`, a local judge-task benchmark for evaluating whether a critic catches Tenacious-specific sales-agent failures: unsupported pricing or scope claims, overclaimed public signals, generic outreach, wrong CRM/calendar actions, and missed human escalation.

## Current status

- `tenacious_bench_v0.1/` is materialized in-repo with `train/`, `dev/`, and `held_out/` splits.
- Current benchmark size: `200` tasks total.
- Split counts: `100 train`, `60 dev`, `40 held_out`.
- Risk coverage: `5` Tenacious-specific risk foci, `40` tasks each.
- Source-mode mix: `96 programmatic`, `50 trace-derived`, `54 hand-authored adversarial`.
- Judge-task schema: [schema.json](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/schema.json)
- Deterministic evaluator: [scoring_evaluator.py](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/scoring_evaluator.py)
- Materialization seed for judge routing: `20260429`.
- Current state: interim / pre-public release; contamination and inter-rater limitations are documented.

## Environment and setup

Use Python `3.12`. The repo already includes a local virtualenv in `.venv/` in this workspace; if you are recreating the environment, install from `pyproject.toml` / `uv.lock`.

```bash
python --version
.venv/bin/python --version
.venv/bin/pytest --version
```

Regenerate and validate the Week 11 package:

```bash
python generation_scripts/materialize_tenacious_bench.py
python generation_scripts/run_contamination_checks.py
python training/validate_tenacious_bench.py training/data/tenacious_bench_seed_200_v2.jsonl --expected-count 200
```

## Evaluator invocation example

Run the built-in examples:

```bash
python scoring_evaluator.py --self-test
```

Score one candidate judge response against one benchmark task:

```bash
python scoring_evaluator.py path/to/task.json path/to/candidate_response.json
```

Expected candidate response shape:

```json
{
  "verdict": "fail",
  "reason": "The response quotes a scope-specific total that must be routed to a delivery lead.",
  "citations": ["pricing_sheet.md"]
}
```

The evaluator returns a numeric score out of `100` with sub-checks for verdict match, reason grounding overlap, and citation match. A score of `70` or higher passes.

## Directory map

- The Week 10 Tenacious sales agent under `agent/`
- Week 10 evidence artifacts under `probes/`, `eval/`, and `agent/data/`
- The Week 11 interim benchmark package under [tenacious_bench_v0.1](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/tenacious_bench_v0.1)
- Interim methodology, audit, datasheet, and reading memos at repo root and in `synthesis_memos/`
- Reproducible materialization and contamination scripts under [generation_scripts](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/generation_scripts)
- `training/data/`: seed datasets and manual review notes.
- `schema.json`: benchmark row contract.
- `contamination_check.json`: current split contamination report.

## Required documentation links

- [audit_memo.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/audit_memo.md)
- [methodology.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/methodology.md)
- [datasheet.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/datasheet.md)
- [synthesis_memos/](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/synthesis_memos)
- [contamination_check.json](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/contamination_check.json)
- [inter_rater_agreement.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/inter_rater_agreement.md)

## Act V Public Artifacts

- Hugging Face dataset: `https://huggingface.co/datasets/Nurye/tenacious_bench_v0.1`
- Hugging Face model: `N/A (Path B)`
- Technical blog post: `https://open.substack.com/pub/nuryenigus/p/tenacious-style-sales-agents?r=8bo5sh&utm_campaign=post&utm_medium=web&showWelcomeOnShare=true`
- Community issue/discussion: `https://github.com/sierra-research/tau2-bench/issues/276`
- Executive memo PDF: [memo.pdf](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/memo.pdf)
- Evidence graph: [evidence_graph.json](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/evidence_graph.json)

## What is next for Days 4-7

- Convert the `train/` split into SimPO preference pairs for Path B
- Run a stricter de-duplication pass over the synthetic expansion families before public release
- Complete the second inter-rater labeling round and revise any ambiguous rubric rows
- Train the small judge adapter, run ablations, and prepare the Hugging Face dataset/model cards

## Week 11 — Training-Ready Codebase

### Dataset

| Item | Path |
|------|------|
| Validated seed (v2) | `training/data/tenacious_bench_seed_200_v2.jsonl` |
| ⚠️ Deprecated seed (do not use) | ~~`training/data/tenacious_bench_seed_200.jsonl`~~ |

### Benchmark package

| Split | Path | Count |
|-------|------|-------|
| Train | `tenacious_bench_v0.1/train/tasks.jsonl` | 100 |
| Dev | `tenacious_bench_v0.1/dev/tasks.jsonl` | 60 |
| Held-out | `tenacious_bench_v0.1/held_out/tasks.jsonl` | 40 |
| Summary | `tenacious_bench_v0.1/summary.json` | — |

### Preference conversion files

| Split | Path | Count |
|-------|------|-------|
| Train preferences | `training/data/train_preferences.jsonl` | 100 |
| Dev preferences | `training/data/dev_preferences.jsonl` | 60 |
| Test preferences | `training/data/test_preferences.jsonl` | 40 |

### Validation commands

Run in this order before any Colab training session:

```bash
# 1. Validate seed dataset
python3 training/validate_tenacious_bench.py training/data/tenacious_bench_seed_200_v2.jsonl \
    --expected-count 200 \
    --expected-risk-distribution \
    unsupported_pricing_or_scope_claim=40,overclaimed_signal_or_maturity_claim=40,generic_outreach_ungrounded=40,wrong_crm_hubspot_calendar_next_action=40,reply_escalation_or_objection_failure=40

# 2. Validate benchmark split package
python3 training/validate_benchmark_package.py

# 3. Convert tasks to preference pairs
python3 training/convert_tasks_to_preferences.py

# 4. Validate preference splits
python3 training/validate_preference_splits.py
```

### Colab training plan

See [training/COLAB_TRAINING_GUIDE.md](training/COLAB_TRAINING_GUIDE.md) for the full step-by-step guide.

- Base model: `Qwen/Qwen2.5-3B-Instruct`
- Training method: SimPO + QLoRA (4-bit, Unsloth)
- Target runtime: Google Colab T4
- Config: [training/configs/simpo_qlora_colab.yaml](training/configs/simpo_qlora_colab.yaml)
- Output adapter: `outputs/tenacious-judge-simpo-lora/`

### Final evaluation plan

1. Run dev evaluation (`training/data/dev_preferences.jsonl`) after each training epoch.
2. Tune hyperparameters on dev only.
3. Run held-out evaluation (`training/data/test_preferences.jsonl`) once, at the end.
4. Target: average scoring_evaluator score ≥ 70 / 100 on held-out split.

## Week 11 — Tenacious v0.2 Judge Adapter Guardrail

The Tenacious v0.2 adapter is a local critic/guardrail for the Week 10 Conversion Engine. It is not the sales generator: the existing agent still drafts outreach, replies, CRM updates, and calendar actions, while the judge reviews candidate actions before they are sent, logged as final, or committed.

Place the unzipped local adapter at:

```bash
outputs/models/tenacious-judge-v02-simpo-lora/
```

Enable the guardrail explicitly:

```bash
TENACIOUS_JUDGE_ENABLED=true
TENACIOUS_JUDGE_ADAPTER_PATH=outputs/models/tenacious-judge-v02-simpo-lora
TENACIOUS_JUDGE_BASE_MODEL=Qwen/Qwen2.5-3B-Instruct
TENACIOUS_JUDGE_MAX_NEW_TOKENS=256
```

Default behavior remains unchanged with `TENACIOUS_JUDGE_ENABLED=false`. Inference is local and does not use a paid API by default; if the adapter, base model cache, or ML dependencies are unavailable, actions are routed to human review rather than allowed. Demo commands:

```bash
python scripts/demo_judge_adapter.py --mock
python scripts/demo_judge_adapter.py --real
python scripts/demo_judge_adapter.py --mock --comparison
```

Adapter weights are local artifacts only and are ignored by GitHub (`outputs/models/`, `*.safetensors`, and `*.zip`). Final evaluation summary: Combined dev 93.3%, v0.2 dev 86.7%, v0.2 held-out test 80.0%. Held-out was run once after dev review and was not used for tuning.

## Week 10 vs Week 11 Comparison Mode

Comparison mode shows the Week 10 candidate action beside the Week 11 judge-reviewed decision. Week 11 is a judge, not a generator: it does not rewrite the message. It only returns `PASS`, `FAIL`, or `HUMAN REVIEW`, and the engine maps that to `ALLOW`, `BLOCK`, or `ROUTE TO HUMAN`.

Environment:

```bash
TENACIOUS_JUDGE_ENABLED=true
TENACIOUS_JUDGE_ADAPTER_PATH=outputs/models/tenacious-judge-v02-simpo-lora
TENACIOUS_COMPARISON_MODE=true
TENACIOUS_COMPARISON_DRY_RUN=true
```

Defaults are safe:

```bash
TENACIOUS_COMPARISON_MODE=false
TENACIOUS_COMPARISON_DRY_RUN=true
```

Run the dashboard:

```bash
uvicorn agent.main:app --reload
```

Open `/dashboard`, go to `Simulator`, and enable `Week 11 Judge Comparison`. The simulator will show two panels for each compared reply: `Week 10 Baseline Output` and `Week 11 Judge Review`. In dry-run mode, email/SMS/CRM/calendar actions are previewed only:

- `PASS`: the baseline is allowed and the preview says `Would send`.
- `FAIL`: the output is blocked and the preview says `Blocked by Week 11 judge`.
- `HUMAN REVIEW`: the action is routed to a person and the preview says `Needs human review`.

Run the mock comparison demo:

```bash
python scripts/demo_judge_adapter.py --mock --comparison
```

Blocked outputs are the visible improvement: unsafe pricing claims, SMS/calendar escalation without consent, generic capacity overclaims, and opt-out follow-ups are prevented instead of being polished and sent. Comparison reviews are logged locally at `agent/data/comparison_reviews.jsonl` and exposed through `GET /api/comparison-reviews`; the simulator uses `POST /api/simulator/compare-reply`.

### Week 11 Guardrail Safety

Every outbound action (email, SMS, HubSpot CRM write, calendar confirmation) passes through four gates in order. A real provider call is only made when all four pass.

```
judge gate → dry-run gate → outbound gate → provider-config gate
```

| Gate | Env var / condition | Block result |
|---|---|---|
| Judge | `TENACIOUS_JUDGE_ENABLED=true` + verdict | `skipped` or `route_to_review` |
| Dry-run | `TENACIOUS_COMPARISON_MODE=true` AND `TENACIOUS_COMPARISON_DRY_RUN=true` | `previewed` (no external call) |
| Outbound | `OUTBOUND_ENABLED=true` (email, SMS, HubSpot) | `previewed` if false |
| Provider config | API key / token present | `previewed` if absent |

**Dry-run guarantees** (`TENACIOUS_COMPARISON_DRY_RUN=true`):

- Email: no POST to Resend or MailerSend; artifact written with `"status": "previewed"`.
- SMS: no POST to Africa's Talking; artifact written with `"status": "previewed"`.
- HubSpot: no contact search, no PATCH/POST to `api.hubapi.com`; artifact written with `"status": "previewed"`.
- Calendar confirmation: `handle_calendar_confirmation()` returns `ok=false, dry_run=true` without committing the booking, updating prospect status, or triggering any downstream CRM write.
- Comparison review is always logged to `agent/data/comparison_reviews.jsonl` regardless of dry-run state.

**`OUTBOUND_ENABLED` behavior**:

- Defaults to `false`. No live provider call is made unless explicitly set to `true`.
- Email and SMS already required this flag via `status().configured`. HubSpot now requires it too: `configured = bool(outbound_enabled and hubspot_access_token)`.
- Setting `OUTBOUND_ENABLED=false` prevents all Resend, MailerSend, Africa's Talking, and HubSpot API calls even when API credentials are present.

**Judge-disabled warning**:

When `OUTBOUND_ENABLED=true` and `TENACIOUS_JUDGE_ENABLED=false`, the dashboard runtime status and logs emit:

> Outbound is enabled while Week 11 judge is disabled. Actions may bypass the trained guardrail.

This is a visible warning, not a startup failure. Default Week 10 behavior (judge disabled) is preserved. The warning is surfaced in `GET /dashboard/state` under `tenacious_judge_runtime.judge_disabled_warning` and in the application log at WARNING level.

**Judge unavailable — fail closed**:

If the ML adapter is missing, dependencies are absent, or inference fails, `review_before_action()` returns `needs_human_review`. All real sends are blocked automatically.

### Cost Discipline

- Compute envelope: **$10 per trainee** (challenge limit).
- Total spend to date: **$0.021750** (two Week 10 τ²-Bench runs; all Week 11 work was $0).
- Training: Google Colab T4 free runtime + Unsloth + QLoRA + SimPO → **$0**.
- τ²-Bench retail rerun: **not run**. Week 10 result reused per challenge rules ("Re-running it costs roughly $5–8 per pass").
- All v0.1 and v0.2 dataset authoring used local rule-based scripts; no paid model API calls.
- Full cost log with per-entry evidence: [cost_log.md](cost_log.md).

### ⚠️ Deprecated seed warning

**Never** use `training/data/tenacious_bench_seed_200.jsonl` in any training, evaluation,
or conversion script. Use `tenacious_bench_seed_200_v2.jsonl` exclusively.
The `validate_benchmark_package.py` script will error if the deprecated file is referenced.

---

## Week 10 agent context

The underlying product is still the same Tenacious conversion agent:

- enrichment from public hiring, layoffs, leadership, and competitor signals
- policy gating for ICP fit, bench capacity, pricing scope, and human handoff
- outbound and reply orchestration across email, SMS, CRM, and calendar tools
- trace-first operation so failures can be converted into benchmark tasks

Important directories:

- `agent/`: application code for the sales agent
- `probes/`: Week 10 failure taxonomy and adversarial probes
- `training/data/`: seed datasets and review notes
- `tenacious_bench_v0.1/`: interim benchmark partitions
- `generation_scripts/`: reproducible materialization and contamination checks
