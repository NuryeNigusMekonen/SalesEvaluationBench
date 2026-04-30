# Week 11 v0.2 Self-Adjudication Report

This document is a **first-pass self-review**, not a final independent human review. The targeted row repairs below close the evidence-alignment issues found in the first audit pass.

- Total approved: 100
- Total revise: 0
- Total reject: 0
- Rows needing changes: none

## Repairs Completed
- Aligned six pass rows so the outreach copy, chosen rationale, rejected rationale, and expected reason now use the exact public role count and role type from the row brief.
- Rewrote eleven CRM/calendar rejected rationales so they reference the correct company, channel state, and wrong operational reasoning for that row.
- Re-aligned `tb_v02_0092` so the Go stack, requested capacity, available capacity, agent output, and pricing critique all point at the same unsupported claim.

## Split Recommendation
The dataset is now clean enough to proceed to final human manual adjudication. Do not split inside this step, but after that human pass it should be reasonable to create the 70/15/15 split with the existing contamination controls.
