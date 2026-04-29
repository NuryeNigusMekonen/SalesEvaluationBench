# Cost Log

This log records repo-visible compute and API costs to date. The Wednesday interim packaging pass itself used only local files and added no new external API cost.

| Date | Bucket | Amount (USD) | Source | Note |
|---|---|---:|---|---|
| 2026-04-23 | Held-out evaluation smoke | 0.003556 | `invoice_summary.json`, `eval/score_log.json` | τ²-Bench retail smoke run, Flash Lite |
| 2026-04-23 | Baseline reproduction | 0.018194 | `eval/score_log.json` | 5-task τ²-Bench retail submission-style run, Gemini Flash Lite |
| 2026-04-23 | Baseline reproduction | 0.000000 recorded | `eval/score_log.json` | DeepSeek V3 run matched the published baseline, but LiteLLM had no mapped pricing for the OpenRouter alias |
| 2026-04-29 | Dataset materialization | 0.000000 | local scripts | `generation_scripts/materialize_tenacious_bench.py` and contamination checks used only local repo artifacts |

## Current Week 11 interim interpretation

- No new τ²-Bench retail runs were performed for this interim packaging pass.
- No paid LLM calls were used to create the Wednesday split package.
- Residual model-routing and synthesis budget is still available for the final submission stage.
