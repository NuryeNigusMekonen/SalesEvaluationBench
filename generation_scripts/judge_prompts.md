# Judge Prompts And Routing Notes

## Current interim state

The repo already contains a fully local, manually reviewed seed dataset in `training/data/tenacious_bench_seed_200_v2.jsonl`. For the Wednesday interim, the benchmark is materialized from that local artifact instead of calling external models.

The executable routing and filter logic lives in `generation_scripts/materialize_tenacious_bench.py` with random seed `20260429`. It assigns a judge model family by deterministic rotation, blocks self-judging by author family, scores coherence / grounding / rubric clarity against `>= 4/5` thresholds, and removes exact duplicate chosen/rejected preference-pair signatures before split assignment.

## Planned model roles for Days 4-7

- Hard-case author:
  Frontier model family through OpenRouter, used only for novel adversarial seeds that are not already covered by traces, templates, or transcript-grounded tasks.
- Bulk variation:
  Cheap dev-tier model family through OpenRouter, used to expand approved seed scenarios into paraphrases after contamination-safe grouping rules are in place.
- Judge / quality filter:
  Separate model family from the generator. Never use the same model family to both generate and judge the same task family.

## Prompt contracts

### Hard-case author prompt

Goal: produce one Tenacious-specific failure case grounded in local seed materials, not a generic sales prompt.

Requirements:
- cite the exact local seed artifact or trace family
- keep the failure centered on one primary risk focus
- produce both a plausible flawed output and the expected safe verdict
- avoid reusing existing scenario IDs

### Bulk variation prompt

Goal: vary company, contact, phrasing, and thread state while preserving the same policy boundary.

Requirements:
- preserve the same risk focus and same underlying rule
- do not paraphrase any sealed held-out task
- keep all generated variants tagged with prompt template version and source scenario family

### Judge filter prompt

Goal: return a structured verdict over the generated task:

```json
{
  "include": true,
  "coherence_score": 1,
  "grounding_score": 1,
  "rubric_clarity_score": 1,
  "notes": "..."
}
```

Inclusion thresholds for the final version:
- coherence: `>= 4/5`
- grounding: `>= 4/5`
- rubric clarity: `>= 4/5`

The same thresholds are encoded in `JUDGE_DIMENSION_THRESHOLDS` so they are checked by code, not only documented here.

## Leakage guardrails

- Do not use the same model family to author and judge the same task.
- Do not generate from held-out prompts.
- Keep prompt template versions in task metadata.
- Run contamination checks after every generation batch before split promotion.
