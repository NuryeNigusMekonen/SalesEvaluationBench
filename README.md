# The Conversion Engine

Week 10 built the Tenacious sales agent. Week 11 adds the interim evaluation bench package on top of that existing agent, traces, probes, and seed materials.

![Dashboard Screenshot](screenshoot/dashboard.png)

## Week 11 interim status

- `tenacious_bench_v0.1/` is materialized in-repo with `train/`, `dev/`, and `held_out/` splits.
- Current benchmark size: `200` tasks total.
- Split counts: `100 train`, `60 dev`, `40 held_out`.
- Risk coverage: `5` Tenacious-specific risk foci, `40` tasks each.
- Source-mode mix: `96 programmatic`, `50 trace-derived`, `54 hand-authored adversarial`.
- Judge-task schema: [schema.json](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/schema.json)
- Deterministic evaluator: [scoring_evaluator.py](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/scoring_evaluator.py)

## What this repo now contains

- The Week 10 Tenacious sales agent under `agent/`
- Week 10 evidence artifacts under `probes/`, `eval/`, and `agent/data/`
- The Week 11 interim benchmark package under [tenacious_bench_v0.1](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/tenacious_bench_v0.1)
- Interim methodology, audit, datasheet, and reading memos at repo root and in `synthesis_memos/`
- Reproducible materialization and contamination scripts under [generation_scripts](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/generation_scripts)

## Quick start

Create the interim benchmark package from the checked-in seed set:

```bash
python generation_scripts/materialize_tenacious_bench.py
python generation_scripts/run_contamination_checks.py
```

Validate the upstream seed dataset and inspect split counts:

```bash
python training/validate_tenacious_bench.py training/data/tenacious_bench_seed_200_v2.jsonl --expected-count 200
python scoring_evaluator.py --self-test
```

Key outputs:

- [audit_memo.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/audit_memo.md)
- [methodology.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/methodology.md)
- [datasheet.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/datasheet.md)
- [contamination_check.json](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/contamination_check.json)
- [inter_rater_agreement.md](/home/nurye/Desktop/TRP1/week10/TheConversionEngine/inter_rater_agreement.md)

## What is next for Days 4-7

- Convert the `train/` split into SimPO preference pairs for Path B
- Run a stricter de-duplication pass over the synthetic expansion families before public release
- Complete the second inter-rater labeling round and revise any ambiguous rubric rows
- Train the small judge adapter, run ablations, and prepare the Hugging Face dataset/model cards

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
