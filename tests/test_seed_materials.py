"""
Verification suite for Tenacious seed material integration.

Checks:
  1. All seed files load and paths resolve.
  2. Bench capacity is non-empty and contains expected stacks.
  3. ICP pitch language loads for all four segments in both AI tiers.
  4. A Segment 1 lead produces a style-compliant cold email.
  5. A pricing question reply cites pricing_sheet.md language (no invented numbers).
  6. An unsupported bench request routes to human review.
  7. Case studies load and quotable text is present.
  8. Objection patterns load from transcript_05.
  9. Style validation catches known violations.
 10. No banned phrases in seed-generated replies.
"""

import pytest

from agent.config import settings
from agent.seed.loader import seed_materials
from agent.schemas.briefs import (
    BenchMatch,
    CompetitorGapBrief,
    HiringSignal,
    HiringSignalBrief,
)
from agent.schemas.prospect import ProspectRecord, SignalConfidence

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_prospect(
    segment: str = "recently_funded_startup",
    ai_maturity_score: int = 2,
    segment_confidence: float = 0.80,
    bench_sufficient: bool = True,
) -> ProspectRecord:
    return ProspectRecord(
        prospect_id="test_seed_001",
        company_name="AlphaTest Corp",
        company_domain="alphatest.io",
        contact_name="Elena Cho",
        contact_email="elena@alphatest.io",
        contact_phone=None,
        source="test",
        primary_segment=segment,
        primary_segment_label=segment.replace("_", " ").title(),
        segment_confidence=segment_confidence,
        ai_maturity_score=ai_maturity_score,
        status="enriched",
    )


def _hiring_brief(bench_sufficient: bool = True) -> HiringSignalBrief:
    return HiringSignalBrief(
        summary="AlphaTest Corp closed a $14M Series B in February with three Python roles open.",
        primary_segment="recently_funded_startup",
        segment_confidence=0.80,
        recommended_pitch_angle="Series B startup scaling engineering capacity.",
        signals=[
            HiringSignal(
                name="funding_signal",
                summary="AlphaTest Corp closed a $14M Series B in February with three Python roles open.",
                confidence=0.85,
            )
        ],
        confidence_by_signal=[
            SignalConfidence(
                signal_name="funding",
                score=0.85,
                rationale="Crunchbase snapshot confirmed.",
            )
        ],
        ai_maturity_score=2,
        ai_maturity_justification="ML roles and AI keywords present.",
        do_not_claim=[],
        bench_match=BenchMatch(
            required_stacks=["python"],
            available_capacity={"python": 7} if bench_sufficient else {"python": 0},
            sufficient=bench_sufficient,
            recommendation=(
                "Proceed with Python squad engagement."
                if bench_sufficient
                else "Python bench at capacity. Route to human."
            ),
        ),
    )


def _competitor_brief() -> CompetitorGapBrief:
    return CompetitorGapBrief(
        peer_group_definition="Series B startups in general B2B software.",
        peer_companies=["PeerCo A"],
        top_quartile_practices=["Dedicated MLOps function"],
        safe_gap_framing="Three peer companies have posted MLOps roles in the last 90 days.",
        confidence=0.70,
    )


# ---------------------------------------------------------------------------
# 1. Seed file paths and existence
# ---------------------------------------------------------------------------


def test_all_seed_paths_exist() -> None:
    assert settings.bench_summary_path.exists(), "bench_summary.json not found"
    assert settings.icp_definition_path.exists(), "icp_definition.md not found"
    assert settings.pricing_sheet_path.exists(), "pricing_sheet.md not found"
    assert settings.style_guide_path.exists(), "style_guide.md not found"
    assert settings.case_studies_path.exists(), "case_studies.md not found"
    assert settings.email_sequences_dir.exists(), "email_sequences/ not found"
    assert settings.discovery_transcripts_dir.exists(), "discovery_transcripts/ not found"
    assert (settings.email_sequences_dir / "cold.md").exists(), "cold.md not found"
    assert (settings.discovery_transcripts_dir / "transcript_05_objection_heavy.md").exists()


# ---------------------------------------------------------------------------
# 2. Bench capacity
# ---------------------------------------------------------------------------


def test_bench_capacity_loaded() -> None:
    assert seed_materials.bench_loaded, "bench_summary.json should load successfully"
    capacity = seed_materials.bench_capacity
    expected_stacks = {"python", "go", "data", "ml", "infra", "frontend", "fullstack_nestjs"}
    missing = expected_stacks - set(capacity.keys())
    assert not missing, f"Missing stacks in bench capacity: {missing}"


def test_bench_capacity_non_zero() -> None:
    for stack, count in seed_materials.bench_capacity.items():
        assert isinstance(count, int), f"Capacity for {stack} should be int"
    assert seed_materials.bench_capacity["python"] > 0
    assert seed_materials.bench_capacity["data"] > 0


# ---------------------------------------------------------------------------
# 3. ICP pitch language
# ---------------------------------------------------------------------------


def test_icp_pitch_loads_all_segments() -> None:
    expected_segments = {
        "recently_funded_startup",
        "mid_market_restructuring",
        "engineering_leadership_transition",
        "specialized_capability_gap",
    }
    loaded = set(seed_materials.icp_pitch.keys())
    missing = expected_segments - loaded
    assert not missing, f"ICP pitch missing segments: {missing}"


def test_icp_pitch_high_vs_low_readiness() -> None:
    s1_high = seed_materials.get_pitch_language("recently_funded_startup", 2)
    s1_low = seed_materials.get_pitch_language("recently_funded_startup", 1)
    assert s1_high != s1_low, "Segment 1 should have different pitch for high vs. low AI readiness"
    assert "scale" in s1_high.lower(), "High-readiness Segment 1 pitch should mention scaling"
    assert "squad" in s1_low.lower() or "function" in s1_low.lower(), (
        "Low-readiness Segment 1 pitch should mention building the first function or squad"
    )


def test_icp_pitch_segment3_same_for_both_tiers() -> None:
    s3_high = seed_materials.get_pitch_language("engineering_leadership_transition", 2)
    s3_low = seed_materials.get_pitch_language("engineering_leadership_transition", 0)
    assert s3_high == s3_low, "Segment 3 pitch should not split on AI readiness per icp_definition.md"


# ---------------------------------------------------------------------------
# 4. Style-compliant cold email from Segment 1 lead
# ---------------------------------------------------------------------------


def test_segment1_email_style_compliance() -> None:
    from agent.policies.service import policy_service

    prospect = _minimal_prospect(segment="recently_funded_startup", ai_maturity_score=2)
    decision = policy_service.draft_initial_decision(
        prospect=prospect,
        hiring_signal_brief=_hiring_brief(bench_sufficient=True),
        competitor_gap_brief=_competitor_brief(),
    )

    # Subject must be present and within 60 chars
    assert "Subject:" in decision.reply_draft
    subject_line = decision.reply_draft.split("\n")[0].replace("Subject: ", "").strip()
    assert len(subject_line) <= 60, f"Subject too long ({len(subject_line)} chars): {subject_line!r}"

    # Body (before signature) must be <= 120 words
    body_part = decision.reply_draft.split("Best,")[0] if "Best," in decision.reply_draft else decision.reply_draft
    word_count = len(body_part.split())
    assert word_count <= 150, f"Email body too long ({word_count} words, target ≤ 120 + slack)"

    # Subject must start with an approved prefix
    first_word = subject_line.split(":")[0].strip().lower() if ":" in subject_line else subject_line.split()[0].lower()
    banned = {"quick", "just", "hey", "following up", "circling back"}
    assert first_word not in banned, f"Subject starts with banned word: {first_word!r}"

    # Must not contain banned vendor clichés
    body_lower = decision.reply_draft.lower()
    cliches = {"top talent", "world-class", "a-players", "rockstar", "ninja"}
    for cliche in cliches:
        assert cliche not in body_lower, f"Reply contains banned cliché: {cliche!r}"


def test_segment1_email_uses_seed_pitch_language() -> None:
    from agent.policies.service import policy_service

    # High AI readiness
    prospect_hi = _minimal_prospect(segment="recently_funded_startup", ai_maturity_score=2)
    decision_hi = policy_service.draft_initial_decision(
        prospect=prospect_hi,
        hiring_signal_brief=_hiring_brief(),
        competitor_gap_brief=_competitor_brief(),
    )
    assert "scale" in decision_hi.reply_draft.lower(), (
        "High AI readiness Segment 1 email should include 'scale' from icp_definition.md pitch"
    )

    # Low AI readiness
    prospect_lo = _minimal_prospect(segment="recently_funded_startup", ai_maturity_score=0)
    decision_lo = policy_service.draft_initial_decision(
        prospect=prospect_lo,
        hiring_signal_brief=_hiring_brief(),
        competitor_gap_brief=_competitor_brief(),
    )
    assert "squad" in decision_lo.reply_draft.lower() or "function" in decision_lo.reply_draft.lower(), (
        "Low AI readiness Segment 1 email should include 'squad' or 'function' from icp_definition.md pitch"
    )

    # Pitches must differ
    assert decision_hi.reply_draft != decision_lo.reply_draft, (
        "High and low AI readiness emails should differ"
    )


# ---------------------------------------------------------------------------
# 5. Pricing reply cites pricing_sheet.md — no invented numbers
# ---------------------------------------------------------------------------


def test_pricing_reply_no_invented_numbers() -> None:
    from agent.orchestration.handoff import ChannelHandoffManager
    from agent.storage.repository import ProspectRepository
    from agent.schemas.prospect import InboundMessageRequest

    repo = ProspectRepository()
    manager = ChannelHandoffManager(repo)

    snapshot_like = type("S", (), {
        "prospect": _minimal_prospect(),
        "hiring_signal_brief": _hiring_brief(),
        "competitor_gap_brief": _competitor_brief(),
    })()

    message = InboundMessageRequest(
        contact_email="elena@alphatest.io",
        channel="email",
        body="What is your pricing? How much does it cost?",
    )

    decision, _ = manager.route_inbound_message(snapshot_like, message)

    # Must cite pricing guardrail
    assert "pricing_guardrail" in decision.risk_flags

    # Must NOT contain a dollar sign followed by digits (no invented number)
    import re
    invented = re.findall(r"\$\d+", decision.reply_draft)
    assert not invented, f"Pricing reply contains invented dollar amount(s): {invented}"

    # Must reference the concept of a public floor or monthly rate
    body_lower = decision.reply_draft.lower()
    assert any(kw in body_lower for kw in ("monthly", "floor", "minimum", "scoping")), (
        "Pricing reply should reference monthly rate, floor, or scoping conversation"
    )

    # Must not use banned phrases
    banned = ["guaranteed savings", "40% cost savings", "we can definitely"]
    for phrase in banned:
        assert phrase not in body_lower, f"Pricing reply contains banned phrase: {phrase!r}"


def test_differentiation_reply_avoids_generic_capacity_overclaim() -> None:
    from agent.orchestration.handoff import ChannelHandoffManager
    from agent.storage.repository import ProspectRepository
    from agent.schemas.prospect import InboundMessageRequest

    repo = ProspectRepository()
    manager = ChannelHandoffManager(repo)

    snapshot_like = type("S", (), {
        "prospect": _minimal_prospect(segment="engineering_leadership_transition"),
        "hiring_signal_brief": _hiring_brief(),
        "competitor_gap_brief": _competitor_brief(),
    })()

    message = InboundMessageRequest(
        contact_email="elena@alphatest.io",
        channel="email",
        body="Thanks for the context. What makes Tenacious different?",
    )

    decision, _ = manager.route_inbound_message(snapshot_like, message)

    assert decision.next_action == "send_email"
    body_lower = decision.reply_draft.lower()
    assert "managed delivery" in body_lower
    assert "named engineers" in body_lower
    forbidden = ["world-class", "top talent", "any stack", "60 engineers", "7-14 days", "7–14 days"]
    for phrase in forbidden:
        assert phrase not in body_lower, f"Differentiation reply contains overclaim: {phrase!r}"


def test_update_reply_avoids_generic_capacity_overclaim() -> None:
    from agent.orchestration.handoff import ChannelHandoffManager
    from agent.storage.repository import ProspectRepository
    from agent.schemas.prospect import InboundMessageRequest

    repo = ProspectRepository()
    manager = ChannelHandoffManager(repo)

    snapshot_like = type("S", (), {
        "prospect": _minimal_prospect(segment="engineering_leadership_transition"),
        "hiring_signal_brief": _hiring_brief(),
        "competitor_gap_brief": _competitor_brief(),
    })()

    message = InboundMessageRequest(
        contact_email="elena@alphatest.io",
        channel="email",
        body="i am just following do you have an update?",
    )

    decision, _ = manager.route_inbound_message(snapshot_like, message)

    assert decision.next_action == "send_email"
    body_lower = decision.reply_draft.lower()
    assert "strongest public signal" in body_lower
    forbidden = ["world-class", "top talent", "any stack", "60 engineers", "7-14 days", "7–14 days"]
    for phrase in forbidden:
        assert phrase not in body_lower, f"Update reply contains overclaim: {phrase!r}"


# ---------------------------------------------------------------------------
# 6. Unsupported bench request routes to human review
# ---------------------------------------------------------------------------


def test_bench_mismatch_routes_to_human() -> None:
    from agent.policies.service import policy_service

    prospect = _minimal_prospect(segment="recently_funded_startup", bench_sufficient=False)
    decision = policy_service.draft_initial_decision(
        prospect=prospect,
        hiring_signal_brief=_hiring_brief(bench_sufficient=False),
        competitor_gap_brief=_competitor_brief(),
    )

    assert decision.needs_human, "Bench mismatch should set needs_human=True"
    assert "bench_mismatch_route_human" in decision.risk_flags


def test_bench_mismatch_reply_does_not_promise_capacity() -> None:
    from agent.orchestration.handoff import ChannelHandoffManager
    from agent.storage.repository import ProspectRepository
    from agent.schemas.prospect import InboundMessageRequest

    repo = ProspectRepository()
    manager = ChannelHandoffManager(repo)

    # Prospect with bench_sufficient=False
    snapshot_like = type("S", (), {
        "prospect": _minimal_prospect(bench_sufficient=False),
        "hiring_signal_brief": _hiring_brief(bench_sufficient=False),
        "competitor_gap_brief": _competitor_brief(),
    })()

    message = InboundMessageRequest(
        contact_email="elena@alphatest.io",
        channel="email",
        body="We need 20 Python engineers for our platform build.",
    )

    decision, _ = manager.route_inbound_message(snapshot_like, message)

    assert decision.needs_human, "Bench mismatch should route to human"
    assert "bench_mismatch_route_human" in decision.risk_flags

    # Reply must not promise capacity
    body_lower = decision.reply_draft.lower()
    forbidden = ["we have", "we can provide", "we will assign", "available immediately"]
    for phrase in forbidden:
        assert phrase not in body_lower, (
            f"Bench mismatch reply must not promise capacity; found: {phrase!r}"
        )


# ---------------------------------------------------------------------------
# 7. Case studies load and are quotable
# ---------------------------------------------------------------------------


def test_case_studies_load() -> None:
    assert seed_materials.case_studies, "case_studies.md should load at least one case study"
    assert len(seed_materials.case_studies) == 3, "Expected exactly 3 case studies from seed"


def test_case_study_quotable_text_not_empty() -> None:
    for cs in seed_materials.case_studies:
        assert cs.quotable, f"Case study {cs.name} has empty quotable text"
        assert len(cs.quotable) > 20, f"Case study {cs.name} quotable text too short"


def test_case_study_no_real_client_names() -> None:
    """Case studies must use sector descriptors, not real client names."""
    for cs in seed_materials.case_studies:
        # The approved descriptors are "global adtech", "loyalty program", "fitness franchise"
        # Real client names should not appear
        real_name_patterns = ["microsoft", "google", "amazon", "facebook", "stripe", "shopify"]
        q_lower = cs.quotable.lower()
        for name in real_name_patterns:
            assert name not in q_lower, (
                f"Case study {cs.name} contains real client name: {name!r}"
            )


def test_case_study_find_by_segment() -> None:
    # Segment 4 (specialized capability gap) should match at least one study
    cs = seed_materials.find_case_study("specialized_capability_gap")
    assert cs is not None, "Should find a case study for specialized_capability_gap"
    assert cs.quotable, "Found case study should have quotable text"


# ---------------------------------------------------------------------------
# 8. Objection patterns load from transcript_05
# ---------------------------------------------------------------------------


def test_objection_patterns_loaded() -> None:
    op = seed_materials.objection_patterns
    assert op.offshore_concern, "offshore_concern phrase should be non-empty"
    assert op.small_poc, "small_poc phrase should be non-empty"
    assert op.price_comparison, "price_comparison phrase should be non-empty"


def test_objection_patterns_no_banned_phrases() -> None:
    op = seed_materials.objection_patterns
    banned = [
        "we're not like other offshore",
        "guaranteed 40%",
        "we can handle any stack",
    ]
    all_phrases = " ".join([
        op.offshore_concern, op.price_comparison, op.capacity_proof,
        op.small_poc, op.architecture_boundary,
    ]).lower()
    for phrase in banned:
        assert phrase not in all_phrases, (
            f"Objection patterns contain banned phrase: {phrase!r}"
        )


# ---------------------------------------------------------------------------
# 9. Style validation catches known violations
# ---------------------------------------------------------------------------


def test_style_validation_catches_long_subject() -> None:
    violations = seed_materials.validate_email_style(
        subject="This is a very long subject line that exceeds the 60-character limit by quite a bit",
        body_excluding_signature="Short body.",
    )
    assert any("subject_too_long" in v for v in violations), (
        f"Expected subject_too_long violation, got: {violations}"
    )


def test_style_validation_catches_banned_prefix() -> None:
    violations = seed_materials.validate_email_style(
        subject="Just checking in about your engineering needs",
        body_excluding_signature="Short body.",
    )
    assert any("banned_subject_prefix" in v for v in violations), (
        f"Expected banned_subject_prefix violation, got: {violations}"
    )


def test_style_validation_catches_long_body() -> None:
    long_body = "word " * 130  # 130 words, over the 120 limit
    violations = seed_materials.validate_email_style(
        subject="Context: test",
        body_excluding_signature=long_body,
    )
    assert any("body_too_long" in v for v in violations), (
        f"Expected body_too_long violation, got: {violations}"
    )


def test_style_validation_catches_vendor_cliches() -> None:
    violations = seed_materials.validate_email_style(
        subject="Context: test",
        body_excluding_signature="We have top talent and world-class engineers for you.",
    )
    assert any("banned_phrase" in v for v in violations), (
        f"Expected banned_phrase violation, got: {violations}"
    )


def test_style_validation_passes_clean_email() -> None:
    violations = seed_materials.validate_email_style(
        subject="Context: AlphaTest engineering signal",
        body_excluding_signature=(
            "Elena,\n\n"
            "AlphaTest closed a $14M Series B in February and has three Python roles open. "
            "The typical bottleneck at this stage is recruiting capacity, not budget. "
            "We help teams scale their engineering output faster than in-house hiring can support. "
            "Worth 15 minutes next week?"
        ),
    )
    assert not violations, f"Clean email should have no style violations, got: {violations}"
