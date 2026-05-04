import hashlib
import json
import re

from agent.config import settings
from agent.enrichment.ai_maturity import collect_ai_maturity_inputs, score_ai_maturity
from agent.enrichment.common import utc_now_iso
from agent.enrichment.competitor_gap import build_competitor_gap_brief
from agent.enrichment.connectors import (
    crunchbase_connector,
)
from agent.enrichment.crunchbase_odm import build_crunchbase_funding_signal
from agent.enrichment.job_post_scraper import build_job_post_signal
from agent.enrichment.layoffs_fyi_signal import build_layoff_signal
from agent.enrichment.leadership_changes import build_leadership_change_signal
from agent.schemas.briefs import (
    CompetitorGapBrief,
    BenchMatch,
    HiringSignal,
    HiringSignalBrief,
)
from agent.schemas.prospect import (
    SEGMENT_DISPLAY_NAMES,
    LeadIntakeRequest,
    ProspectRecord,
    SignalConfidence,
)


class EnrichmentService:
    """Hybrid enrichment flow backed by local snapshots with heuristic fallback."""

    SECTOR_KEYWORDS = {
        "fintech": {"pay", "fin", "bank", "credit", "lending", "treasury"},
        "healthtech": {"health", "care", "clinic", "med", "patient"},
        "commerce": {"shop", "retail", "market", "commerce", "cart"},
        "devtools": {"dev", "cloud", "infra", "platform", "data", "stack"},
    }

    def _stable_int(self, key: str, start: int, end: int) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        span = end - start + 1
        return start + (int(digest[:8], 16) % span)

    def _tokens(self, *parts: str | None) -> set[str]:
        text = " ".join(part or "" for part in parts).lower()
        return set(re.findall(r"[a-z0-9]+", text))

    def _infer_sector(self, tokens: set[str]) -> str:
        for sector, keywords in self.SECTOR_KEYWORDS.items():
            if tokens & keywords:
                return sector
        return "general_b2b"

    def _load_bench_capacity(self) -> dict[str, int]:
        if not settings.bench_summary_path.exists():
            return {}
        with open(settings.bench_summary_path, encoding="utf-8") as handle:
            bench = json.load(handle)
        return {
            stack_name: int(stack.get("available_engineers", 0))
            for stack_name, stack in bench.get("stacks", {}).items()
        }

    def _infer_required_stacks(self, tokens: set[str], ai_roles: int, sector: str) -> list[str]:
        required: set[str] = set()
        if tokens & {"python", "django", "fastapi", "flask"}:
            required.add("python")
        if tokens & {"go", "grpc", "microservices"}:
            required.add("go")
        if tokens & {"data", "analytics", "dbt", "snowflake", "databricks"}:
            required.add("data")
        if ai_roles or tokens & {"ai", "ml", "llm", "agent", "inference", "scientist"}:
            required.add("ml")
        if tokens & {"infra", "cloud", "platform", "kubernetes", "terraform"}:
            required.add("infra")
        if tokens & {"react", "frontend", "typescript", "next"}:
            required.add("frontend")
        if not required:
            required.add("data" if sector in {"fintech", "commerce", "healthtech"} else "python")
        return sorted(required)

    def _classify_segment(
        self,
        *,
        employee_estimate: int,
        funding_musd: int,
        funding_months_ago: int,
        job_openings: int,
        layoff_days_ago: int,
        layoff_pct: int,
        leadership_days_ago: int,
        ai_maturity_score: int,
        ai_roles: int,
        source_hits: int,
    ) -> tuple[str, float]:
        fresh_funding = funding_months_ago <= 6 and 5 <= funding_musd <= 30
        recent_layoff = layoff_days_ago <= 120 and layoff_pct <= 40
        leadership_recent = leadership_days_ago <= 90
        specialized_signal = ai_maturity_score >= 2 and ai_roles > 0

        if recent_layoff and fresh_funding and employee_estimate >= 180 and job_openings >= 3:
            confidence = 0.82
            segment = "mid_market_restructuring"
        elif leadership_recent and 50 <= employee_estimate <= 500:
            confidence = 0.78
            segment = "engineering_leadership_transition"
        elif specialized_signal:
            confidence = 0.74
            segment = "specialized_capability_gap"
        elif fresh_funding and 15 <= employee_estimate <= 80 and job_openings >= 5:
            confidence = 0.76
            segment = "recently_funded_startup"
        else:
            confidence = 0.45
            segment = "abstain"

        confidence += min(0.12, source_hits * 0.03)
        if segment == "recently_funded_startup" and recent_layoff and layoff_pct > 15:
            segment = "mid_market_restructuring"
            confidence = min(confidence, 0.72)
        if confidence < 0.6:
            return "abstain", round(confidence, 2)
        return segment, round(min(confidence, 0.94), 2)

    def enrich(
        self,
        intake: LeadIntakeRequest,
        *,
        prefer_browser_job_scrape: bool = False,
    ) -> tuple[
        ProspectRecord,
        HiringSignalBrief,
        CompetitorGapBrief,
    ]:
        seed_key = f"{intake.company_name}|{intake.company_domain or ''}|{intake.contact_email or ''}"
        tokens = self._tokens(intake.company_name, intake.company_domain)

        funding_signal = build_crunchbase_funding_signal(
            intake.company_name,
            intake.company_domain,
        )
        jobs_signal = build_job_post_signal(
            intake.company_name,
            intake.company_domain,
            prefer_browser_scrape=prefer_browser_job_scrape,
        )
        layoff_signal = build_layoff_signal(
            intake.company_name,
            intake.company_domain,
        )
        leadership_signal = build_leadership_change_signal(
            intake.company_name,
            intake.company_domain,
        )
        source_hits = sum(
            1
            for signal in (funding_signal, jobs_signal, layoff_signal, leadership_signal)
            if signal["matched"]
        )

        sector = funding_signal["sector"] or self._infer_sector(tokens)
        employee_estimate = int(
            funding_signal["employee_count"]
            or self._stable_int(seed_key + "employees", 18, 900)
        )
        company_record = crunchbase_connector.lookup(intake.company_name, intake.company_domain) or {}
        funding_musd = int(funding_signal["funding_musd"] or 0)
        funding_months_ago = int(funding_signal["funding_months_ago"] or 999)
        job_openings = int(jobs_signal["open_engineering_roles"] or 0)
        ai_roles = int(jobs_signal["ai_roles"] or 0)
        job_examples = jobs_signal["examples"] or []
        tokens |= self._tokens(*job_examples)
        layoff_days_ago = int(layoff_signal["days_ago"] or 999)
        layoff_pct = int(layoff_signal["percent"] or 0)
        leadership_days_ago = int(leadership_signal["days_ago"] or 999)

        ai_maturity_inputs = collect_ai_maturity_inputs(
            company_name=intake.company_name,
            company_domain=intake.company_domain,
            job_examples=job_examples,
            ai_roles=ai_roles,
            open_engineering_roles=job_openings,
            leadership_role=leadership_signal.get("role"),
            leadership_person=leadership_signal.get("person"),
            company_tokens=tokens,
            github_activity_text=company_record.get("github_activity"),
            executive_commentary_text=company_record.get("executive_commentary"),
            modern_stack_text=company_record.get("modern_stack"),
            strategic_communications_text=company_record.get("strategic_communications"),
        )
        ai_maturity_assessment = score_ai_maturity(ai_maturity_inputs)
        ai_maturity_score = ai_maturity_assessment.score
        ai_justification = ai_maturity_assessment.summary
        ai_confidence = ai_maturity_assessment.confidence

        funding_confidence = float(funding_signal["confidence"])
        jobs_confidence = float(jobs_signal["confidence"])
        layoff_confidence = float(layoff_signal["confidence"])
        leadership_confidence = float(leadership_signal["confidence"])

        primary_segment, segment_confidence = self._classify_segment(
            employee_estimate=employee_estimate,
            funding_musd=funding_musd,
            funding_months_ago=funding_months_ago,
            job_openings=job_openings,
            layoff_days_ago=layoff_days_ago if layoff_signal["matched"] else 999,
            layoff_pct=layoff_pct,
            leadership_days_ago=leadership_days_ago if leadership_signal["matched"] else 999,
            ai_maturity_score=ai_maturity_score,
            ai_roles=ai_roles,
            source_hits=source_hits,
        )
        segment_label = SEGMENT_DISPLAY_NAMES[primary_segment]

        prospect = ProspectRecord(
            company_name=intake.company_name,
            company_domain=intake.company_domain,
            contact_name=intake.contact_name,
            contact_email=intake.contact_email,
            contact_phone=intake.contact_phone,
            source=intake.source,
            primary_segment=primary_segment,
            primary_segment_label=segment_label,
            segment_confidence=segment_confidence,
            ai_maturity_score=ai_maturity_score,
            status="source_backed_brief_ready",
        )

        confidence_by_signal = [
            SignalConfidence(
                signal_name="funding_event",
                score=funding_confidence,
                rationale=(
                    "Crunchbase ODM match found and funding window filter applied."
                    if funding_signal["matched"]
                    else "No Crunchbase ODM record matched the company."
                ),
            ),
            SignalConfidence(
                signal_name="job_post_velocity",
                score=jobs_confidence,
                rationale=(
                    "Job-post velocity computed over a 60-day window from public-page snapshot data."
                    if jobs_signal["matched"]
                    else "No BuiltIn, Wellfound, or LinkedIn public-page snapshot matched the company."
                ),
            ),
            SignalConfidence(
                signal_name="layoff_signal",
                score=layoff_confidence,
                rationale=(
                    "Matched layoffs.fyi source data."
                    if layoff_signal["matched"]
                    else "No layoffs.fyi history matched the company."
                ),
            ),
            SignalConfidence(
                signal_name="leadership_change",
                score=leadership_confidence,
                rationale=(
                    "Matched press or Crunchbase-derived leadership change data."
                    if leadership_signal["matched"]
                    else "No leadership change was found in the active window."
                ),
            ),
            SignalConfidence(
                signal_name="ai_maturity",
                score=ai_confidence,
                rationale=ai_justification,
            ),
        ]

        signal_modules = [funding_signal, jobs_signal, layoff_signal, leadership_signal]
        hiring_signals = [
            HiringSignal(
                name=signal_payload["name"],
                summary=signal_payload["summary"],
                confidence=float(signal_payload["confidence"]),
                evidence=signal_payload["source_attribution"],
                source_attribution=signal_payload["source_attribution"],
                observed_at=signal_payload["observed_at"],
                collected_at=signal_payload["collected_at"],
                edge_case=signal_payload["edge_case"],
            )
            for signal_payload in signal_modules
        ]

        do_not_claim = [
            "Do not promise staffing capacity without bench confirmation.",
        ]
        if primary_segment == "abstain":
            do_not_claim.append("Do not use a segment-specific pitch; ask one exploratory question instead.")
        if not funding_signal["matched"]:
            do_not_claim.append("Do not present funding details as verified until a company snapshot match exists.")
        if jobs_signal["edge_case"] == "missing_job_post_record":
            do_not_claim.append("Do not claim hiring velocity unless public job-post evidence is matched.")
        if jobs_signal["edge_case"] == "zero_open_job_posts":
            do_not_claim.append("Do not imply active hiring when the public job-post window is currently zero.")
        if ai_maturity_score < 2:
            do_not_claim.append("Do not pitch a specialized AI capability gap as if it is confirmed.")
        if layoff_signal["edge_case"] == "no_layoff_history":
            do_not_claim.append("Do not assert restructuring pressure directly without layoff evidence.")
        if leadership_signal["edge_case"] == "no_leadership_change_in_window":
            do_not_claim.append("Do not frame outreach around a leadership transition that was not observed in-window.")

        brief_mode = "snapshot-backed" if source_hits >= 2 else "hybrid"
        required_stacks = self._infer_required_stacks(tokens, ai_roles, sector)
        bench_capacity = self._load_bench_capacity()
        available_capacity = {
            stack: bench_capacity.get(stack, 0)
            for stack in required_stacks
        }
        bench_sufficient = all(count > 0 for count in available_capacity.values())
        if not bench_sufficient:
            do_not_claim.append("Do not offer a capability whose current bench count is zero.")
        bench_match = BenchMatch(
            required_stacks=required_stacks,
            available_capacity=available_capacity,
            sufficient=bench_sufficient,
            recommendation=(
                "Bench match is sufficient for a scoped discovery conversation; quote capacity as available, not committed."
                if bench_sufficient
                else "Route staffing-specific questions to a human because at least one required stack has no visible capacity."
            ),
        )

        hiring_signal_brief = HiringSignalBrief(
            summary=(
                f"{brief_mode.title()} brief for {intake.company_name}: {sector} profile, about "
                f"{employee_estimate} employees, likely segment '{segment_label}'. "
                f"Matched {source_hits} source records across the current local enrichment snapshots."
            ),
            generated_at=utc_now_iso(),
            primary_segment=segment_label,
            segment_confidence=segment_confidence,
            recommended_pitch_angle=(
                "Lead with the strongest matched public signal first, then qualify gently where signals are still partial."
            ),
            ai_maturity_score=ai_maturity_score,
            ai_maturity_assessment=ai_maturity_assessment,
            ai_maturity_justification=ai_justification,
            bench_match=bench_match,
            confidence_by_signal=confidence_by_signal,
            signals=hiring_signals,
            do_not_claim=do_not_claim,
        )

        competitor_gap_brief = build_competitor_gap_brief(
            company_name=intake.company_name,
            company_domain=intake.company_domain,
            sector=sector,
            target_employee_count=employee_estimate,
            target_ai_assessment=ai_maturity_assessment,
        )

        return prospect, hiring_signal_brief, competitor_gap_brief


enrichment_service = EnrichmentService()
