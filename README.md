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
