# Cost Log — The Conversion Engine (Week 11)

Total compute envelope : **$10.00**

Every API and compute charge for this project is recorded below with timestamp, bucket, purpose, and amount. Entries are append-only; no amounts are altered retroactively.

---

## Week 11 Cost Table

| timestamp_utc | bucket | tool_or_service | purpose | cost_usd | evidence | notes |
|---|---|---|---|---:|---|---|
| 2026-04-23T00:00:00Z | Held-out evaluation | OpenRouter / Flash Lite (LiteLLM) | τ²-Bench retail smoke run — 5-task held-out evaluation | 0.003556 | `invoice_summary.json` → `llm_eval_usd_recorded: 0.003556`; `eval/score_log.json` | Week 10 carry-over. Smoke run only; not a full retail rerun. Provider billing should be verified against OpenRouter dashboard (LiteLLM pricing partially unmapped for this model alias). |
| 2026-04-23T00:00:00Z | Held-out evaluation | Gemini Flash Lite (LiteLLM) | τ²-Bench baseline reproduction — 5-task submission-style run | 0.018194 | `eval/score_log.json` | Week 10 carry-over. Establishes the DeepSeek V3 baseline against the Week 10 τ²-Bench result that is reused for Week 11. |
| 2026-04-23T00:00:00Z | Held-out evaluation | DeepSeek V3 via OpenRouter (LiteLLM) | τ²-Bench baseline reproduction — DeepSeek V3 run matched published baseline | 0.000000 | `eval/score_log.json` | LiteLLM had no mapped pricing for the OpenRouter alias; $0 recorded. Actual provider cost may be non-zero — verify in OpenRouter dashboard if needed. |
| 2026-04-29T00:00:00Z | Dataset authoring | Local scripts only | v0.1 dataset materialization — `generation_scripts/materialize_tenacious_bench.py` and contamination checks | 0.000000 | `cost_log.md` (prior entry); no API call in `generation_scripts/` | All generation used local repo artifacts. No external API calls. |
| 2026-04-29T00:00:00Z | Dataset authoring | Local scripts only | v0.2 seed expansion (100 rows) — `training/data/tenacious_bench_v0_2_expansion_100.jsonl`; validators; split creation | 0.000000 | `reports/week11_v02_expansion_report.md` → "no external APIs"; all `source_provenance.generator = local_rule_v02_style_guide_expansion` | Local rule-based generation only. No paid LLM calls. Confirmed by `paper_content_used: false` and `generation_notes` in every row's metadata. |
| 2026-04-29T00:00:00Z | Dataset authoring | Local scripts only | v0.2 self-adjudication and targeted row repairs | 0.000000 | `reports/week11_v02_self_adjudication_report.md` → "Total approved: 100; rows needing changes: none (repairs were local edits)" | No external model calls. Repairs were manual edits to JSONL rows. |
| 2026-04-30T00:00:00Z | Dataset authoring | Local scripts only | v0.2 split creation (70/15/15), preference conversion, and split/preference validation | 0.000000 | `training/validate_v02_split.py` and `training/validate_v02_preferences.py` both PASS locally | `training/convert_v02_tasks_to_preferences.py` generates preference files from local task JSONL; no API calls. |
| 2026-04-29T00:00:00Z | Training | Google Colab T4 (free tier) / Unsloth / QLoRA / SimPO | v0.1 SimPO QLoRA adapter training on `Qwen/Qwen2.5-3B-Instruct` | 0.000000 | `training/COLAB_TRAINING_GUIDE.md` (T4 GPU, free Colab runtime); `outputs/training_run_summary.json` MISSING — see note | Colab T4 free runtime was used. No paid compute charge. `outputs/training_run_summary.json` is absent (outputs/ directory not created in this repo); the $0 training cost is consistent with the free-tier path documented in `training/COLAB_TRAINING_GUIDE.md`. |
| 2026-04-29T00:00:00Z | Held-out evaluation | Local adapter / local scripts | Held-out evaluation on v0.1 preference files — `training/data/test_preferences.jsonl` | 0.000000 | `tenacious_bench_v0.1/summary.json` → held_out count 40; no API call evidence | Evaluation ran locally against the trained adapter. No external API calls. |
| — | Held-out evaluation | Not run | τ²-Bench retail validation rerun — explicitly skipped per challenge rules | 0.000000 | `docs/TRP1 Challenge Week 11_  Sales Agent Evaluation Bench.md` → "You will not re-run τ²-Bench retail this week. Re-running it costs roughly $5–8 per pass." | Week 10 τ²-Bench result reused as informational reference. No new retail run. |
| — | Reserve | — | Unspent reserve | 0.000000 | — | No reserve compute was used. |

---

## Budget Summary

| Item | Amount (USD) |
|---|---:|
| Total budget (per trainee) | 10.000000 |
| Week 10 carry-over (τ²-Bench smoke) | 0.003556 |
| Week 10 carry-over (τ²-Bench baseline reproduction) | 0.018194 |
| Week 10 carry-over (DeepSeek V3 — recorded as $0) | 0.000000 |
| Week 11 dataset authoring (v0.1 + v0.2, local only) | 0.000000 |
| Week 11 training (Colab T4 free tier) | 0.000000 |
| Week 11 held-out evaluation (local) | 0.000000 |
| τ²-Bench retail rerun (not run) | 0.000000 |
| Reserve used | 0.000000 |
| **Total recorded spend** | **0.021750** |
| **Remaining budget** | **9.978250** |

**Training cost note:** The default training path (Google Colab T4 free runtime + Unsloth + QLoRA + SimPO) was free. The T4 GPU is provided at no charge under Colab's free tier. No paid GPU or cloud compute was provisioned.

**τ²-Bench rerun note:** The challenge document explicitly states "You will not re-run τ²-Bench retail this week. Re-running it costs roughly $5–8 per pass." The Week 10 τ²-Bench result is reused as informational reference. Skipping this single run preserves approximately $5–8 of the $10 budget for dataset authoring and training.

---

## Compliance

This project followed the challenge cost-discipline rules as follows:

1. **No τ²-Bench retail rerun.** The Week 10 result is reused. No new retail τ²-Bench submission was made. No charges of $5–8 for a rerun appear in this log.

2. **No eval-tier model used during early dataset authoring.** All v0.1 and v0.2 dataset generation used local rule-based scripts (`source_provenance.generator = local_rule_v02_style_guide_expansion`). No OpenAI, Anthropic, or other paid model was called to author tasks.

3. **Local validators used before any training.** The following validators were run locally before any Colab training session:
   - `training/validate_tenacious_bench.py`
   - `training/validate_benchmark_package.py`
   - `training/convert_tasks_to_preferences.py`
   - `training/validate_preference_splits.py`
   - `training/validate_v02_split.py`
   - `training/validate_v02_preferences.py`

4. **Held-out set not repeatedly tuned against.** Dev evaluation was used for hyperparameter tuning. The held-out split (`training/data/test_preferences.jsonl`, 40 rows for v0.1; 15 rows for v0.2) was evaluated once at the end. The v0.1 held-out set is sealed and not used for v0.2 development.

5. **All API and compute charges logged.** Every charge — including $0 entries — is recorded in this file with a timestamp, bucket, tool or service, purpose, evidence pointer, and notes. The two non-zero entries from Week 10 (τ²-Bench smoke and baseline reproduction) total $0.021750.

---

## Evidence

| Claim | Evidence file | Key field or section |
|---|---|---|
| v0.1 paid API budget: $0 | `outputs/training_run_summary.json` | `paid_api_budget_used_usd: 0.0` — **file missing** (outputs/ directory not created in repo); cost is confirmed by Colab free-tier path in `training/COLAB_TRAINING_GUIDE.md` |
| v0.2 expansion: no external APIs, no training | `reports/week11_v02_expansion_report.md` | "Validation Result" section; `source_provenance.generator = local_rule_v02_style_guide_expansion` in every row |
| v0.2 self-adjudication: no external APIs | `reports/week11_v02_self_adjudication_report.md` | "Total approved: 100; rows needing changes: none" |
| τ²-Bench smoke and baseline reproduction costs | `invoice_summary.json` | `llm_eval_usd_recorded: 0.003556`; `eval/score_log.json` |
| v0.1 benchmark split metadata | `tenacious_bench_v0.1/summary.json` | `total_tasks: 200`, split counts, `random_seed: 20260429` |
| Training path (Colab T4, Unsloth, SimPO, QLoRA) | `training/COLAB_TRAINING_GUIDE.md`; `README.md` § "Colab training plan" | Base model `Qwen/Qwen2.5-3B-Instruct`, runtime "T4 GPU (free tier)" |
| Challenge rule: no τ²-Bench retail rerun | `docs/TRP1 Challenge Week 11_  Sales Agent Evaluation Bench.md` | "You will not re-run τ²-Bench retail this week. Re-running it costs roughly $5–8 per pass." |

### Missing evidence

- `outputs/training_run_summary.json` — the `outputs/` directory was not committed to the repo. The `paid_api_budget_used_usd: 0.0` value cited in context is consistent with the Colab T4 free-tier path and is recorded here as $0 on that basis. If the adapter outputs are available on Colab, the summary file should be downloaded and committed to `outputs/` to close this gap.
