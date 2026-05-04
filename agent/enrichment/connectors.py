import csv
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from agent.config import settings
from agent.schemas.tools import ToolExecutionResult, ToolStatus


def _normalize(value: str | None) -> str:
    return "".join(char for char in (value or "").lower() if char.isalnum())


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def _parse_rss_items(raw: str) -> list[dict]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []

    items: list[dict] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        observed_at = ""
        days_ago = ""
        if pub_date:
            try:
                dt = parsedate_to_datetime(pub_date)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_utc = dt.astimezone(timezone.utc)
                observed_at = dt_utc.isoformat()
                delta = datetime.now(timezone.utc) - dt_utc
                days_ago = str(max(0, int(delta.total_seconds() // 86_400)))
            except Exception:
                observed_at = ""
                days_ago = ""
        items.append(
            {
                "title": title,
                "link": link,
                "pub_date": pub_date,
                "observed_at": observed_at,
                "days_ago": days_ago,
            }
        )
    return items


def _guess_company_name(title: str) -> str:
    text = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
    patterns = [
        r"^(.*?)\s+(?:raises?|raised|secures?|funding|wins?)\b",
        r"^(.*?)\s+(?:lays?\s+off|to\s+lay\s+off|job\s+cuts?)\b",
        r"^(.*?)\s+(?:appoints?|hires?|names?)\b",
        r"^(.*?)\s+(?:ceo|cto|cfo|chief\s+[a-z]+\s+officer)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" :,-")
            if candidate:
                return candidate
    candidate = re.split(r"[:|]", text, maxsplit=1)[0].strip(" :,-")
    return candidate or text


def _domain_from_link(link: str) -> str:
    host = (urlparse(link).netloc or "").lower().strip()
    if host.startswith("www."):
        host = host[4:]
    blocked_hosts = {
        "news.google.com",
        "techcrunch.com",
        "www.techcrunch.com",
        "www.reuters.com",
        "reuters.com",
        "www.bloomberg.com",
        "bloomberg.com",
    }
    if host in blocked_hosts:
        return ""
    return host


def _extract_money_musd(text: str) -> int:
    match = re.search(r"\$?\s*(\d+(?:\.\d+)?)\s*([mb])\b", text, flags=re.IGNORECASE)
    if not match:
        return 0
    amount = float(match.group(1))
    unit = match.group(2).lower()
    if unit == "b":
        return int(amount * 1_000)
    return int(amount)


class BaseEnrichmentConnector:
    name = "connector"
    label = "Connector"
    snapshot_path: Path | None = None
    live_url: str = ""
    details = "Connector not configured."

    def status(self) -> ToolStatus:
        has_snapshot = bool(self.snapshot_path and self.snapshot_path.exists())
        has_live = bool(self.live_url)
        configured = has_snapshot or has_live
        if has_live:
            details = f"Uses live source {self.live_url} with snapshot fallback when available."
        elif has_snapshot:
            details = f"Uses local snapshot at {self.snapshot_path}."
        else:
            details = self.details
        return ToolStatus(
            name=self.name,
            label=self.label,
            mode="configured" if configured else "mock",
            configured=configured,
            available=True,
            details=details,
        )

    def _load_records(self) -> list[dict]:
        def _load_snapshot_records() -> list[dict]:
            if self.snapshot_path and self.snapshot_path.exists():
                with open(self.snapshot_path, encoding="utf-8") as handle:
                    return json.load(handle)
            return []

        if settings.enrichment_prefer_live_sources and self.live_url:
            try:
                with urlopen(self.live_url, timeout=20) as response:
                    raw = response.read().decode("utf-8")
                    return self._parse_live_payload(raw)
            except Exception:
                # Fall back to the local snapshot when live retrieval fails.
                return _load_snapshot_records()

        snapshot_rows = _load_snapshot_records()
        if snapshot_rows:
            return snapshot_rows

        if self.live_url:
            with urlopen(self.live_url, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return self._parse_live_payload(raw)
        return []

    def load_records(self) -> list[dict]:
        try:
            return self._load_records()
        except Exception:
            return []

    def _parse_live_payload(self, raw: str) -> list[dict]:
        return json.loads(raw)

    def lookup(self, company_name: str, company_domain: str | None) -> dict | None:
        records = self._load_records()
        normalized_domain = _normalize(company_domain)
        normalized_name = _normalize(company_name)
        for record in records:
            if normalized_domain and _normalize(record.get("domain")) == normalized_domain:
                return record
        for record in records:
            if _normalize(record.get("company_name")) == normalized_name:
                return record
        return None

    def run(self, prospect_id: str, matched: bool) -> ToolExecutionResult:
        status = self.status()
        return ToolExecutionResult(
            name=self.name,
            mode=status.mode,
            status="executed" if matched and status.configured else "previewed",
            message=(
                f"{self.label} contributed a matched source record."
                if matched and status.configured
                else f"{self.label} has no direct match for this prospect yet."
            ),
            artifact_ref=f"prospect:{prospect_id}",
        )


class CrunchbaseConnector(BaseEnrichmentConnector):
    name = "crunchbase"
    label = "Crunchbase ODM"
    snapshot_path = settings.crunchbase_snapshot_path
    live_url = settings.crunchbase_live_url
    details = "Set CRUNCHBASE_SNAPSHOT_PATH to a JSON snapshot of company records."

    def _parse_live_payload(self, raw: str) -> list[dict]:
        try:
            payload = json.loads(raw)
            if isinstance(payload, list):
                records: list[dict] = []
                for row in payload:
                    if not isinstance(row, dict):
                        continue
                    records.append(
                        {
                            "company_name": row.get("company_name") or row.get("company") or row.get("name") or "",
                            "domain": row.get("domain") or row.get("website") or "",
                            "sector": row.get("sector") or row.get("industry") or "",
                            "employee_count": _safe_int(row.get("employee_count") or row.get("employees"), 0),
                            "funding_musd": _safe_int(row.get("funding_musd") or row.get("funding"), 0),
                            "funding_months_ago": _safe_int(row.get("funding_months_ago"), 999),
                            "location": row.get("location") or "",
                            "observed_at": row.get("observed_at") or "",
                        }
                    )
                return [r for r in records if r.get("company_name") or r.get("domain")]
            if isinstance(payload, dict):
                nested = payload.get("companies")
                if isinstance(nested, list):
                    return self._parse_live_payload(json.dumps(nested))
        except json.JSONDecodeError:
            pass

        # RSS/news fallback for live funding signal extraction.
        records = []
        for item in _parse_rss_items(raw):
            title = item.get("title", "")
            if not re.search(r"\b(raise[sd]?|funding|series\s+[a-z]|seed\s+round)\b", title, re.IGNORECASE):
                continue
            records.append(
                {
                    "company_name": _guess_company_name(title),
                    "domain": _domain_from_link(item.get("link", "")),
                    "sector": "technology",
                    "employee_count": 0,
                    "funding_musd": _extract_money_musd(title),
                    "funding_months_ago": max(0, _safe_int(item.get("days_ago"), 999) // 30),
                    "location": "",
                    "observed_at": item.get("observed_at") or "",
                }
            )
        return [r for r in records if r.get("company_name")]


class LayoffsConnector(BaseEnrichmentConnector):
    name = "layoffs_fyi"
    label = "layoffs.fyi"
    snapshot_path = settings.layoffs_snapshot_path
    live_url = settings.layoffs_csv_url
    details = "Set LAYOFFS_SNAPSHOT_PATH or LAYOFFS_CSV_URL to use real layoff data."

    def _parse_live_payload(self, raw: str) -> list[dict]:
        rows = []
        reader = csv.DictReader(raw.splitlines())
        for row in reader:
            rows.append(
                {
                    "company_name": row.get("company") or row.get("Company"),
                    "domain": row.get("domain") or "",
                    "days_ago": row.get("days_ago") or row.get("daysAgo") or "",
                    "percent": row.get("percentage") or row.get("percent") or "",
                    "affected_employees": row.get("laid_off") or row.get("affected_employees") or "",
                }
            )
        if rows:
            return rows

        # RSS/news fallback for layoff signal extraction.
        for item in _parse_rss_items(raw):
            title = item.get("title", "")
            if not re.search(r"\b(layoff|layoffs|laid\s+off|job\s+cuts?)\b", title, re.IGNORECASE):
                continue
            percent_match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", title)
            affected_match = re.search(
                r"(\d{2,6})\s+(?:employees|workers|staff|jobs?)",
                title,
                flags=re.IGNORECASE,
            )
            rows.append(
                {
                    "company_name": _guess_company_name(title),
                    "domain": _domain_from_link(item.get("link", "")),
                    "days_ago": item.get("days_ago") or "",
                    "percent": percent_match.group(1) if percent_match else "",
                    "affected_employees": affected_match.group(1) if affected_match else "",
                    "observed_at": item.get("observed_at") or "",
                }
            )
        return rows


class JobPostsConnector(BaseEnrichmentConnector):
    name = "job_posts"
    label = "Public Job Posts"
    snapshot_path = settings.job_posts_snapshot_path
    live_url = settings.job_posts_live_url
    details = "Set JOB_POSTS_SNAPSHOT_PATH to a JSON snapshot of public job-post signals."

    def _parse_live_payload(self, raw: str) -> list[dict]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None

        # RemoteOK-style JSON array support.
        if isinstance(payload, list):
            by_company: dict[str, dict] = {}
            for row in payload:
                if not isinstance(row, dict):
                    continue
                company = str(row.get("company") or row.get("company_name") or "").strip()
                if not company:
                    continue
                key = _normalize(company)
                if not key:
                    continue
                rec = by_company.get(key)
                if rec is None:
                    rec = {
                        "company_name": company,
                        "domain": _domain_from_link(str(row.get("url") or row.get("apply_url") or "")),
                        "open_engineering_roles": 0,
                        "ai_roles": 0,
                        "growth_delta_60d_pct": 0,
                        "examples": [],
                    }
                    by_company[key] = rec
                rec["open_engineering_roles"] = int(rec["open_engineering_roles"]) + 1
                title = str(row.get("position") or row.get("title") or "").strip()
                if title:
                    rec["examples"] = [*rec["examples"], title][:6]
                tags = [str(tag).lower() for tag in (row.get("tags") or []) if isinstance(tag, str)]
                if any(tag in {"ai", "ml", "machine-learning", "llm", "data"} for tag in tags):
                    rec["ai_roles"] = int(rec["ai_roles"]) + 1
            return list(by_company.values())

        return super()._parse_live_payload(raw)


class LeadershipConnector(BaseEnrichmentConnector):
    name = "leadership"
    label = "Leadership Signal"
    snapshot_path = settings.leadership_snapshot_path
    live_url = settings.leadership_live_url
    details = "Set LEADERSHIP_SNAPSHOT_PATH to a JSON snapshot of leadership changes."

    def _parse_live_payload(self, raw: str) -> list[dict]:
        try:
            payload = json.loads(raw)
            if isinstance(payload, list):
                rows: list[dict] = []
                for row in payload:
                    if not isinstance(row, dict):
                        continue
                    company_name = str(
                        row.get("company_name") or row.get("company") or row.get("organization") or ""
                    ).strip()
                    if not company_name:
                        continue
                    rows.append(
                        {
                            "company_name": company_name,
                            "domain": row.get("domain") or row.get("website") or "",
                            "role": row.get("role") or row.get("title") or "",
                            "person": row.get("person") or row.get("contact_name") or row.get("name") or "",
                            "days_ago": _safe_int(row.get("days_ago"), 0),
                            "contact_email": row.get("contact_email") or row.get("email") or "",
                        }
                    )
                return rows
        except json.JSONDecodeError:
            pass

        # RSS/news fallback for leadership-hire signal extraction.
        rows = []
        for item in _parse_rss_items(raw):
            title = item.get("title", "")
            if not re.search(
                r"\b(appoints?|hires?|names?)\b.*\b(ceo|cto|cfo|coo|chief|vp|president)\b",
                title,
                re.IGNORECASE,
            ):
                continue
            role_match = re.search(
                r"\b(CEO|CTO|CFO|COO|President|Chief\s+[A-Za-z\s]+?Officer|VP\s+[A-Za-z\s]+)\b",
                title,
                re.IGNORECASE,
            )
            person_match = re.search(
                r"\b(?:appoints?|hires?|names?)\s+([A-Z][A-Za-z\-\.]+(?:\s+[A-Z][A-Za-z\-\.]+){0,2})",
                title,
            )
            rows.append(
                {
                    "company_name": _guess_company_name(title),
                    "domain": _domain_from_link(item.get("link", "")),
                    "role": role_match.group(1) if role_match else "leadership hire",
                    "person": person_match.group(1) if person_match else "",
                    "days_ago": item.get("days_ago") or "",
                    "contact_email": "",
                    "observed_at": item.get("observed_at") or "",
                }
            )
        return rows


crunchbase_connector = CrunchbaseConnector()
layoffs_connector = LayoffsConnector()
job_posts_connector = JobPostsConnector()
leadership_connector = LeadershipConnector()
