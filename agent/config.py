from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass(frozen=True)
class Settings:
    project_root: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = project_root / "agent" / "data"
    database_path: Path = data_dir / "conversion_engine.db"
    trace_path: Path = data_dir / "traces.jsonl"
    outbox_dir: Path = data_dir / "outbox"
    snapshots_dir: Path = data_dir / "snapshots"
    webhook_dir: Path = data_dir / "webhooks"
    seed_dir: Path = project_root / "docs" / "tenacious_sales_data" / "seed"
    bench_summary_path: Path = Path(
        os.getenv(
            "BENCH_SUMMARY_PATH",
            project_root / "docs" / "tenacious_sales_data" / "seed" / "bench_summary.json",
        )
    )
    icp_definition_path: Path = Path(
        os.getenv(
            "ICP_DEFINITION_PATH",
            project_root / "docs" / "tenacious_sales_data" / "seed" / "icp_definition.md",
        )
    )
    pricing_sheet_path: Path = Path(
        os.getenv(
            "PRICING_SHEET_PATH",
            project_root / "docs" / "tenacious_sales_data" / "seed" / "pricing_sheet.md",
        )
    )
    style_guide_path: Path = Path(
        os.getenv(
            "STYLE_GUIDE_PATH",
            project_root / "docs" / "tenacious_sales_data" / "seed" / "style_guide.md",
        )
    )
    case_studies_path: Path = Path(
        os.getenv(
            "CASE_STUDIES_PATH",
            project_root / "docs" / "tenacious_sales_data" / "seed" / "case_studies.md",
        )
    )
    email_sequences_dir: Path = Path(
        os.getenv(
            "EMAIL_SEQUENCES_DIR",
            project_root / "docs" / "tenacious_sales_data" / "seed" / "email_sequences",
        )
    )
    discovery_transcripts_dir: Path = Path(
        os.getenv(
            "DISCOVERY_TRANSCRIPTS_DIR",
            project_root / "docs" / "tenacious_sales_data" / "seed" / "discovery_transcripts",
        )
    )
    outbound_enabled: bool = os.getenv("OUTBOUND_ENABLED", "").lower() in {"1", "true", "yes"}
    app_base_url: str = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "")
    resend_webhook_secret: str = os.getenv("RESEND_WEBHOOK_SECRET", "")
    calcom_webhook_secret: str = os.getenv("CALCOM_WEBHOOK_SECRET", "")
    hubspot_webhook_secret: str = os.getenv("HUBSPOT_WEBHOOK_SECRET", "")
    crunchbase_snapshot_path: Path = Path(
        os.getenv("CRUNCHBASE_SNAPSHOT_PATH", data_dir / "snapshots" / "crunchbase_companies.json")
    )
    crunchbase_live_url: str = os.getenv("CRUNCHBASE_LIVE_URL", "")
    job_posts_snapshot_path: Path = Path(
        os.getenv("JOB_POSTS_SNAPSHOT_PATH", data_dir / "snapshots" / "job_posts.json")
    )
    job_posts_live_url: str = os.getenv("JOB_POSTS_LIVE_URL", "")
    layoffs_snapshot_path: Path = Path(
        os.getenv("LAYOFFS_SNAPSHOT_PATH", data_dir / "snapshots" / "layoffs.json")
    )
    leadership_snapshot_path: Path = Path(
        os.getenv("LEADERSHIP_SNAPSHOT_PATH", data_dir / "snapshots" / "leadership.json")
    )
    leadership_live_url: str = os.getenv("LEADERSHIP_LIVE_URL", "")
    layoffs_csv_url: str = os.getenv("LAYOFFS_CSV_URL", "")
    enrichment_prefer_live_sources: bool = os.getenv("ENRICHMENT_PREFER_LIVE_SOURCES", "").lower() in {
        "1",
        "true",
        "yes",
    }
    lead_min_source_hits: int = int(os.getenv("LEAD_MIN_SOURCE_HITS", "2"))
    lead_min_segment_confidence: float = float(os.getenv("LEAD_MIN_SEGMENT_CONFIDENCE", "0.65"))
    lead_require_tenacious_pass: bool = os.getenv("LEAD_REQUIRE_TENACIOUS_PASS", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    lead_auto_refresh_on_seed_query: bool = os.getenv("LEAD_AUTO_REFRESH_ON_SEED_QUERY", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    lead_refresh_use_playwright_job_scrape: bool = os.getenv(
        "LEAD_REFRESH_USE_PLAYWRIGHT_JOB_SCRAPE",
        "true",
    ).lower() in {
        "1",
        "true",
        "yes",
    }
    email_provider: str = os.getenv("EMAIL_PROVIDER", "mock")
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    resend_from_email: str = os.getenv("RESEND_FROM_EMAIL", "drafts@tenacious.local")
    resend_reply_to: str = os.getenv("RESEND_REPLY_TO", "")
    mailersend_api_key: str = os.getenv("MAILERSEND_API_KEY", "")
    mailersend_from_email: str = os.getenv("MAILERSEND_FROM_EMAIL", "drafts@tenacious.local")
    mailersend_from_name: str = os.getenv("MAILERSEND_FROM_NAME", "Tenacious")
    sms_provider: str = os.getenv("SMS_PROVIDER", "mock")
    africas_talking_username: str = os.getenv("AFRICASTALKING_USERNAME", "")
    africas_talking_api_key: str = os.getenv("AFRICASTALKING_API_KEY", "")
    africas_talking_sender_id: str = os.getenv("AFRICASTALKING_SENDER_ID", "")
    africas_talking_env: str = os.getenv("AFRICASTALKING_ENV", "production")
    voice_provider: str = os.getenv("VOICE_PROVIDER", "mock")
    shared_voice_rig_webhook_url: str = os.getenv("SHARED_VOICE_RIG_WEBHOOK_URL", "")
    shared_voice_rig_api_key: str = os.getenv("SHARED_VOICE_RIG_API_KEY", "")
    shared_voice_rig_keyword_prefix: str = os.getenv("SHARED_VOICE_RIG_KEYWORD_PREFIX", "")
    voice_webhook_secret: str = os.getenv("VOICE_WEBHOOK_SECRET", "")
    hubspot_access_token: str = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
    hubspot_base_url: str = os.getenv("HUBSPOT_BASE_URL", "https://api.hubapi.com")
    calcom_api_key: str = os.getenv("CALCOM_API_KEY", "")
    calcom_api_base: str = os.getenv("CALCOM_API_BASE", "https://api.cal.com")
    calcom_api_version: str = os.getenv("CALCOM_API_VERSION", "2026-02-25")
    calcom_event_type_id: str = os.getenv("CALCOM_EVENT_TYPE_ID", "")
    calcom_username: str = os.getenv("CALCOM_USERNAME", "")
    calcom_event_type_slug: str = os.getenv("CALCOM_EVENT_TYPE_SLUG", "discovery-call")
    calcom_default_timezone: str = os.getenv("CALCOM_DEFAULT_TIMEZONE", "UTC")
    langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    langfuse_host: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    langfuse_export_enabled: bool = os.getenv("LANGFUSE_EXPORT_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
    }
    tau2_bench_path: Path = Path(os.getenv("TAU2_BENCH_PATH", project_root / "eval" / "tau2-bench"))
    tenacious_judge_enabled: bool = os.getenv("TENACIOUS_JUDGE_ENABLED", "").lower() in {
        "1",
        "true",
        "yes",
    }
    tenacious_judge_adapter_path: Path = Path(
        os.getenv(
            "TENACIOUS_JUDGE_ADAPTER_PATH",
            project_root / "outputs" / "models" / "tenacious-judge-v02-simpo-lora",
        )
    )
    tenacious_judge_base_model: str = os.getenv(
        "TENACIOUS_JUDGE_BASE_MODEL",
        "Qwen/Qwen2.5-3B-Instruct",
    )
    tenacious_judge_max_new_tokens: int = int(os.getenv("TENACIOUS_JUDGE_MAX_NEW_TOKENS", "256"))
    tenacious_comparison_mode: bool = os.getenv("TENACIOUS_COMPARISON_MODE", "").lower() in {
        "1",
        "true",
        "yes",
    }
    tenacious_comparison_dry_run: bool = os.getenv(
        "TENACIOUS_COMPARISON_DRY_RUN",
        "true",
    ).lower() in {
        "1",
        "true",
        "yes",
    }


settings = Settings()
