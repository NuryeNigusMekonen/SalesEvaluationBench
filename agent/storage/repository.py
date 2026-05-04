import json
from datetime import datetime, timezone
from typing import Any

from agent.schemas.briefs import (
    CompetitorGapBrief,
    HiringSignalBrief,
    ProspectEnrichmentResponse,
)
from agent.schemas.conversation import ConversationDecision
from agent.schemas.prospect import ProspectRecord
from agent.schemas.tools import ToolchainReport
from agent.storage.database import get_connection, initialize_database


class ProspectRepository:
    def __init__(self) -> None:
        initialize_database()

    def save(self, prospect: ProspectRecord) -> ProspectRecord:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO prospects (
                    prospect_id,
                    company_name,
                    company_domain,
                    contact_name,
                    contact_email,
                    contact_phone,
                    source,
                    primary_segment,
                    primary_segment_label,
                    segment_confidence,
                    ai_maturity_score,
                    status,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prospect.prospect_id,
                    prospect.company_name,
                    prospect.company_domain,
                    prospect.contact_name,
                    prospect.contact_email,
                    prospect.contact_phone,
                    prospect.source,
                    prospect.primary_segment,
                    prospect.primary_segment_label,
                    prospect.segment_confidence,
                    prospect.ai_maturity_score,
                    prospect.status,
                    prospect.created_at.isoformat(),
                    prospect.updated_at.isoformat(),
                ),
            )
        return prospect

    def list_all(self) -> list[ProspectRecord]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    prospect_id,
                    company_name,
                    company_domain,
                    contact_name,
                    contact_email,
                    contact_phone,
                    source,
                    primary_segment,
                    primary_segment_label,
                    segment_confidence,
                    ai_maturity_score,
                    status,
                    created_at,
                    updated_at
                FROM prospects
                ORDER BY created_at DESC
                """
            ).fetchall()

        return [ProspectRecord.model_validate(dict(row)) for row in rows]

    def count(self) -> int:
        with get_connection() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM prospects").fetchone()
        return int(row["count"])

    def list_active(self, limit: int = 200) -> list[ProspectRecord]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    prospect_id,
                    company_name,
                    company_domain,
                    contact_name,
                    contact_email,
                    contact_phone,
                    source,
                    primary_segment,
                    primary_segment_label,
                    segment_confidence,
                    ai_maturity_score,
                    status,
                    created_at,
                    updated_at
                FROM prospects
                WHERE status = 'active_qualified_tenacious_pass'
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [ProspectRecord.model_validate(dict(row)) for row in rows]

    def find_by_company(self, company_name: str, company_domain: str | None = None) -> ProspectRecord | None:
        with get_connection() as connection:
            if company_domain:
                row = connection.execute(
                    """
                    SELECT
                        prospect_id,
                        company_name,
                        company_domain,
                        contact_name,
                        contact_email,
                        contact_phone,
                        source,
                        primary_segment,
                        primary_segment_label,
                        segment_confidence,
                        ai_maturity_score,
                        status,
                        created_at,
                        updated_at
                    FROM prospects
                    WHERE lower(company_domain) = lower(?)
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (company_domain,),
                ).fetchone()
                if row:
                    return ProspectRecord.model_validate(dict(row))

            row = connection.execute(
                """
                SELECT
                    prospect_id,
                    company_name,
                    company_domain,
                    contact_name,
                    contact_email,
                    contact_phone,
                    source,
                    primary_segment,
                    primary_segment_label,
                    segment_confidence,
                    ai_maturity_score,
                    status,
                    created_at,
                    updated_at
                FROM prospects
                WHERE lower(company_name) = lower(?)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (company_name,),
            ).fetchone()
        return ProspectRecord.model_validate(dict(row)) if row else None

    def save_source_signal_record(
        self,
        *,
        company_key: str,
        company_name: str,
        company_domain: str | None,
        source_name: str,
        observed_at: str | None,
        collected_at: str,
        raw_payload_json: str,
        normalized_payload_json: str,
    ) -> None:
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO source_signal_records (
                    company_key,
                    company_name,
                    company_domain,
                    source_name,
                    observed_at,
                    collected_at,
                    raw_payload_json,
                    normalized_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_key,
                    company_name,
                    company_domain,
                    source_name,
                    observed_at,
                    collected_at,
                    raw_payload_json,
                    normalized_payload_json,
                ),
            )

    def save_lead_qualification_record(
        self,
        *,
        prospect_id: str,
        company_key: str,
        company_name: str,
        company_domain: str | None,
        source_hit_count: int,
        qualification_score: float,
        qualification_status: str,
        qualification_reason: str,
        judge_reason: str,
        governance_decision: str,
    ) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO lead_qualification_records (
                    prospect_id,
                    company_key,
                    company_name,
                    company_domain,
                    source_hit_count,
                    qualification_score,
                    qualification_status,
                    qualification_reason,
                    judge_reason,
                    governance_decision,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prospect_id,
                    company_key,
                    company_name,
                    company_domain,
                    source_hit_count,
                    qualification_score,
                    qualification_status,
                    qualification_reason,
                    judge_reason,
                    governance_decision,
                    updated_at,
                ),
            )

    def qualification_map(self) -> dict[str, dict[str, Any]]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    prospect_id,
                    company_key,
                    company_name,
                    company_domain,
                    source_hit_count,
                    qualification_score,
                    qualification_status,
                    qualification_reason,
                    judge_reason,
                    governance_decision,
                    updated_at
                FROM lead_qualification_records
                """
            ).fetchall()
        return {
            str(row["prospect_id"]): {
                "company_key": row["company_key"],
                "company_name": row["company_name"],
                "company_domain": row["company_domain"],
                "source_hit_count": int(row["source_hit_count"] or 0),
                "qualification_score": float(row["qualification_score"] or 0),
                "qualification_status": row["qualification_status"],
                "qualification_reason": row["qualification_reason"],
                "judge_reason": row["judge_reason"],
                "governance_decision": row["governance_decision"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        }

    def add_correction_history(
        self,
        *,
        prospect_id: str | None,
        source: str,
        category: str,
        recommendation: str,
        trigger: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO correction_history_records (
                    prospect_id,
                    source,
                    category,
                    trigger,
                    recommendation,
                    metadata_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prospect_id,
                    source,
                    category,
                    trigger,
                    recommendation,
                    json.dumps(metadata or {}),
                    created_at,
                ),
            )

    def list_correction_history(
        self,
        *,
        prospect_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        with get_connection() as connection:
            if prospect_id:
                rows = connection.execute(
                    """
                    SELECT
                        correction_id,
                        prospect_id,
                        source,
                        category,
                        trigger,
                        recommendation,
                        metadata_json,
                        created_at
                    FROM correction_history_records
                    WHERE prospect_id = ?
                    ORDER BY correction_id DESC
                    LIMIT ?
                    """,
                    (prospect_id, limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        correction_id,
                        prospect_id,
                        source,
                        category,
                        trigger,
                        recommendation,
                        metadata_json,
                        created_at
                    FROM correction_history_records
                    ORDER BY correction_id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [
            {
                "correction_id": int(row["correction_id"]),
                "prospect_id": row["prospect_id"],
                "source": row["source"],
                "category": row["category"],
                "trigger": row["trigger"],
                "recommendation": row["recommendation"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def recent_recommendation_memory(self, prospect_id: str, limit: int = 6) -> list[str]:
        rows = self.list_correction_history(prospect_id=prospect_id, limit=limit * 3)
        seen: set[str] = set()
        memory: list[str] = []
        for row in rows:
            rec = str(row.get("recommendation") or "").strip()
            if not rec or rec in seen:
                continue
            memory.append(rec)
            seen.add(rec)
            if len(memory) >= limit:
                break
        return memory

    def recent_global_recommendation_memory(
        self,
        *,
        limit: int = 6,
        min_occurrences: int = 1,
        exclude_prospect_id: str | None = None,
        sources: list[str] | None = None,
    ) -> list[str]:
        bounded_limit = max(1, limit)
        bounded_min_occurrences = max(1, min_occurrences)

        where_clauses = ["trim(recommendation) <> ''"]
        parameters: list[object] = []

        if exclude_prospect_id:
            where_clauses.append("(prospect_id IS NULL OR prospect_id <> ?)")
            parameters.append(exclude_prospect_id)

        if sources:
            placeholders = ", ".join("?" for _ in sources)
            where_clauses.append(f"source IN ({placeholders})")
            parameters.extend(sources)

        query = f"""
            SELECT
                recommendation,
                COUNT(*) AS seen_count,
                MAX(correction_id) AS latest_correction_id
            FROM correction_history_records
            WHERE {' AND '.join(where_clauses)}
            GROUP BY recommendation
            HAVING COUNT(*) >= ?
            ORDER BY latest_correction_id DESC
            LIMIT ?
        """
        parameters.extend((bounded_min_occurrences, bounded_limit))

        with get_connection() as connection:
            rows = connection.execute(query, tuple(parameters)).fetchall()

        memory: list[str] = []
        for row in rows:
            recommendation = str(row["recommendation"] or "").strip()
            if recommendation:
                memory.append(recommendation)
        return memory

    def recent_recommendation_memory_blended(
        self,
        *,
        prospect_id: str | None,
        limit: int = 6,
        local_limit: int = 6,
        global_limit: int = 6,
        global_min_occurrences: int = 1,
        global_sources: list[str] | None = None,
    ) -> list[str]:
        bounded_limit = max(1, limit)

        local_memory = (
            self.recent_recommendation_memory(prospect_id, limit=max(1, local_limit))
            if prospect_id
            else []
        )
        global_memory = self.recent_global_recommendation_memory(
            limit=max(1, global_limit),
            min_occurrences=global_min_occurrences,
            exclude_prospect_id=prospect_id,
            sources=global_sources,
        )

        blended: list[str] = []
        seen: set[str] = set()
        for recommendation in [*local_memory, *global_memory]:
            normalized = recommendation.strip()
            if not normalized or normalized in seen:
                continue
            blended.append(normalized)
            seen.add(normalized)
            if len(blended) >= bounded_limit:
                break
        return blended

    def update_status(self, prospect_id: str, status: str) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        with get_connection() as connection:
            connection.execute(
                """
                UPDATE prospects
                SET status = ?, updated_at = ?
                WHERE prospect_id = ?
                """,
                (status, updated_at, prospect_id),
            )

    def record_interaction_event(
        self,
        prospect_id: str,
        event_type: str,
        *,
        channel: str | None = None,
        provider: str | None = None,
        payload: dict | None = None,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT INTO interaction_events (
                    prospect_id,
                    event_type,
                    channel,
                    provider,
                    payload_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    prospect_id,
                    event_type,
                    channel,
                    provider,
                    json.dumps(payload or {}),
                    created_at,
                ),
            )

    def has_interaction_event(self, prospect_id: str, event_type: str) -> bool:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM interaction_events
                WHERE prospect_id = ? AND event_type = ?
                LIMIT 1
                """,
                (prospect_id, event_type),
            ).fetchone()
        return row is not None

    def list_interaction_events(self, prospect_id: str) -> list[dict]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT event_type, channel, provider, payload_json, created_at
                FROM interaction_events
                WHERE prospect_id = ?
                ORDER BY event_id ASC
                """,
                (prospect_id,),
            ).fetchall()
        return [
            {
                "event_type": row["event_type"],
                "channel": row["channel"],
                "provider": row["provider"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def save_snapshot(
        self,
        prospect: ProspectRecord,
        hiring_signal_brief: HiringSignalBrief,
        competitor_gap_brief: CompetitorGapBrief,
        initial_decision: ConversationDecision,
        trace_id: str,
        toolchain_report: ToolchainReport | None = None,
    ) -> ProspectEnrichmentResponse:
        self.save(prospect)
        updated_at = datetime.now(timezone.utc).isoformat()
        with get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO prospect_briefs (
                    prospect_id,
                    hiring_signal_brief_json,
                    competitor_gap_brief_json,
                    initial_decision_json,
                    trace_id,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    prospect.prospect_id,
                    json.dumps(hiring_signal_brief.model_dump(mode="json")),
                    json.dumps(competitor_gap_brief.model_dump(mode="json")),
                    json.dumps(initial_decision.model_dump(mode="json")),
                    trace_id,
                    updated_at,
                ),
            )
            if toolchain_report is not None:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO prospect_tool_runs (
                        prospect_id,
                        toolchain_report_json,
                        updated_at
                    ) VALUES (?, ?, ?)
                    """,
                    (
                        prospect.prospect_id,
                        json.dumps(toolchain_report.model_dump(mode="json")),
                        updated_at,
                    ),
                )

        return ProspectEnrichmentResponse(
            prospect=prospect,
            hiring_signal_brief=hiring_signal_brief,
            competitor_gap_brief=competitor_gap_brief,
            initial_decision=initial_decision,
            trace_id=trace_id,
            toolchain_report=toolchain_report,
        )

    def get_snapshot(self, prospect_id: str) -> ProspectEnrichmentResponse | None:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    p.prospect_id,
                    p.company_name,
                    p.company_domain,
                    p.contact_name,
                    p.contact_email,
                    p.contact_phone,
                    p.source,
                    p.primary_segment,
                    p.primary_segment_label,
                    p.segment_confidence,
                    p.ai_maturity_score,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    b.hiring_signal_brief_json,
                    b.competitor_gap_brief_json,
                    b.initial_decision_json,
                    b.trace_id,
                    tr.toolchain_report_json
                FROM prospects p
                JOIN prospect_briefs b ON b.prospect_id = p.prospect_id
                LEFT JOIN prospect_tool_runs tr ON tr.prospect_id = p.prospect_id
                WHERE p.prospect_id = ?
                """,
                (prospect_id,),
            ).fetchone()

        if row is None:
            return None
        return self._snapshot_from_row(row)

    def find_snapshot_by_contact(
        self,
        *,
        contact_email: str | None = None,
        contact_phone: str | None = None,
    ) -> ProspectEnrichmentResponse | None:
        if not contact_email and not contact_phone:
            return None
        where_clause = "p.contact_email = ?" if contact_email else "p.contact_phone = ?"
        value = contact_email or contact_phone
        with get_connection() as connection:
            row = connection.execute(
                f"""
                SELECT
                    p.prospect_id,
                    p.company_name,
                    p.company_domain,
                    p.contact_name,
                    p.contact_email,
                    p.contact_phone,
                    p.source,
                    p.primary_segment,
                    p.primary_segment_label,
                    p.segment_confidence,
                    p.ai_maturity_score,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    b.hiring_signal_brief_json,
                    b.competitor_gap_brief_json,
                    b.initial_decision_json,
                    b.trace_id,
                    tr.toolchain_report_json
                FROM prospects p
                JOIN prospect_briefs b ON b.prospect_id = p.prospect_id
                LEFT JOIN prospect_tool_runs tr ON tr.prospect_id = p.prospect_id
                WHERE {where_clause}
                ORDER BY b.updated_at DESC
                LIMIT 1
                """,
                (value,),
            ).fetchone()
        return self._snapshot_from_row(row) if row else None

    def list_recent_snapshots(self, limit: int = 6) -> list[ProspectEnrichmentResponse]:
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.prospect_id,
                    p.company_name,
                    p.company_domain,
                    p.contact_name,
                    p.contact_email,
                    p.contact_phone,
                    p.source,
                    p.primary_segment,
                    p.primary_segment_label,
                    p.segment_confidence,
                    p.ai_maturity_score,
                    p.status,
                    p.created_at,
                    p.updated_at,
                    b.hiring_signal_brief_json,
                    b.competitor_gap_brief_json,
                    b.initial_decision_json,
                    b.trace_id,
                    tr.toolchain_report_json
                FROM prospect_briefs b
                JOIN prospects p ON p.prospect_id = b.prospect_id
                LEFT JOIN prospect_tool_runs tr ON tr.prospect_id = p.prospect_id
                ORDER BY b.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [self._snapshot_from_row(row) for row in rows]

    def _snapshot_from_row(self, row) -> ProspectEnrichmentResponse:
        hiring_signal_payload = json.loads(row["hiring_signal_brief_json"])
        hiring_signal_payload.setdefault(
            "primary_segment",
            row["primary_segment_label"] or row["primary_segment"] or "Unknown",
        )
        hiring_signal_payload.setdefault(
            "segment_confidence",
            float(row["segment_confidence"] or 0),
        )
        hiring_signal_payload.setdefault(
            "bench_match",
            {
                "required_stacks": [],
                "available_capacity": {},
                "sufficient": True,
                "recommendation": "Legacy brief created before bench-match fields were added.",
            },
        )
        prospect = ProspectRecord.model_validate(
            {
                "prospect_id": row["prospect_id"],
                "company_name": row["company_name"],
                "company_domain": row["company_domain"],
                "contact_name": row["contact_name"],
                "contact_email": row["contact_email"],
                "contact_phone": row["contact_phone"],
                "source": row["source"],
                "primary_segment": row["primary_segment"],
                "primary_segment_label": row["primary_segment_label"],
                "segment_confidence": row["segment_confidence"],
                "ai_maturity_score": row["ai_maturity_score"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        return ProspectEnrichmentResponse(
            prospect=prospect,
            hiring_signal_brief=HiringSignalBrief.model_validate(hiring_signal_payload),
            competitor_gap_brief=CompetitorGapBrief.model_validate(
                json.loads(row["competitor_gap_brief_json"])
            ),
            initial_decision=ConversationDecision.model_validate(
                json.loads(row["initial_decision_json"])
            ),
            trace_id=row["trace_id"],
            toolchain_report=(
                ToolchainReport.model_validate(json.loads(row["toolchain_report_json"]))
                if row["toolchain_report_json"]
                else None
            ),
        )
