# Synthetic Data Memo

The synthetic-data paper is useful here because it warns against treating scale as quality. That lands directly on this repo: the risky move would be to produce hundreds of fluent sales rows that only look realistic because they share the same template voice. For Tenacious-Bench, synthetic rows are valuable only when they preserve a specific business boundary from the seed materials or Week 10 traces.

My design decision is to prefer targeted synthetic hard negatives over bulk expansion. The current `seed_200_v2` file is already strongest where the row is anchored to a concrete artifact family like `pricing_sheet.md`, `warm.md`, or a trace such as `tr_e3382190bf3c`. It is weakest where paraphrase families repeat a scaffold with only shallow entity changes. That is exactly why the interim release materializes the local seed set and documents contamination risk instead of pretending generation quality is already solved.

The point I would push back on is the temptation to read the paper as an argument for “more synthetic coverage” in the abstract. For this benchmark, more weakly checked synthetic coverage would make the judge look smarter than it is. A smaller adversarial slice with stronger provenance beats a bigger one with fuzzy evidence. That is the trade I would keep even if it lowers the apparent size of the public release.
