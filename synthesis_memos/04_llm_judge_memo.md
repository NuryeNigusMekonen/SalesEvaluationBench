# LLM-As-A-Judge Memo

The LLM-as-a-judge survey pushes on a simple point: a judge is not reliable just because it explains itself. That is especially relevant for Tenacious-Bench because the benchmark is built around business boundaries that sound plausible when violated. A confident, polished critique can still miss the rule that actually matters.

That is why the interim evaluator is deliberately structured and a little boring. It scores a candidate judge response on verdict accuracy, grounded-reason overlap, and source citation match. It is not pretending to be the final judge model; it is a reproducible scaffold for the benchmark. The dataset rows themselves also carry `chosen` and `rejected` critiques, which makes them usable for later pairwise preference tuning.

The design choice I would defend against a looser reading of the survey is not to start with unconstrained free-form critique generation. For this workflow, structure comes first. The judge has to tell us whether the row is `pass`, `fail`, or `needs_human_review`, and it has to point back to the seed materials that justify that call. Style can come later. Reliability has to come first.
