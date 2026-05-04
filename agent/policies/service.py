from agent.generation.service import generation_service
from agent.schemas.briefs import CompetitorGapBrief, HiringSignalBrief
from agent.schemas.conversation import ConversationDecision
from agent.schemas.prospect import ProspectRecord
from agent.seed.loader import seed_materials


class PolicyService:
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _strongest_signal(self, hiring_signal_brief: HiringSignalBrief) -> str:
        if not hiring_signal_brief.signals:
            return "I found only partial public signal for your team."
        signal = max(hiring_signal_brief.signals, key=lambda item: item.confidence)
        if signal.confidence < 0.65:
            return f"I found a partial signal worth checking: {signal.summary}"
        return signal.summary

    def _build_subject(
        self,
        segment: str,
        company_name: str,
        hiring_signal_brief: HiringSignalBrief,
    ) -> str:
        """Construct a segment-appropriate subject line within the 60-char limit.

        Prefix rules come from email_sequences/cold.md:
          - Segment 1 (funded startup): Context: [funding event]
          - Segment 2 (restructuring):  Note on [company] engineering
          - Segment 3 (leadership):     Congrats on the [role] appointment
          - Segment 4 (capability gap): Question on [capability signal]
          - abstain:                    Context: engineering signal
        """
        prefix = seed_materials.get_subject_prefix(segment)
        max_len = seed_materials.style.max_subject_chars

        if segment == "recently_funded_startup":
            candidate = f"{prefix}: {company_name} funding and engineering"
        elif segment == "mid_market_restructuring":
            candidate = f"{prefix} {company_name} engineering"
        elif segment == "engineering_leadership_transition":
            # Use leadership signal if available for specificity
            strongest = hiring_signal_brief.signals[0].summary if hiring_signal_brief.signals else ""
            role_hint = "CTO" if "cto" in strongest.lower() else "the engineering appointment"
            candidate = f"{prefix} {role_hint}"
        elif segment == "specialized_capability_gap":
            candidate = f"{prefix} {company_name} AI capability"
        else:
            candidate = f"{prefix}: engineering signal"

        if len(candidate) <= max_len:
            return candidate

        # Shorten: try without company name
        if segment in {"recently_funded_startup", "mid_market_restructuring"}:
            return f"{prefix}: engineering signal"[:max_len]
        return candidate[:max_len]

    def _build_body_and_signature(
        self,
        *,
        segment: str,
        ai_maturity_score: int,
        contact_name: str | None,
        first_signal: str,
        peer_note: str,
        ask: str,
    ) -> tuple[str, str]:
        """Build the 4-sentence cold email body and the signature separately.

        Structure from email_sequences/cold.md:
          Sentence 1 — concrete fact from signal brief (first_signal)
          Sentence 2 — typical bottleneck for this segment
          Sentence 3 — specific Tenacious fit (ICP pitch language)
          Sentence 4 — the ask (15 minutes, low pressure)
        """
        greeting = contact_name or "there"
        bottleneck = seed_materials.get_bottleneck_sentence(segment)
        tenacious_fit = seed_materials.get_pitch_language(segment, ai_maturity_score)

        body_content = (
            f"Hi {greeting},\n\n"
            f"{first_signal}\n\n"
            f"{bottleneck}\n\n"
            f"We work with teams at this stage to {tenacious_fit}."
            f"{peer_note}\n\n"
            f"{ask}"
        )
        signature = (
            "\n\nBest,\n"
            "Tenacious research workflow\n"
            "Tenacious Intelligence Corporation\n"
            "gettenacious.com"
        )
        return body_content, signature

    def _validate_style(self, subject: str, body_content: str) -> list[str]:
        """Return style violations using style_guide.md constraints via seed_materials."""
        return seed_materials.validate_email_style(subject, body_content)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draft_initial_decision(
        self,
        prospect: ProspectRecord,
        hiring_signal_brief: HiringSignalBrief,
        competitor_gap_brief: CompetitorGapBrief,
        *,
        trace_id: str | None = None,
        correction_memory: list[str] | None = None,
    ) -> ConversationDecision:
        risk_flags: list[str] = []

        # --- Signal and policy risk flags ---
        if any(signal.score < 0.5 for signal in hiring_signal_brief.confidence_by_signal):
            risk_flags.append("low_confidence_signal_present")
        if competitor_gap_brief.confidence < 0.5:
            risk_flags.append("omit_strong_competitor_gap_claims")
        if prospect.primary_segment == "abstain" or prospect.segment_confidence < 0.6:
            risk_flags.append("segment_abstention")
        if not hiring_signal_brief.bench_match.sufficient:
            risk_flags.append("bench_mismatch_route_human")
        if "Do not present development-mode estimates as verified public facts." in hiring_signal_brief.do_not_claim:
            risk_flags.append("development_mode_only")

        # --- Content assembly ---
        first_signal = self._strongest_signal(hiring_signal_brief)

        # Peer note: only when confidence is high and segment is not abstain
        peer_note = ""
        if competitor_gap_brief.confidence >= 0.6 and prospect.primary_segment != "abstain":
            first_peer = competitor_gap_brief.peer_companies[0] if competitor_gap_brief.peer_companies else "a peer"
            first_practice = (
                competitor_gap_brief.top_quartile_practices[0]
                if competitor_gap_brief.top_quartile_practices
                else "Delivery priorities are more legible in public."
            )
            peer_note = (
                f"\n\nOne peer signal: {first_peer}. {first_practice} "
                "I would treat that as a question, not a conclusion."
            )

        ask = (
            "Would it be useful if I sent the two-page research note?"
            if prospect.primary_segment == "abstain"
            else "Worth 15 minutes next week to walk through what we found?"
        )

        # --- Subject (seed-driven prefix + 60-char limit) ---
        subject = self._build_subject(
            segment=prospect.primary_segment,
            company_name=prospect.company_name,
            hiring_signal_brief=hiring_signal_brief,
        )

        # --- Body (4-sentence structure from cold.md, pitch from icp_definition.md) ---
        body_content, signature = self._build_body_and_signature(
            segment=prospect.primary_segment,
            ai_maturity_score=prospect.ai_maturity_score,
            contact_name=prospect.contact_name,
            first_signal=first_signal,
            peer_note=peer_note,
            ask=ask,
        )

        # --- Style validation (style_guide.md) ---
        style_violations = self._validate_style(subject, body_content)
        if style_violations:
            for v in style_violations:
                risk_flags.append(f"style_violation:{v}")
            # A violation routes to human review — do not suppress the draft
            risk_flags.append("style_validation_failed")

        fallback_body = f"{body_content}{signature}"
        draft = generation_service.draft_email_from_scaffold(
            trace_id=trace_id,
            prospect_id=prospect.prospect_id,
            scenario="initial_outreach",
            company_name=prospect.company_name,
            contact_name=prospect.contact_name,
            fallback_subject=subject,
            fallback_body=fallback_body,
            context={
                "primary_segment": prospect.primary_segment_label,
                "segment_confidence": round(prospect.segment_confidence, 2),
                "ai_maturity_score": prospect.ai_maturity_score,
                "recommended_pitch_angle": hiring_signal_brief.recommended_pitch_angle,
                "signals": [signal.summary for signal in hiring_signal_brief.signals[:4]],
                "confidence_by_signal": [
                    {
                        "signal_name": item.signal_name,
                        "score": item.score,
                    }
                    for item in hiring_signal_brief.confidence_by_signal
                ],
                "top_quartile_practices": competitor_gap_brief.top_quartile_practices[:3],
                "safe_gap_framing": competitor_gap_brief.safe_gap_framing,
                "do_not_claim": hiring_signal_brief.do_not_claim,
                "risk_flags": risk_flags,
                "recommendation_memory": correction_memory or [],
            },
        )

        return ConversationDecision(
            next_action="send_email",
            channel="email",
            reply_draft=draft.as_reply_draft,
            needs_human=not hiring_signal_brief.bench_match.sufficient or bool(style_violations),
            risk_flags=risk_flags,
            trace_tags=[
                "draft_initial_outreach",
                "seed_driven_policy",
                "confidence_aware_policy",
                "llm_rewritten" if draft.source == "openrouter" else "deterministic_fallback",
            ],
        )


policy_service = PolicyService()
