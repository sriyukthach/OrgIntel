"""
OrgIntel SQLite Database Management
Handles connection pooling, table schema creation, migrations, and transactions.
"""

import sqlite3
import aiosqlite
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from backend.app.config import settings


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- 1. Companies Master Table
CREATE TABLE IF NOT EXISTS companies (
    org_number TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    org_form TEXT,
    org_form_description TEXT,
    registration_status TEXT DEFAULT 'Active',
    is_active INTEGER DEFAULT 1,
    address TEXT,
    postal_code TEXT,
    city TEXT,
    municipality TEXT,
    municipality_number TEXT,
    country TEXT DEFAULT 'Norway',
    industry_code TEXT,
    industry_description TEXT,
    registration_date TEXT,
    founding_date TEXT,
    website TEXT,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    raw_identity_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Company Snapshots (for Historical Tracking & Change Detection)
CREATE TABLE IF NOT EXISTS company_snapshots (
    id TEXT PRIMARY KEY,
    org_number TEXT NOT NULL,
    snapshot_timestamp TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    FOREIGN KEY (org_number) REFERENCES companies(org_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshots_org_time ON company_snapshots(org_number, snapshot_timestamp DESC);

-- 3. Atomic Facts with Traceable Evidence
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    org_number TEXT NOT NULL,
    field TEXT NOT NULL,
    value TEXT NOT NULL,
    normalized_value TEXT,
    source_url TEXT NOT NULL,
    source_title TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    effective_date TEXT,
    reporting_period TEXT,
    confidence REAL NOT NULL,
    verification_status TEXT NOT NULL,
    evidence_excerpt TEXT NOT NULL,
    FOREIGN KEY (org_number) REFERENCES companies(org_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_facts_org_field ON facts(org_number, field);

-- 4. Evidence Repository
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    org_number TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_title TEXT NOT NULL,
    publisher_domain TEXT NOT NULL,
    retrieval_timestamp TEXT NOT NULL,
    publication_date TEXT,
    evidence_excerpt TEXT NOT NULL,
    supported_fields_json TEXT NOT NULL,
    source_priority INTEGER NOT NULL,
    content_hash TEXT,
    FOREIGN KEY (org_number) REFERENCES companies(org_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_evidence_org ON evidence(org_number);

-- 5. People / Leadership
CREATE TABLE IF NOT EXISTS people (
    id TEXT PRIMARY KEY,
    org_number TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    role_code TEXT,
    birth_year INTEGER,
    effective_date TEXT,
    source_url TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    evidence_excerpt TEXT,
    is_organization INTEGER DEFAULT 0,
    organization_number TEXT,
    FOREIGN KEY (org_number) REFERENCES companies(org_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_people_org ON people(org_number);

-- 6. Financial Records
CREATE TABLE IF NOT EXISTS financials (
    id TEXT PRIMARY KEY,
    org_number TEXT NOT NULL,
    reporting_year INTEGER NOT NULL,
    currency TEXT DEFAULT 'NOK',
    revenue REAL,
    operating_result REAL,
    profit_loss REAL,
    total_assets REAL,
    equity REAL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    evidence_excerpt TEXT,
    FOREIGN KEY (org_number) REFERENCES companies(org_number) ON DELETE CASCADE,
    UNIQUE(org_number, reporting_year)
);

CREATE INDEX IF NOT EXISTS idx_financials_org_year ON financials(org_number, reporting_year DESC);

-- 7. Activities & Announcements
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    org_number TEXT NOT NULL,
    title TEXT NOT NULL,
    date TEXT,
    summary TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    FOREIGN KEY (org_number) REFERENCES companies(org_number) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_activities_org ON activities(org_number);

-- 8. Research Runs Tracker
CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY,
    org_number TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    sources_attempted_json TEXT,
    sources_successful_json TEXT,
    facts_found INTEGER DEFAULT 0,
    facts_verified INTEGER DEFAULT 0,
    outbound_requests_count INTEGER DEFAULT 0,
    estimated_cost_usd REAL DEFAULT 0.0,
    latency_ms REAL DEFAULT 0.0,
    warnings_json TEXT,
    errors_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_org ON research_runs(org_number, started_at DESC);

-- 9. Public Source Cache (prevents duplicate requests & stays within 2000 limit)
CREATE TABLE IF NOT EXISTS source_cache (
    cache_key TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    response_body TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    headers_json TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cache_expires ON source_cache(expires_at);
"""


def init_sync_db():
    """Synchronously create database tables and run migrations."""
    settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.DATABASE_PATH))
    try:
        conn.executescript(SCHEMA_SQL)
        # Migrations for added columns if tables already exist
        try:
            conn.execute("ALTER TABLE people ADD COLUMN is_organization INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE people ADD COLUMN organization_number TEXT")
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


async def init_db():
    """Asynchronously initialize SQLite database and run migrations."""
    settings.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(settings.DATABASE_PATH)) as db:
        await db.executescript(SCHEMA_SQL)
        try:
            await db.execute("ALTER TABLE people ADD COLUMN is_organization INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE people ADD COLUMN organization_number TEXT")
        except Exception:
            pass
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide an async database connection context manager."""
    db = await aiosqlite.connect(str(settings.DATABASE_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON;")
    try:
        yield db
    finally:
        await db.close()
