"""DB接続・スキーマ・マイグレーション（database.pyの基盤部分）"""
from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from config import Config

logger = logging.getLogger(__name__)

# --- Database backend detection ---

_DATABASE_URL = os.getenv("DATABASE_URL", "")
_USE_PG = bool(_DATABASE_URL)

if _USE_PG:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
else:
    import sqlite3

# --- Connection Pool (PostgreSQL only) ---
_pg_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pg_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pg_pool
    if _pg_pool is None or _pg_pool.closed:
        _pg_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1, maxconn=5, dsn=_DATABASE_URL,
        )
        logger.info("PostgreSQL connection pool created (min=1, max=5)")
    return _pg_pool


class _DBWrapper:
    """Thin wrapper for SQLite/PostgreSQL connection compatibility.

    Provides a unified interface so that callers can use ``conn.execute(sql, params)``
    with ``?`` placeholders regardless of the backend.  For PostgreSQL the wrapper
    automatically converts ``?`` to ``%s``.
    """

    def __init__(self, raw_conn, is_pg: bool, pool=None):
        self._conn = raw_conn
        self.is_pg = is_pg
        self._pool = pool  # For returning connection to pool

    def execute(self, sql, params=None):
        if self.is_pg:
            sql = sql.replace("?", "%s")
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params)
            return cur
        return self._conn.execute(sql, params or ())

    def executescript(self, sql):
        if self.is_pg:
            cur = self._conn.cursor()
            cur.execute(sql)
            cur.close()
        else:
            self._conn.executescript(sql)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._pool is not None:
            self._pool.putconn(self._conn)
        else:
            self._conn.close()


def _ensure_db_dir():
    if not _USE_PG:
        Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    if _USE_PG:
        pool = _get_pg_pool()
        raw = pool.getconn()
        conn = _DBWrapper(raw, is_pg=True, pool=pool)
    else:
        _ensure_db_dir()
        raw = sqlite3.connect(str(Config.DB_PATH), timeout=30)
        raw.row_factory = sqlite3.Row
        raw.execute("PRAGMA journal_mode=WAL")
        raw.execute("PRAGMA foreign_keys=ON")
        conn = _DBWrapper(raw, is_pg=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- Schema definitions ---

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id              SERIAL PRIMARY KEY,
    gmail_message_id TEXT UNIQUE NOT NULL,
    subject         TEXT DEFAULT '',
    sender          TEXT DEFAULT '',
    received_at     TIMESTAMP,
    body_text       TEXT DEFAULT '',
    labels          TEXT DEFAULT '',
    is_processed    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_emails_processed
    ON emails(is_processed);

CREATE TABLE IF NOT EXISTS job_listings (
    id              SERIAL PRIMARY KEY,
    email_id        INTEGER NOT NULL REFERENCES emails(id),
    company_name    TEXT DEFAULT '',
    work_area       TEXT DEFAULT '',
    unit_price      TEXT DEFAULT '',
    unit_price_min  INTEGER,
    unit_price_max  INTEGER,
    required_skills TEXT DEFAULT '[]',
    project_details TEXT DEFAULT '',
    job_type        TEXT DEFAULT '',
    raw_extraction  TEXT DEFAULT '',
    confidence      REAL DEFAULT 0.0,
    start_month     TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_listings_company
    ON job_listings(company_name);
CREATE INDEX IF NOT EXISTS idx_listings_area
    ON job_listings(work_area);
CREATE INDEX IF NOT EXISTS idx_listings_price
    ON job_listings(unit_price_min, unit_price_max);
CREATE INDEX IF NOT EXISTS idx_listings_created
    ON job_listings(created_at);

CREATE TABLE IF NOT EXISTS skills (
    id              SERIAL PRIMARY KEY,
    listing_id      INTEGER NOT NULL REFERENCES job_listings(id),
    skill_name      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_skills_name
    ON skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_skills_listing
    ON skills(listing_id);

CREATE TABLE IF NOT EXISTS fetch_log (
    id              SERIAL PRIMARY KEY,
    started_at      TIMESTAMP DEFAULT NOW(),
    finished_at     TIMESTAMP,
    status          TEXT DEFAULT 'running',
    emails_fetched  INTEGER DEFAULT 0,
    emails_processed INTEGER DEFAULT 0,
    errors          TEXT DEFAULT '[]',
    query_used      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS engineers (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    experience_years INTEGER,
    current_price   INTEGER,
    desired_price_min INTEGER,
    desired_price_max INTEGER,
    status          TEXT DEFAULT '待機中',
    preferred_areas TEXT DEFAULT '',
    available_from  TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    processes       TEXT DEFAULT '',
    job_type_experience TEXT DEFAULT '',
    position_experience TEXT DEFAULT '',
    remote_preference TEXT DEFAULT '',
    career_desired_job_type TEXT DEFAULT '',
    career_desired_skills TEXT DEFAULT '',
    career_notes    TEXT DEFAULT '',
    birth_date      TEXT DEFAULT '',
    education       TEXT DEFAULT '',
    industry_experience TEXT DEFAULT '',
    skill_proficiency TEXT DEFAULT '{}',
    certifications  TEXT DEFAULT '',
    email           TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    name_kana       TEXT DEFAULT '',
    gender          TEXT DEFAULT '',
    hire_date       TEXT DEFAULT '',
    office_branch   TEXT DEFAULT '',
    department      TEXT DEFAULT '',
    fairgrit_user_id TEXT DEFAULT '',
    address         TEXT DEFAULT '',
    nearest_station TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS engineer_skills (
    id              SERIAL PRIMARY KEY,
    engineer_id     INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE,
    skill_name      TEXT NOT NULL,
    years           INTEGER
);

CREATE INDEX IF NOT EXISTS idx_eng_skills_name
    ON engineer_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_eng_skills_engineer
    ON engineer_skills(engineer_id);

CREATE TABLE IF NOT EXISTS engineer_careers (
    id              SERIAL PRIMARY KEY,
    engineer_id     INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE,
    company_name    TEXT NOT NULL DEFAULT '',
    job_title       TEXT NOT NULL DEFAULT '',
    period_start    TEXT DEFAULT '',
    period_end      TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_engineer_careers_engineer_id
    ON engineer_careers(engineer_id);

CREATE TABLE IF NOT EXISTS engineer_assignments (
    id              SERIAL PRIMARY KEY,
    engineer_id     INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE,
    listing_id      INTEGER REFERENCES job_listings(id) ON DELETE SET NULL,
    company_name    TEXT DEFAULT '',
    project_name    TEXT DEFAULT '',
    start_date      TEXT DEFAULT '',
    end_date        TEXT DEFAULT '',
    unit_price      INTEGER,
    status          TEXT DEFAULT '稼働中',
    notes           TEXT DEFAULT '',
    contract_type   TEXT DEFAULT '',
    sales_person    TEXT DEFAULT '',
    client_company_name TEXT DEFAULT '',
    monthly_rate    INTEGER,
    work_hours_lower REAL,
    work_hours_upper REAL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eng_assignments_engineer
    ON engineer_assignments(engineer_id);

CREATE TABLE IF NOT EXISTS user_profiles (
    id              TEXT PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    role            TEXT NOT NULL DEFAULT 'engineer',
    engineer_id     INTEGER REFERENCES engineers(id) ON DELETE SET NULL,
    display_name    TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_email
    ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role
    ON user_profiles(role);

CREATE TABLE IF NOT EXISTS companies (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    name_kana       TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    url             TEXT DEFAULT '',
    prefecture      TEXT DEFAULT '',
    tags            TEXT DEFAULT '',
    contact_name    TEXT DEFAULT '',
    contact_email   TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_name
    ON companies(name);

CREATE TABLE IF NOT EXISTS matching_proposals (
    id              SERIAL PRIMARY KEY,
    engineer_id     INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE,
    listing_id      INTEGER NOT NULL REFERENCES job_listings(id) ON DELETE CASCADE,
    score           INTEGER DEFAULT 0,
    status          TEXT DEFAULT '候補',
    notes           TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(engineer_id, listing_id)
);

CREATE INDEX IF NOT EXISTS idx_proposals_engineer
    ON matching_proposals(engineer_id);
CREATE INDEX IF NOT EXISTS idx_proposals_listing
    ON matching_proposals(listing_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status
    ON matching_proposals(status);

CREATE TABLE IF NOT EXISTS invite_logs (
    id              SERIAL PRIMARY KEY,
    user_id         TEXT NOT NULL,
    email           TEXT NOT NULL,
    invited_by      TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invite_logs_user_id
    ON invite_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_invite_logs_email
    ON invite_logs(email);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    description TEXT DEFAULT '',
    applied_at  TIMESTAMP DEFAULT NOW()
);
"""

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_message_id TEXT UNIQUE NOT NULL,
    subject         TEXT DEFAULT '',
    sender          TEXT DEFAULT '',
    received_at     TIMESTAMP,
    body_text       TEXT DEFAULT '',
    labels          TEXT DEFAULT '',
    is_processed    BOOLEAN DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_emails_processed
    ON emails(is_processed);

CREATE TABLE IF NOT EXISTS job_listings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id        INTEGER NOT NULL,
    company_name    TEXT DEFAULT '',
    work_area       TEXT DEFAULT '',
    unit_price      TEXT DEFAULT '',
    unit_price_min  INTEGER,
    unit_price_max  INTEGER,
    required_skills TEXT DEFAULT '[]',
    project_details TEXT DEFAULT '',
    job_type        TEXT DEFAULT '',
    raw_extraction  TEXT DEFAULT '',
    confidence      REAL DEFAULT 0.0,
    start_month     TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id)
);

CREATE INDEX IF NOT EXISTS idx_listings_company
    ON job_listings(company_name);
CREATE INDEX IF NOT EXISTS idx_listings_area
    ON job_listings(work_area);
CREATE INDEX IF NOT EXISTS idx_listings_price
    ON job_listings(unit_price_min, unit_price_max);
CREATE INDEX IF NOT EXISTS idx_listings_created
    ON job_listings(created_at);

CREATE TABLE IF NOT EXISTS skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id      INTEGER NOT NULL,
    skill_name      TEXT NOT NULL,
    FOREIGN KEY (listing_id) REFERENCES job_listings(id)
);

CREATE INDEX IF NOT EXISTS idx_skills_name
    ON skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_skills_listing
    ON skills(listing_id);

CREATE TABLE IF NOT EXISTS fetch_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at     TIMESTAMP,
    status          TEXT DEFAULT 'running',
    emails_fetched  INTEGER DEFAULT 0,
    emails_processed INTEGER DEFAULT 0,
    errors          TEXT DEFAULT '[]',
    query_used      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS engineers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    experience_years INTEGER,
    current_price   INTEGER,
    desired_price_min INTEGER,
    desired_price_max INTEGER,
    status          TEXT DEFAULT '待機中',
    preferred_areas TEXT DEFAULT '',
    available_from  TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    processes       TEXT DEFAULT '',
    job_type_experience TEXT DEFAULT '',
    position_experience TEXT DEFAULT '',
    remote_preference TEXT DEFAULT '',
    career_desired_job_type TEXT DEFAULT '',
    career_desired_skills TEXT DEFAULT '',
    career_notes    TEXT DEFAULT '',
    birth_date      TEXT DEFAULT '',
    education       TEXT DEFAULT '',
    industry_experience TEXT DEFAULT '',
    skill_proficiency TEXT DEFAULT '{}',
    certifications  TEXT DEFAULT '',
    email           TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    name_kana       TEXT DEFAULT '',
    gender          TEXT DEFAULT '',
    hire_date       TEXT DEFAULT '',
    office_branch   TEXT DEFAULT '',
    department      TEXT DEFAULT '',
    fairgrit_user_id TEXT DEFAULT '',
    address         TEXT DEFAULT '',
    nearest_station TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS engineer_skills (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engineer_id     INTEGER NOT NULL,
    skill_name      TEXT NOT NULL,
    years           INTEGER,
    FOREIGN KEY (engineer_id) REFERENCES engineers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_eng_skills_name
    ON engineer_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_eng_skills_engineer
    ON engineer_skills(engineer_id);

CREATE TABLE IF NOT EXISTS engineer_careers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engineer_id     INTEGER NOT NULL,
    company_name    TEXT NOT NULL DEFAULT '',
    job_title       TEXT NOT NULL DEFAULT '',
    period_start    TEXT DEFAULT '',
    period_end      TEXT DEFAULT '',
    description     TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (engineer_id) REFERENCES engineers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_engineer_careers_engineer_id
    ON engineer_careers(engineer_id);

CREATE TABLE IF NOT EXISTS engineer_assignments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engineer_id     INTEGER NOT NULL,
    listing_id      INTEGER,
    company_name    TEXT DEFAULT '',
    project_name    TEXT DEFAULT '',
    start_date      TEXT DEFAULT '',
    end_date        TEXT DEFAULT '',
    unit_price      INTEGER,
    status          TEXT DEFAULT '稼働中',
    notes           TEXT DEFAULT '',
    contract_type   TEXT DEFAULT '',
    sales_person    TEXT DEFAULT '',
    client_company_name TEXT DEFAULT '',
    monthly_rate    INTEGER,
    work_hours_lower REAL,
    work_hours_upper REAL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (engineer_id) REFERENCES engineers(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES job_listings(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_eng_assignments_engineer
    ON engineer_assignments(engineer_id);

CREATE TABLE IF NOT EXISTS user_profiles (
    id              TEXT PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    role            TEXT NOT NULL DEFAULT 'engineer',
    engineer_id     INTEGER,
    display_name    TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (engineer_id) REFERENCES engineers(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_email
    ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role
    ON user_profiles(role);

CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    name_kana       TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    url             TEXT DEFAULT '',
    prefecture      TEXT DEFAULT '',
    tags            TEXT DEFAULT '',
    contact_name    TEXT DEFAULT '',
    contact_email   TEXT DEFAULT '',
    notes           TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_name
    ON companies(name);

CREATE TABLE IF NOT EXISTS matching_proposals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    engineer_id     INTEGER NOT NULL,
    listing_id      INTEGER NOT NULL,
    score           INTEGER DEFAULT 0,
    status          TEXT DEFAULT '候補',
    notes           TEXT DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(engineer_id, listing_id),
    FOREIGN KEY (engineer_id) REFERENCES engineers(id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES job_listings(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_proposals_engineer
    ON matching_proposals(engineer_id);
CREATE INDEX IF NOT EXISTS idx_proposals_listing
    ON matching_proposals(listing_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status
    ON matching_proposals(status);

CREATE TABLE IF NOT EXISTS invite_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    email           TEXT NOT NULL,
    invited_by      TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    description TEXT DEFAULT '',
    applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


# --- Migration definitions ---

MIGRATIONS = [
    (1, "job_listings.start_month", "ALTER TABLE job_listings ADD COLUMN start_month TEXT DEFAULT ''"),
    (2, "job_listings.requirements", "ALTER TABLE job_listings ADD COLUMN requirements TEXT DEFAULT ''"),
    (3, "engineers.processes", "ALTER TABLE engineers ADD COLUMN processes TEXT DEFAULT ''"),
    (4, "engineers.job_type_experience", "ALTER TABLE engineers ADD COLUMN job_type_experience TEXT DEFAULT ''"),
    (5, "engineers.position_experience", "ALTER TABLE engineers ADD COLUMN position_experience TEXT DEFAULT ''"),
    (6, "engineers.remote_preference", "ALTER TABLE engineers ADD COLUMN remote_preference TEXT DEFAULT ''"),
    (7, "engineers.career_desired_job_type", "ALTER TABLE engineers ADD COLUMN career_desired_job_type TEXT DEFAULT ''"),
    (8, "engineers.career_desired_skills", "ALTER TABLE engineers ADD COLUMN career_desired_skills TEXT DEFAULT ''"),
    (9, "engineers.career_notes", "ALTER TABLE engineers ADD COLUMN career_notes TEXT DEFAULT ''"),
    (10, "engineers.birth_date", "ALTER TABLE engineers ADD COLUMN birth_date TEXT DEFAULT ''"),
    (11, "engineers.education", "ALTER TABLE engineers ADD COLUMN education TEXT DEFAULT ''"),
    (12, "engineers.industry_experience", "ALTER TABLE engineers ADD COLUMN industry_experience TEXT DEFAULT ''"),
    (13, "engineers.skill_proficiency", "ALTER TABLE engineers ADD COLUMN skill_proficiency TEXT DEFAULT '{}'"),
    (14, "engineers.certifications", "ALTER TABLE engineers ADD COLUMN certifications TEXT DEFAULT ''"),
    # --- Phase 1: 認証・権限 ---
    (15, "user_profiles", """CREATE TABLE IF NOT EXISTS user_profiles (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'engineer',
        engineer_id INTEGER REFERENCES engineers(id) ON DELETE SET NULL,
        display_name TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),
    (16, "idx_user_profiles_email", "CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email)"),
    (17, "idx_user_profiles_role", "CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles(role)"),
    # --- Phase 2: engineers拡張 ---
    (18, "engineers.email", "ALTER TABLE engineers ADD COLUMN email TEXT DEFAULT ''"),
    (19, "engineers.phone", "ALTER TABLE engineers ADD COLUMN phone TEXT DEFAULT ''"),
    (20, "engineers.name_kana", "ALTER TABLE engineers ADD COLUMN name_kana TEXT DEFAULT ''"),
    (21, "engineers.gender", "ALTER TABLE engineers ADD COLUMN gender TEXT DEFAULT ''"),
    (22, "engineers.hire_date", "ALTER TABLE engineers ADD COLUMN hire_date TEXT DEFAULT ''"),
    (23, "engineers.office_branch", "ALTER TABLE engineers ADD COLUMN office_branch TEXT DEFAULT ''"),
    (24, "engineers.department", "ALTER TABLE engineers ADD COLUMN department TEXT DEFAULT ''"),
    (25, "engineers.fairgrit_user_id", "ALTER TABLE engineers ADD COLUMN fairgrit_user_id TEXT DEFAULT ''"),
    (26, "engineers.address", "ALTER TABLE engineers ADD COLUMN address TEXT DEFAULT ''"),
    (27, "engineers.nearest_station", "ALTER TABLE engineers ADD COLUMN nearest_station TEXT DEFAULT ''"),
    # --- Phase 2: companiesテーブル ---
    (28, "companies", """CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        name_kana TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        url TEXT DEFAULT '',
        prefecture TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        contact_name TEXT DEFAULT '',
        contact_email TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),
    (29, "idx_companies_name", "CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name)"),
    # --- Phase 2: engineer_assignments拡張 ---
    (30, "engineer_assignments.contract_type", "ALTER TABLE engineer_assignments ADD COLUMN contract_type TEXT DEFAULT ''"),
    (31, "engineer_assignments.sales_person", "ALTER TABLE engineer_assignments ADD COLUMN sales_person TEXT DEFAULT ''"),
    (32, "engineer_assignments.client_company_name", "ALTER TABLE engineer_assignments ADD COLUMN client_company_name TEXT DEFAULT ''"),
    (33, "engineer_assignments.monthly_rate", "ALTER TABLE engineer_assignments ADD COLUMN monthly_rate INTEGER"),
    (34, "engineer_assignments.work_hours_lower", "ALTER TABLE engineer_assignments ADD COLUMN work_hours_lower REAL"),
    (35, "engineer_assignments.work_hours_upper", "ALTER TABLE engineer_assignments ADD COLUMN work_hours_upper REAL"),
    # --- Phase 3: 招待ログ ---
    (36, "invite_logs", """CREATE TABLE IF NOT EXISTS invite_logs (
        id INTEGER PRIMARY KEY,
        user_id TEXT NOT NULL,
        email TEXT NOT NULL,
        invited_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),
    (37, "idx_invite_logs_user_id", "CREATE INDEX IF NOT EXISTS idx_invite_logs_user_id ON invite_logs(user_id)"),
    (38, "idx_invite_logs_email", "CREATE INDEX IF NOT EXISTS idx_invite_logs_email ON invite_logs(email)"),
    # --- エンジニア自己登録: 職歴テーブル + スキル年数 ---
    (39, "engineer_careers", """CREATE TABLE IF NOT EXISTS engineer_careers (
        id SERIAL PRIMARY KEY,
        engineer_id INTEGER NOT NULL REFERENCES engineers(id) ON DELETE CASCADE,
        company_name TEXT NOT NULL DEFAULT '',
        job_title TEXT NOT NULL DEFAULT '',
        period_start TEXT DEFAULT '',
        period_end TEXT DEFAULT '',
        description TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""),
    (40, "idx_engineer_careers_engineer_id", "CREATE INDEX IF NOT EXISTS idx_engineer_careers_engineer_id ON engineer_careers(engineer_id)"),
    (41, "engineer_skills.years", "ALTER TABLE engineer_skills ADD COLUMN years INTEGER"),
]


def _run_migrations(conn):
    """バージョン管理方式のマイグレーション実行。適用済みはスキップ。"""
    cursor = conn.execute("SELECT COALESCE(MAX(version), 0) AS ver FROM schema_migrations")
    row = cursor.fetchone()
    current_version = row["ver"] if isinstance(row, dict) else row[0]

    pending = [(v, desc, sql) for v, desc, sql in MIGRATIONS if v > current_version]
    if not pending:
        logger.info("Schema up to date (version %d)", current_version)
        return

    for version, description, sql in pending:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception as e:
            conn.rollback()
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate column" in err_msg:
                pass
            else:
                logger.error("Migration v%d failed: %s — %s", version, description, e)
                raise
        conn.execute(
            "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
            (version, description),
        )
        conn.commit()
        logger.info("Applied migration v%d: %s", version, description)


def _safe_add_column(conn, table: str, column: str, col_type: str = "TEXT DEFAULT ''"):
    """カラム追加マイグレーション。既存カラムはスキップ、それ以外のエラーはログ+再送出。"""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        err_msg = str(e).lower()
        if "already exists" in err_msg or "duplicate column" in err_msg:
            pass
        else:
            logger.error("Migration failed: ALTER TABLE %s ADD COLUMN %s — %s", table, column, e)
            raise


def init_db():
    with get_connection() as conn:
        conn.executescript(_PG_SCHEMA if conn.is_pg else _SQLITE_SCHEMA)
        conn.commit()
        _run_migrations(conn)
