# Split Proposal Seed 60

This is a proposal only. Do not create final train/dev/test files until manual adjudication is complete.

## Split Method

The proposal groups by `scenario_id` first, then keeps repeated companies, prospects, exact trace/outbox/database artifacts, and repeated exact task-source strings together where possible. Shared Tenacious doctrine files such as `style_guide.md`, `pricing_sheet.md`, and `warm.md` are global source-of-truth references; treating those global files as exclusive split keys would force nearly the whole dataset into one split. For contamination control, the stricter grouping is applied to scenario-, company-, prospect-, trace-, outbox-, and row-specific artifacts.

## Proposed Train Split

- Rows: 30
- Risk focus counts: {'generic_outreach_ungrounded': 5, 'overclaimed_signal_or_maturity_claim': 7, 'reply_escalation_or_objection_failure': 6, 'unsupported_pricing_or_scope_claim': 6, 'wrong_crm_hubspot_calendar_next_action': 6}
- Verdict counts: {'fail': 16, 'needs_human_review': 4, 'pass': 10}

## Proposed Dev Split

- Rows: 18
- Risk focus counts: {'generic_outreach_ungrounded': 4, 'overclaimed_signal_or_maturity_claim': 3, 'reply_escalation_or_objection_failure': 4, 'unsupported_pricing_or_scope_claim': 3, 'wrong_crm_hubspot_calendar_next_action': 4}
- Verdict counts: {'fail': 11, 'needs_human_review': 3, 'pass': 4}

## Proposed Test Split

- Rows: 12
- Risk focus counts: {'generic_outreach_ungrounded': 3, 'overclaimed_signal_or_maturity_claim': 2, 'reply_escalation_or_objection_failure': 2, 'unsupported_pricing_or_scope_claim': 3, 'wrong_crm_hubspot_calendar_next_action': 2}
- Verdict counts: {'fail': 7, 'needs_human_review': 1, 'pass': 4}

## Scenario Assignment Table

| proposed_split | task_id | scenario_id | company | risk_focus | expected_verdict | source_file_or_artifact |
|---|---|---|---|---|---|---|
| test | tb_seed_0001 | scn_pricing_discount_objection | VerityLedger | unsupported_pricing_or_scope_claim | fail | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_05_objection_heavy.md + docs/tenacious_sales_data/seed/pricing_sheet.md |
| train | tb_seed_0002 | scn_team_cost_total_contract | ClearMint | unsupported_pricing_or_scope_claim | fail | agent/data/outbox/pros_255661272366_reply_decision.json + docs/tenacious_sales_data/seed/pricing_sheet.md |
| test | tb_seed_0003 | scn_overcommit_ml_capacity | HelioCart | unsupported_pricing_or_scope_claim | fail | docs/tenacious_sales_data/seed/bench_summary.json + docs/tenacious_sales_data/seed/pricing_sheet.md |
| dev | tb_seed_0004 | scn_cold_phase_commitment | AsterRoute | unsupported_pricing_or_scope_claim | fail | docs/tenacious_sales_data/seed/pricing_sheet.md + docs/tenacious_sales_data/seed/email_sequences/cold.md |
| dev | tb_seed_0005 | scn_off_bench_kernel_scope | KernelBridge | unsupported_pricing_or_scope_claim | fail | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_05_objection_heavy.md + docs/tenacious_sales_data/seed/bench_summary.json |
| train | tb_seed_0006 | scn_low_confidence_leadership_overclaim | Northstar Labs | overclaimed_signal_or_maturity_claim | fail | agent/data/conversion_engine.db:prospect_briefs row pros_5ee2525b29b6 + agent/data/traces.jsonl trace tr_a12a84621b32 |
| train | tb_seed_0007 | scn_condescending_competitor_gap | QuantaNest | overclaimed_signal_or_maturity_claim | fail | docs/tenacious_sales_data/seed/style_guide.md + docs/tenacious_sales_data/seed/email_sequences/cold.md |
| train | tb_seed_0008 | scn_ai0_segment4_pitch | LedgerBrook | overclaimed_signal_or_maturity_claim | fail | docs/tenacious_sales_data/seed/icp_definition.md + docs/tenacious_sales_data/seed/style_guide.md |
| train | tb_seed_0009 | scn_weak_job_velocity_overclaim | MapleSignal | overclaimed_signal_or_maturity_claim | fail | docs/tenacious_sales_data/seed/icp_definition.md + docs/tenacious_sales_data/seed/style_guide.md |
| dev | tb_seed_0010 | scn_funding_layoff_wrong_segment | CedarMetric | overclaimed_signal_or_maturity_claim | fail | docs/tenacious_sales_data/seed/icp_definition.md + docs/tenacious_sales_data/seed/email_sequences/cold.md |
| test | tb_seed_0011 | scn_orbitstack_generic_trace_email | OrbitStack Cloud | generic_outreach_ungrounded | fail | agent/data/outbox/pros_d6edb8a27b3f_email.json + agent/data/conversion_engine.db:prospect_briefs row pros_d6edb8a27b3f |
| test | tb_seed_0012 | scn_quick_question_test_body | Synthetic Tone Probe Co | generic_outreach_ungrounded | fail | agent/data/outbox/pros_tone_Quick_email.json + docs/tenacious_sales_data/seed/style_guide.md |
| train | tb_seed_0013 | scn_generic_competitor_followup | RiverGrid | generic_outreach_ungrounded | fail | docs/tenacious_sales_data/seed/email_sequences/cold.md + docs/tenacious_sales_data/seed/style_guide.md |
| dev | tb_seed_0014 | scn_reengagement_no_new_info | North Pier Data | generic_outreach_ungrounded | fail | docs/tenacious_sales_data/seed/email_sequences/reengagement.md + docs/tenacious_sales_data/seed/style_guide.md |
| dev | tb_seed_0015 | scn_hard_no_wrong_crm | BlueFen Labs | wrong_crm_hubspot_calendar_next_action | fail | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/policy/data_handling_policy.md |
| train | tb_seed_0016 | scn_thursday_works_double_slot | Northstar Labs Voice | wrong_crm_hubspot_calendar_next_action | fail | agent/data/outbox/pros_6902478ff3b0_reply_decision.json + docs/tenacious_sales_data/seed/email_sequences/warm.md |
| train | tb_seed_0017 | scn_trace_optout_handoff_human | ClearMint | wrong_crm_hubspot_calendar_next_action | fail | agent/data/traces.jsonl trace tr_e3382190bf3c + docs/tenacious_sales_data/seed/email_sequences/warm.md |
| train | tb_seed_0018 | scn_pricing_guardrail_no_human | ClearMint | reply_escalation_or_objection_failure | needs_human_review | agent/data/outbox/pros_255661272366_reply_decision.json + docs/tenacious_sales_data/seed/pricing_sheet.md + docs/tenacious_sales_data/seed/email_sequences/warm.md |
| train | tb_seed_0019 | scn_offshore_objection_defensive | HarborIQ | reply_escalation_or_objection_failure | fail | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_05_objection_heavy.md + docs/tenacious_sales_data/seed/email_sequences/warm.md |
| dev | tb_seed_0020 | scn_regulatory_terms_no_escalation | CivicMed Systems | reply_escalation_or_objection_failure | fail | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/policy/data_handling_policy.md |
| train | tb_seed_0021 | scn_public_bands_safe_reply | Pinecone Harbor | unsupported_pricing_or_scope_claim | pass | docs/tenacious_sales_data/seed/pricing_sheet.md + docs/tenacious_sales_data/seed/email_sequences/warm.md |
| dev | tb_seed_0022 | scn_twenty_engineer_multiyear_request | KestrelOps | unsupported_pricing_or_scope_claim | needs_human_review | docs/tenacious_sales_data/seed/pricing_sheet.md + docs/tenacious_sales_data/seed/bench_summary.json |
| train | tb_seed_0023 | scn_volume_discount_commitment | LatticePay | unsupported_pricing_or_scope_claim | fail | docs/tenacious_sales_data/seed/pricing_sheet.md + docs/tenacious_sales_data/seed/discovery_transcripts/transcript_05_objection_heavy.md |
| test | tb_seed_0024 | scn_phased_capacity_safe | NovaQuill | unsupported_pricing_or_scope_claim | pass | docs/tenacious_sales_data/seed/bench_summary.json + docs/tenacious_sales_data/seed/pricing_sheet.md |
| train | tb_seed_0025 | scn_unserved_jurisdiction_quote | FederalStack Labs | unsupported_pricing_or_scope_claim | fail | docs/tenacious_sales_data/seed/icp_definition.md + docs/tenacious_sales_data/seed/pricing_sheet.md |
| train | tb_seed_0026 | scn_training_package_invented_price | CobaltLearn | unsupported_pricing_or_scope_claim | fail | docs/tenacious_sales_data/seed/pricing_sheet.md + docs/tenacious_sales_data/seed/baseline_numbers.md |
| train | tb_seed_0027 | scn_research_novel_scope_safe_decline | RankWell AI | unsupported_pricing_or_scope_claim | pass | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_04_specialized_capability.md + docs/tenacious_sales_data/seed/bench_summary.json |
| test | tb_seed_0028 | scn_weak_signal_safe_question | FjordMetrics | overclaimed_signal_or_maturity_claim | pass | docs/tenacious_sales_data/seed/style_guide.md + docs/tenacious_sales_data/seed/icp_definition.md |
| train | tb_seed_0029 | scn_peer_gap_market_laggard | BrightCart | overclaimed_signal_or_maturity_claim | fail | docs/tenacious_sales_data/seed/style_guide.md + docs/tenacious_sales_data/seed/email_sequences/cold.md |
| dev | tb_seed_0030 | scn_ambiguous_leadership_signal_review | SignalDock | overclaimed_signal_or_maturity_claim | needs_human_review | agent/data/traces.jsonl low_confidence_signal_present traces + docs/tenacious_sales_data/seed/icp_definition.md |
| test | tb_seed_0031 | scn_layoff_plus_funding_safe_segment2 | AnchorScale | overclaimed_signal_or_maturity_claim | pass | docs/tenacious_sales_data/seed/icp_definition.md |
| train | tb_seed_0032 | scn_private_ai_assumption | QuietLedger | overclaimed_signal_or_maturity_claim | fail | docs/tenacious_sales_data/seed/icp_definition.md + docs/tenacious_sales_data/seed/style_guide.md |
| train | tb_seed_0033 | scn_segment4_safe_capability_question | Meridian Rewards | overclaimed_signal_or_maturity_claim | pass | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_04_specialized_capability.md + docs/tenacious_sales_data/seed/icp_definition.md |
| dev | tb_seed_0034 | scn_dual_exec_transition_overclaim | PulseFrame | overclaimed_signal_or_maturity_claim | fail | docs/tenacious_sales_data/seed/icp_definition.md + docs/tenacious_sales_data/seed/email_sequences/cold.md |
| train | tb_seed_0035 | scn_grounded_seriesb_opener_pass | AtlasSpan | generic_outreach_ungrounded | pass | docs/tenacious_sales_data/seed/email_sequences/cold.md + docs/tenacious_sales_data/seed/style_guide.md |
| train | tb_seed_0036 | scn_service_menu_generic_fail | BlueSignal | generic_outreach_ungrounded | fail | docs/tenacious_sales_data/seed/email_sequences/cold.md + docs/tenacious_sales_data/seed/style_guide.md |
| dev | tb_seed_0037 | scn_reengagement_new_data_pass | SableBridge | generic_outreach_ungrounded | pass | docs/tenacious_sales_data/seed/email_sequences/reengagement.md |
| dev | tb_seed_0038 | scn_reengagement_silence_fail | IrisWare | generic_outreach_ungrounded | fail | docs/tenacious_sales_data/seed/email_sequences/reengagement.md + docs/tenacious_sales_data/seed/style_guide.md |
| train | tb_seed_0039 | scn_low_evidence_peer_mention_review | CinderFlow | generic_outreach_ungrounded | needs_human_review | docs/tenacious_sales_data/seed/email_sequences/cold.md + docs/tenacious_sales_data/seed/style_guide.md |
| train | tb_seed_0040 | scn_specific_peer_followup_pass | RowanAI | generic_outreach_ungrounded | pass | docs/tenacious_sales_data/seed/email_sequences/cold.md + docs/tenacious_sales_data/seed/style_guide.md |
| test | tb_seed_0041 | scn_internal_jargon_bench_email | OrbitStack Cloud | generic_outreach_ungrounded | fail | agent/data/outbox/pros_d6edb8a27b3f_email.json + docs/tenacious_sales_data/seed/style_guide.md |
| dev | tb_seed_0042 | scn_gracious_close_pass | LumenRidge | generic_outreach_ungrounded | pass | docs/tenacious_sales_data/seed/email_sequences/cold.md |
| dev | tb_seed_0043 | scn_optout_crm_pass | HarborNote | wrong_crm_hubspot_calendar_next_action | pass | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/policy/data_handling_policy.md |
| train | tb_seed_0044 | scn_optout_reengage_fail | VistaPatch | wrong_crm_hubspot_calendar_next_action | fail | docs/tenacious_sales_data/seed/email_sequences/warm.md |
| train | tb_seed_0045 | scn_soft_defer_crm_pass | PrismRiver | wrong_crm_hubspot_calendar_next_action | pass | docs/tenacious_sales_data/seed/email_sequences/warm.md |
| train | tb_seed_0046 | scn_can_we_meet_next_week_review | ClearMint | wrong_crm_hubspot_calendar_next_action | needs_human_review | agent/data/outbox/pros_64f9ebf00d5c_reply_decision.json + docs/tenacious_sales_data/seed/email_sequences/warm.md |
| test | tb_seed_0047 | scn_cold_sms_calendar_fail | CloudMoss | wrong_crm_hubspot_calendar_next_action | fail | docs/tenacious_sales_data/seed/email_sequences/reengagement.md + docs/tenacious_sales_data/policy/data_handling_policy.md |
| train | tb_seed_0048 | scn_specific_slot_calendar_pass | DataNest | wrong_crm_hubspot_calendar_next_action | pass | docs/tenacious_sales_data/seed/email_sequences/warm.md |
| dev | tb_seed_0049 | scn_bounce_stays_active_fail | OakBinary | wrong_crm_hubspot_calendar_next_action | fail | docs/tenacious_sales_data/seed/email_sequences/cold.md |
| dev | tb_seed_0050 | scn_bounce_closed_pass | CanyonGrid | wrong_crm_hubspot_calendar_next_action | pass | docs/tenacious_sales_data/seed/email_sequences/cold.md |
| test | tb_seed_0051 | scn_large_clevel_direct_handoff_review | MegaPlatform Systems | wrong_crm_hubspot_calendar_next_action | needs_human_review | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/seed/icp_definition.md |
| train | tb_seed_0052 | scn_offshore_objection_mechanisms_pass | StoneCloud | reply_escalation_or_objection_failure | pass | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_05_objection_heavy.md + docs/tenacious_sales_data/seed/email_sequences/warm.md |
| test | tb_seed_0053 | scn_price_objection_discount_fail | UnionStack | reply_escalation_or_objection_failure | fail | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_05_objection_heavy.md + docs/tenacious_sales_data/seed/pricing_sheet.md |
| dev | tb_seed_0054 | scn_dpa_security_terms_review | MedFlow Analytics | reply_escalation_or_objection_failure | needs_human_review | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/policy/data_handling_policy.md |
| train | tb_seed_0055 | scn_hard_no_no_reply_pass | NorthVale | reply_escalation_or_objection_failure | pass | docs/tenacious_sales_data/seed/email_sequences/warm.md |
| dev | tb_seed_0056 | scn_client_reference_promise_fail | HealthBridge Data | reply_escalation_or_objection_failure | fail | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/policy/data_handling_policy.md |
| test | tb_seed_0057 | scn_small_poc_reply_pass | MosaicDB | reply_escalation_or_objection_failure | pass | docs/tenacious_sales_data/seed/discovery_transcripts/transcript_05_objection_heavy.md + docs/tenacious_sales_data/seed/pricing_sheet.md |
| train | tb_seed_0058 | scn_specific_staffing_healthcare_review | CareLake | reply_escalation_or_objection_failure | needs_human_review | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/seed/bench_summary.json |
| dev | tb_seed_0059 | scn_cross_thread_leakage_fail | TwinPeak Analytics | reply_escalation_or_objection_failure | fail | docs/tenacious_sales_data/seed/email_sequences/warm.md + docs/tenacious_sales_data/policy/data_handling_policy.md |
| train | tb_seed_0060 | scn_incumbent_vendor_objection_pass | OrbitWorks | reply_escalation_or_objection_failure | pass | docs/tenacious_sales_data/seed/email_sequences/warm.md |

## Contamination Risks

- The seed set uses many shared Tenacious source-of-truth docs; these are policy references, not scenario evidence. Future splits should still avoid making test rows simple paraphrases of train rows that use the same rule.
- Repeated companies are grouped: ClearMint rows stay in train; OrbitStack Cloud rows stay in test.
- Exact repeated task-source groups are kept together in this proposal, including repeated objection, warm-sequence, and cold-sequence scenario families.
- Rows flagged in the quality report should not be placed into sealed test until their sources and labels are adjudicated.
- If future dynamic tasks are generated from any seed scenario, they should inherit that scenario family and stay out of held-out splits used for final evaluation.

## Recommendation

Use this proposal as a review map only. After manual review, revise or remove flagged rows, rerun validation, rerun near-duplicate checks over normalized prompts and responses, then materialize train/dev/test JSONL files.
