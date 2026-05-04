import sqlite3

from agent.config import settings


def ensure_data_dir() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_data_dir()
    connection = sqlite3.connect(settings.database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    ensure_data_dir()
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS prospects (
                prospect_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                company_domain TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                source TEXT NOT NULL,
                primary_segment TEXT,
                primary_segment_label TEXT,
                segment_confidence REAL NOT NULL DEFAULT 0,
                ai_maturity_score INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS prospect_briefs (
                prospect_id TEXT PRIMARY KEY,
                hiring_signal_brief_json TEXT NOT NULL,
                competitor_gap_brief_json TEXT NOT NULL,
                initial_decision_json TEXT NOT NULL,
                trace_id TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (prospect_id) REFERENCES prospects (prospect_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS prospect_tool_runs (
                prospect_id TEXT PRIMARY KEY,
                toolchain_report_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (prospect_id) REFERENCES prospects (prospect_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS interaction_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                channel TEXT,
                provider TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (prospect_id) REFERENCES prospects (prospect_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_signal_records (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_key TEXT NOT NULL,
                company_name TEXT NOT NULL,
                company_domain TEXT,
                source_name TEXT NOT NULL,
                observed_at TEXT,
                collected_at TEXT NOT NULL,
                raw_payload_json TEXT NOT NULL,
                normalized_payload_json TEXT NOT NULL,
                UNIQUE(company_key, source_name)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lead_qualification_records (
                prospect_id TEXT PRIMARY KEY,
                company_key TEXT NOT NULL,
                company_name TEXT NOT NULL,
                company_domain TEXT,
                source_hit_count INTEGER NOT NULL DEFAULT 0,
                qualification_score REAL NOT NULL DEFAULT 0,
                qualification_status TEXT NOT NULL,
                qualification_reason TEXT,
                judge_reason TEXT,
                governance_decision TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (prospect_id) REFERENCES prospects (prospect_id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_source_signal_company
            ON source_signal_records(company_key)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qualification_status
            ON lead_qualification_records(qualification_status, updated_at)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS correction_history_records (
                correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id TEXT,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                trigger TEXT,
                recommendation TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (prospect_id) REFERENCES prospects (prospect_id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_correction_history_prospect
            ON correction_history_records(prospect_id, created_at)
            """
        )
        _ensure_column(connection, "prospects", "contact_phone", "TEXT")
        _ensure_column(connection, "prospects", "primary_segment_label", "TEXT")
        _ensure_column(connection, "prospects", "segment_confidence", "REAL NOT NULL DEFAULT 0")


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )
