# Contamination Memo

The contamination survey is probably the most operationally important common reading for this interim submission. The obvious failure mode is exact duplication; the subtler failure mode is paraphrase leakage, where a template family gets split across train, dev, and held-out. That subtler case is already visible in this repo: the exact `scenario_id` overlap is zero, but the token-similarity checks still surface synthetic families that are too close for comfort.

That shaped one concrete decision in the interim package: the contamination report is not a ceremonial success stamp. It records the residual leakage risk honestly. The repo now has split files, a deterministic checker, and documented limitations. That is better than a fake clean bill of health.

My disagreement with the strongest dynamic-benchmark framing is practical. A fully dynamic benchmark would be harder to validate than the current frozen interim release. For Week 11, the right move is a fixed split plus a clear contamination report, then a stricter refresh before the Hugging Face publication. Reproducibility matters more than novelty if the dynamic layer is not yet trustworthy.
