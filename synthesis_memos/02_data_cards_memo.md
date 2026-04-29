# Data Cards Memo

The data-cards reading matters because this benchmark can be misunderstood very easily. Without documentation, it looks like a generic sales judgment set. It is not. It is a Tenacious-specific workflow benchmark built to judge whether a critic can catch pricing, signal-grounding, CRM, and escalation mistakes in a small, synthetic-but-grounded environment.

My main implementation choice from the paper is to keep the documentation close to the actual artifacts: `datasheet.md`, `summary.json`, `contamination_check.json`, and the source fields inside each row. That makes the benchmark legible from three angles at once: what the dataset is for, what is in it, and where a task came from.

Where I would disagree slightly with an expansive reading of the paper is on how much layered documentation is useful in a one-week build. A giant card can become its own source of drift. For this repo, the better move is a concise but complete datasheet, backed by directly inspectable row metadata and scripts. That still follows the spirit of the paper: clarity, provenance, intended use, and explicit limitations.
