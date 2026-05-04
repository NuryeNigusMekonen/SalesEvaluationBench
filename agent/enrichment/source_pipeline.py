from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from agent.enrichment.connectors import (
    crunchbase_connector,
    job_posts_connector,
    layoffs_connector,
    leadership_connector,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _norm_key(value: str | None) -> str:
    return "".join(ch for ch in (value or "").lower() if ch.isalnum())


def _norm_domain(value: str | None) -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    raw = raw.split("/", 1)[0]
    return raw


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _company_key(company_name: str, company_domain: str) -> str:
    if company_domain:
        return f"domain:{company_domain}"
    return f"name:{_norm_key(company_name)}"


class SourcePipelineService:
    """Collect and normalize company signals from the 4 enrichment sources."""

    SOURCE_ORDER = ("crunchbase", "job_posts", "layoffs_fyi", "leadership")

    def collect_normalized_signals(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (consolidated_companies, normalized_source_records)."""
        collected_at = _utc_now_iso()
        connectors = {
            "crunchbase": crunchbase_connector,
            "job_posts": job_posts_connector,
            "layoffs_fyi": layoffs_connector,
            "leadership": leadership_connector,
        }

        normalized_rows: list[dict[str, Any]] = []
        consolidated: dict[str, dict[str, Any]] = {}

        for source_name in self.SOURCE_ORDER:
            connector = connectors[source_name]
            try:
                records = connector._load_records()  # noqa: SLF001 - internal pipeline call
            except Exception:
                records = []

            for raw_record in records:
                normalized = self._normalize_record(source_name, raw_record, collected_at)
                if not normalized:
                    continue
                normalized_rows.append(normalized)
                self._merge_consolidated(consolidated, normalized)

        return list(consolidated.values()), normalized_rows

    def _normalize_record(
        self,
        source_name: str,
        raw_record: dict[str, Any],
        collected_at: str,
    ) -> dict[str, Any] | None:
        company_name = _norm_text(raw_record.get("company_name") or raw_record.get("company"))
        company_domain = _norm_domain(raw_record.get("domain"))
        if not company_name and not company_domain:
            return None
        if not company_name:
            company_name = company_domain

        normalized: dict[str, Any] = {
            "company_name": company_name,
            "company_domain": company_domain,
            "company_key": _company_key(company_name, company_domain),
            "source_name": source_name,
            "observed_at": raw_record.get("observed_at"),
            "collected_at": collected_at,
            "raw_payload_json": json.dumps(raw_record, ensure_ascii=False),
            "normalized_payload": {},
        }

        if source_name == "crunchbase":
            normalized["normalized_payload"] = {
                "sector": _norm_text(raw_record.get("sector")),
                "employee_count": _to_int(raw_record.get("employee_count"), 0),
                "funding_musd": _to_int(raw_record.get("funding_musd"), 0),
                "funding_months_ago": _to_int(raw_record.get("funding_months_ago"), 999),
                "location": _norm_text(raw_record.get("location")),
            }
        elif source_name == "job_posts":
            normalized["normalized_payload"] = {
                "open_engineering_roles": _to_int(raw_record.get("open_engineering_roles"), 0),
                "ai_roles": _to_int(raw_record.get("ai_roles"), 0),
                "growth_delta_60d_pct": _to_int(raw_record.get("growth_delta_60d_pct"), 0),
                "examples": raw_record.get("examples") or [],
            }
        elif source_name == "layoffs_fyi":
            normalized["normalized_payload"] = {
                "days_ago": _to_int(raw_record.get("days_ago"), 999),
                "percent": _to_int(raw_record.get("percent"), 0),
                "affected_employees": _to_int(raw_record.get("affected_employees"), 0),
            }
        elif source_name == "leadership":
            normalized["normalized_payload"] = {
                "role": _norm_text(raw_record.get("role")),
                "person": _norm_text(raw_record.get("person") or raw_record.get("contact_name")),
                "days_ago": _to_int(raw_record.get("days_ago"), 999),
                "contact_email": _norm_text(raw_record.get("contact_email")),
            }

        normalized["normalized_payload_json"] = json.dumps(normalized["normalized_payload"], ensure_ascii=False)
        return normalized

    def _merge_consolidated(self, consolidated: dict[str, dict[str, Any]], normalized: dict[str, Any]) -> None:
        key = normalized["company_key"]
        current = consolidated.get(key)
        payload = normalized["normalized_payload"]
        source_name = normalized["source_name"]

        if current is None:
            current = {
                "company_key": key,
                "company_name": normalized["company_name"],
                "company_domain": normalized["company_domain"],
                "source_hits": set(),
                "sector": "",
                "employee_count": 0,
                "funding_musd": 0,
                "funding_months_ago": 999,
                "open_engineering_roles": 0,
                "ai_roles": 0,
                "growth_delta_60d_pct": 0,
                "layoff_days_ago": 999,
                "layoff_percent": 0,
                "leadership_role": "",
                "leadership_person": "",
                "leadership_days_ago": 999,
                "contact_email": "",
            }
            consolidated[key] = current

        current["source_hits"].add(source_name)

        if source_name == "crunchbase":
            current["sector"] = payload.get("sector") or current["sector"]
            current["employee_count"] = payload.get("employee_count") or current["employee_count"]
            current["funding_musd"] = payload.get("funding_musd") or current["funding_musd"]
            current["funding_months_ago"] = min(current["funding_months_ago"], payload.get("funding_months_ago") or 999)
        elif source_name == "job_posts":
            current["open_engineering_roles"] = max(current["open_engineering_roles"], payload.get("open_engineering_roles") or 0)
            current["ai_roles"] = max(current["ai_roles"], payload.get("ai_roles") or 0)
            current["growth_delta_60d_pct"] = payload.get("growth_delta_60d_pct") or current["growth_delta_60d_pct"]
        elif source_name == "layoffs_fyi":
            current["layoff_days_ago"] = min(current["layoff_days_ago"], payload.get("days_ago") or 999)
            current["layoff_percent"] = max(current["layoff_percent"], payload.get("percent") or 0)
        elif source_name == "leadership":
            current["leadership_role"] = payload.get("role") or current["leadership_role"]
            current["leadership_person"] = payload.get("person") or current["leadership_person"]
            current["leadership_days_ago"] = min(current["leadership_days_ago"], payload.get("days_ago") or 999)
            current["contact_email"] = payload.get("contact_email") or current["contact_email"]

        current["source_hit_count"] = len(current["source_hits"])

    @staticmethod
    def source_coverage_score(source_hit_count: int) -> float:
        if source_hit_count >= 4:
            return 1.0
        if source_hit_count == 3:
            return 0.85
        if source_hit_count == 2:
            return 0.7
        if source_hit_count == 1:
            return 0.45
        return 0.0


source_pipeline_service = SourcePipelineService()
