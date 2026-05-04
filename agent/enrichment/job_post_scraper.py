from datetime import datetime, timedelta, timezone
from importlib import import_module
import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

from agent.enrichment.common import build_source_ref, utc_now_iso
from agent.enrichment.connectors import job_posts_connector

PUBLIC_JOB_HOSTS = {
    "builtin.com",
    "wellfound.com",
    "linkedin.com",
}


def robots_allows_public_page(url: str, *, user_agent: str = "ConversionEngineBot") -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not host:
        return False
    robots_url = f"{parsed.scheme or 'https'}://{host}/robots.txt"
    parser = RobotFileParser()
    try:
        parser.set_url(robots_url)
        parser.read()
        return parser.can_fetch(user_agent, url)
    except Exception:
        # Fail closed for live scraping. Snapshot-backed enrichment can still proceed.
        return False


def is_public_job_page(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return any(host == allowed or host.endswith(f".{allowed}") for allowed in PUBLIC_JOB_HOSTS)


def scrape_public_job_pages_with_playwright(urls: list[str]) -> list[dict]:
    """
    Public-page-only scraper:
    - only visits BuiltIn, Wellfound, and LinkedIn public company job pages
    - never logs in, solves challenges, or accesses authenticated job data
    - checks robots.txt before navigation and skips blocked URLs
    """
    try:
        sync_api = import_module("playwright.sync_api")
    except Exception:
        return []

    collected: list[dict] = []
    try:
        with sync_api.sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            for url in urls:
                if not is_public_job_page(url):
                    continue
                if not robots_allows_public_page(url):
                    continue
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=15_000)
                    title = page.title()
                    collected.append(
                        {
                            "source_url": url,
                            "title": title,
                            "scraped_at": utc_now_iso(),
                        }
                    )
                except Exception:
                    continue
            browser.close()
    except Exception:
        # Fail safe so enrichment can continue on snapshot/live connector data.
        return []
    return collected


def _default_public_pages(company_name: str, company_domain: str | None) -> list[str]:
    slug = (company_domain or company_name).replace(".", "-")
    return [
        f"https://www.builtin.com/company/{slug}/jobs",
        f"https://wellfound.com/company/{slug}/jobs",
        f"https://www.linkedin.com/company/{slug}/jobs",
    ]


def _infer_open_roles_from_titles(scraped_pages: list[dict]) -> int:
    highest_count = 0
    for row in scraped_pages:
        title = str(row.get("title") or "")
        for match in re.findall(r"(\d+)\s+(?:open\s+)?jobs?", title, flags=re.IGNORECASE):
            highest_count = max(highest_count, int(match))
    return highest_count


def _playwright_source_refs(scraped_pages: list[dict]) -> list[dict]:
    refs: list[dict] = []
    for row in scraped_pages:
        source_url = str(row.get("source_url") or "").strip()
        if not source_url:
            continue
        refs.append(
            build_source_ref(
                source_name="public_job_pages_live",
                reference=source_url,
                note="Public company jobs page scraped via Playwright after robots.txt allow check.",
                observed_at=row.get("scraped_at"),
                source_type="public_page_scrape",
            )
        )
    return refs


def compute_60_day_job_velocity(postings: list[dict], *, as_of: datetime | None = None) -> dict[str, int]:
    anchor = as_of or datetime.now(timezone.utc)
    recent_start = anchor - timedelta(days=60)
    previous_start = anchor - timedelta(days=120)
    recent_count = 0
    previous_count = 0

    for posting in postings:
        published_at = posting.get("published_at")
        if not published_at:
            continue
        published_dt = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
        if published_dt >= recent_start:
            recent_count += 1
        elif published_dt >= previous_start:
            previous_count += 1

    if previous_count == 0:
        delta_pct = 0 if recent_count == 0 else 100
    else:
        delta_pct = round(((recent_count - previous_count) / previous_count) * 100)

    return {
        "current_window_count": recent_count,
        "previous_window_count": previous_count,
        "growth_delta_60d_pct": int(delta_pct),
    }


def build_job_post_signal(
    company_name: str,
    company_domain: str | None,
    *,
    prefer_browser_scrape: bool = False,
) -> dict:
    collected_at = utc_now_iso()
    record = job_posts_connector.lookup(company_name, company_domain)
    default_public_pages = _default_public_pages(company_name, company_domain)
    scraped_pages = (
        scrape_public_job_pages_with_playwright(default_public_pages)
        if prefer_browser_scrape
        else []
    )
    if not record:
        if scraped_pages:
            inferred_open_roles = _infer_open_roles_from_titles(scraped_pages)
            observed_at = max((row.get("scraped_at") for row in scraped_pages if row.get("scraped_at")), default=None)
            if inferred_open_roles > 0:
                summary = (
                    f"Playwright public-page scrape found job evidence and inferred about {inferred_open_roles} "
                    "open roles from visible page titles."
                )
                confidence = 0.62
                edge_case = None
            else:
                summary = (
                    "Playwright scraped public company job pages, but no explicit open-role count was readable "
                    "from page titles."
                )
                confidence = 0.49
                edge_case = "playwright_scrape_no_role_count"

            examples = [
                str(row.get("title") or "").strip()
                for row in scraped_pages
                if str(row.get("title") or "").strip()
            ][:3]
            return {
                "name": "job_post_velocity",
                "summary": summary,
                "confidence": confidence,
                "observed_at": observed_at,
                "collected_at": collected_at,
                "source_attribution": _playwright_source_refs(scraped_pages),
                "edge_case": edge_case,
                "open_engineering_roles": inferred_open_roles,
                "ai_roles": 0,
                "growth_delta_60d_pct": 0,
                "examples": examples,
                "matched": True,
            }

        return {
            "name": "job_post_velocity",
            "summary": "No public job-post record matched this company, so hiring velocity is treated as unknown.",
            "confidence": 0.24,
            "observed_at": None,
            "collected_at": collected_at,
            "source_attribution": [
                build_source_ref(
                    source_name="public_job_pages",
                    reference=company_domain or company_name,
                    note="No BuiltIn, Wellfound, or LinkedIn public-page snapshot matched the company.",
                    source_type="snapshot_lookup",
                )
            ],
            "edge_case": "missing_job_post_record",
            "open_engineering_roles": 0,
            "ai_roles": 0,
            "growth_delta_60d_pct": 0,
            "examples": [],
            "matched": False,
        }

    postings = record.get("postings") or []
    if postings:
        velocity = compute_60_day_job_velocity(postings)
        open_roles = velocity["current_window_count"]
        growth_delta_60d_pct = velocity["growth_delta_60d_pct"]
        observed_at = max((posting.get("published_at") for posting in postings if posting.get("published_at")), default=None)
    else:
        open_roles = int(record.get("open_engineering_roles") or 0)
        growth_delta_60d_pct = int(record.get("growth_delta_60d_pct") or 0)
        observed_at = record.get("observed_at")

    examples = record.get("examples") or []
    ai_roles = int(record.get("ai_roles") or 0)
    public_pages = record.get("source_pages") or default_public_pages
    source_refs = [
        build_source_ref(
            source_name="public_job_pages",
            reference=page,
            note="Public-page-only source eligible for Playwright scraping after robots.txt check.",
            observed_at=observed_at,
            source_type="public_page",
        )
        for page in public_pages
    ]

    if scraped_pages:
        source_refs.extend(_playwright_source_refs(scraped_pages))
        observed_at = max(
            [candidate for candidate in [
                observed_at,
                max((row.get("scraped_at") for row in scraped_pages if row.get("scraped_at")), default=None),
            ] if candidate],
            default=observed_at,
        )
        inferred_open_roles = _infer_open_roles_from_titles(scraped_pages)
        if inferred_open_roles > open_roles:
            open_roles = inferred_open_roles
            examples = [
                str(row.get("title") or "").strip()
                for row in scraped_pages
                if str(row.get("title") or "").strip()
            ][:3] or examples

    if open_roles == 0:
        summary = "Public job-page snapshot shows zero open engineering roles in the last 60-day window."
        confidence = 0.72
        edge_case = "zero_open_job_posts"
    else:
        summary = (
            f"Public job-page signal shows {open_roles} engineering openings with a {growth_delta_60d_pct}% "
            "change over the last 60 days."
        )
        confidence = 0.85
        edge_case = None

    return {
        "name": "job_post_velocity",
        "summary": summary,
        "confidence": confidence,
        "observed_at": observed_at,
        "collected_at": collected_at,
        "source_attribution": source_refs,
        "edge_case": edge_case,
        "open_engineering_roles": open_roles,
        "ai_roles": ai_roles,
        "growth_delta_60d_pct": growth_delta_60d_pct,
        "examples": examples,
        "matched": True,
    }
