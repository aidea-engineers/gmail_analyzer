from __future__ import annotations

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
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
else:
    import sqlite3


class _DBWrapper:
    """Thin wrapper for SQLite/PostgreSQL connection compatibility.

    Provides a unified interface so that callers can use ``conn.execute(sql, params)``
    with ``?`` placeholders regardless of the backend.  For PostgreSQL the wrapper
    automatically converts ``?`` to ``%s``.
    """

    def __init__(self, raw_conn, is_pg: bool):
        self._conn = raw_conn
        self.is_pg = is_pg

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
        self._conn.close()


def _ensure_db_dir():
    if not _USE_PG:
        Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    if _USE_PG:
        raw = psycopg2.connect(_DATABASE_URL)
        conn = _DBWrapper(raw, is_pg=True)
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
    skill_name      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eng_skills_name
    ON engineer_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_eng_skills_engineer
    ON engineer_skills(engineer_id);

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
    FOREIGN KEY (engineer_id) REFERENCES engineers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_eng_skills_name
    ON engineer_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_eng_skills_engineer
    ON engineer_skills(engineer_id);

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
]


def _run_migrations(conn):
    """バージョン管理方式のマイグレーション実行。適用済みはスキップ。"""
    cursor = conn.execute("SELECT COALESCE(MAX(version), 0) AS ver FROM schema_migrations")
    row = cursor.fetchone()
    # RealDictCursor(PG)はdictを返すので名前アクセス、SQLiteはインデックスも可
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
                pass  # 既存カラム — 成功扱い
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
        # 「既に存在する」系のエラーは無視（PG: "already exists", SQLite: "duplicate column"）
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


# --- Email CRUD ---

def insert_email(
    gmail_message_id: str,
    subject: str,
    sender: str,
    received_at: Optional[datetime],
    body_text: str,
    labels: str,
) -> Optional[int]:
    with get_connection() as conn:
        try:
            if conn.is_pg:
                cursor = conn.execute(
                    """INSERT INTO emails
                       (gmail_message_id, subject, sender, received_at, body_text, labels)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT (gmail_message_id) DO NOTHING
                       RETURNING id""",
                    (gmail_message_id, subject, sender, received_at, body_text, labels),
                )
                row = cursor.fetchone()
                return row["id"] if row else None
            else:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO emails
                       (gmail_message_id, subject, sender, received_at, body_text, labels)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (gmail_message_id, subject, sender, received_at, body_text, labels),
                )
                return cursor.lastrowid if cursor.rowcount > 0 else None
        except Exception:
            return None


def get_existing_gmail_ids(gmail_message_ids: list[str]) -> set[str]:
    """既にDBに存在するgmail_message_idのセットを返す"""
    if not gmail_message_ids:
        return set()
    with get_connection() as conn:
        # バッチサイズ100ずつで処理（SQLパラメータ数制限対策）
        existing = set()
        for i in range(0, len(gmail_message_ids), 100):
            batch = gmail_message_ids[i : i + 100]
            placeholders = ",".join("?" * len(batch))
            rows = conn.execute(
                f"SELECT gmail_message_id FROM emails WHERE gmail_message_id IN ({placeholders})",
                batch,
            ).fetchall()
            existing.update(r["gmail_message_id"] for r in rows)
        return existing


def get_unprocessed_emails(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM emails WHERE is_processed = ? ORDER BY id LIMIT ?",
            (False, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_email_processed(email_id: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE emails SET is_processed = ? WHERE id = ?", (True, email_id)
        )


# --- Job Listing CRUD ---

def check_duplicate_listing(
    company_name: str, work_area: str, unit_price: str, project_details: str,
    days: int = 14,
) -> bool:
    """同一案件が既に登録済みかチェックする（重複検出）"""
    if not company_name and not project_details:
        return False

    with get_connection() as conn:
        if conn.is_pg:
            date_condition = "jl.created_at > NOW() - INTERVAL '%s days'" % days
        else:
            date_condition = f"jl.created_at > datetime('now', '-{days} days')"

        conditions = ["1=1", date_condition]
        params = []

        if company_name:
            conditions.append("jl.company_name = ?")
            params.append(company_name)

        if unit_price:
            conditions.append("jl.unit_price = ?")
            params.append(unit_price)

        if work_area:
            conditions.append("jl.work_area = ?")
            params.append(work_area)

        where = " AND ".join(conditions)
        sql = f"""SELECT COUNT(*) as cnt FROM job_listings jl WHERE {where}"""
        row = conn.execute(sql, params).fetchone()
        count = row["cnt"]

        if count == 0:
            return False

        # company + price + area が一致するものが存在する場合、
        # project_details も類似しているか確認
        if project_details:
            sql2 = f"""SELECT project_details FROM job_listings jl WHERE {where}"""
            rows = conn.execute(sql2, params).fetchall()
            for r in rows:
                existing = r["project_details"] or ""
                # 短い方が長い方に含まれているか、または30文字以上一致するかチェック
                if existing and project_details:
                    shorter = min(existing, project_details, key=len)
                    longer = max(existing, project_details, key=len)
                    if shorter in longer:
                        return True
                    # 先頭30文字が一致すれば重複とみなす
                    if len(shorter) >= 30 and shorter[:30] == project_details[:30]:
                        return True
            return False

        return count > 0


def insert_job_listing(email_id: int, extraction: dict) -> Optional[int]:
    """案件をDBに挿入する。重複時はNoneを返す。"""
    company_name = extraction.get("company_name") or ""
    work_area = extraction.get("work_area") or ""
    unit_price = extraction.get("unit_price") or ""
    project_details = extraction.get("project_details") or ""

    # 重複チェック
    if check_duplicate_listing(company_name, work_area, unit_price, project_details):
        return None

    skills_list = extraction.get("required_skills", [])
    skills_json = json.dumps(skills_list, ensure_ascii=False)
    raw_json = json.dumps(extraction, ensure_ascii=False, default=str)

    with get_connection() as conn:
        sql = """INSERT INTO job_listings
                 (email_id, company_name, work_area, unit_price,
                  unit_price_min, unit_price_max, required_skills,
                  project_details, job_type, raw_extraction, confidence, start_month, requirements)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            email_id,
            company_name,
            work_area,
            unit_price,
            extraction.get("unit_price_min"),
            extraction.get("unit_price_max"),
            skills_json,
            project_details,
            extraction.get("job_type") or "",
            raw_json,
            extraction.get("confidence", 0.0),
            extraction.get("start_month") or "",
            extraction.get("requirements") or "",
        )

        if conn.is_pg:
            cursor = conn.execute(sql + " RETURNING id", params)
            listing_id = cursor.fetchone()["id"]
        else:
            cursor = conn.execute(sql, params)
            listing_id = cursor.lastrowid

        for skill in skills_list:
            conn.execute(
                "INSERT INTO skills (listing_id, skill_name) VALUES (?, ?)",
                (listing_id, skill.strip()),
            )

        return listing_id


def search_listings(
    keyword: str = "",
    keyword_mode: str = "and",
    skills: list[str] | None = None,
    areas: list[str] | None = None,
    job_types: list[str] | None = None,
    companies: list[str] | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    query = """
        SELECT DISTINCT jl.*, e.subject, e.sender, e.received_at
        FROM job_listings jl
        JOIN emails e ON jl.email_id = e.id
        LEFT JOIN skills s ON s.listing_id = jl.id
        WHERE 1=1
    """
    params = []

    if keyword:
        keywords = keyword.split()
        if len(keywords) <= 1:
            # 単一キーワード（従来通り）
            query += """ AND (
                jl.company_name LIKE ? OR jl.work_area LIKE ?
                OR jl.project_details LIKE ? OR jl.required_skills LIKE ?
                OR jl.requirements LIKE ? OR e.subject LIKE ?
            )"""
            like = f"%{keyword.strip()}%"
            params.extend([like] * 6)
        else:
            # 複数キーワード（AND/OR切替）
            connector = " AND " if keyword_mode == "and" else " OR "
            kw_clauses = []
            for kw in keywords:
                kw_clauses.append("""(
                    jl.company_name LIKE ? OR jl.work_area LIKE ?
                    OR jl.project_details LIKE ? OR jl.required_skills LIKE ?
                    OR jl.requirements LIKE ? OR e.subject LIKE ?
                )""")
                like = f"%{kw}%"
                params.extend([like] * 6)
            query += f" AND ({connector.join(kw_clauses)})"

    if skills:
        placeholders = ",".join("?" * len(skills))
        query += f" AND s.skill_name IN ({placeholders})"
        params.extend(skills)

    if areas:
        area_conditions = " OR ".join("jl.work_area LIKE ?" for _ in areas)
        query += f" AND ({area_conditions})"
        params.extend(f"%{a}%" for a in areas)

    if job_types:
        type_conditions = " OR ".join("jl.job_type LIKE ?" for _ in job_types)
        query += f" AND ({type_conditions})"
        params.extend(f"%{t}%" for t in job_types)

    if companies:
        company_conditions = " OR ".join("jl.company_name LIKE ?" for _ in companies)
        query += f" AND ({company_conditions})"
        params.extend(f"%{c}%" for c in companies)

    if price_min is not None:
        query += " AND jl.unit_price_max >= ?"
        params.append(price_min)

    if price_max is not None:
        query += " AND jl.unit_price_min <= ?"
        params.append(price_max)

    if date_from:
        query += " AND jl.created_at >= ?"
        params.append(date_from)

    if date_to:
        query += " AND jl.created_at <= ?"
        params.append(date_to)

    query += " ORDER BY jl.created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


# --- Dashboard Aggregation ---

def get_skill_counts(date_from: str = "", date_to: str = "") -> list[dict]:
    query = """
        SELECT s.skill_name, COUNT(*) as count
        FROM skills s
        JOIN job_listings jl ON s.listing_id = jl.id
        WHERE 1=1
    """
    params = []
    if date_from:
        query += " AND jl.created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND jl.created_at <= ?"
        params.append(date_to)
    query += " GROUP BY s.skill_name ORDER BY count DESC"

    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_price_distribution(date_from: str = "", date_to: str = "") -> list[dict]:
    query = """
        SELECT unit_price_min, unit_price_max, unit_price
        FROM job_listings
        WHERE unit_price_min IS NOT NULL
    """
    params = []
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to)

    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_area_counts(date_from: str = "", date_to: str = "") -> list[dict]:
    query = """
        SELECT work_area, COUNT(*) as count
        FROM job_listings
        WHERE work_area != ''
    """
    params = []
    if date_from:
        query += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND created_at <= ?"
        params.append(date_to)
    query += " GROUP BY work_area ORDER BY count DESC"

    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_trend_data(
    granularity: str = "daily", date_from: str = "", date_to: str = ""
) -> list[dict]:
    with get_connection() as conn:
        if conn.is_pg:
            if granularity == "weekly":
                date_expr = "to_char(created_at, 'IYYY-\"W\"IW')"
            else:
                date_expr = "to_char(created_at, 'YYYY-MM-DD')"
        else:
            if granularity == "weekly":
                date_expr = "strftime('%Y-W%W', created_at)"
            else:
                date_expr = "date(created_at)"

        query = f"""
            SELECT {date_expr} as period, COUNT(*) as count
            FROM job_listings
            WHERE 1=1
        """
        params = []
        if date_from:
            query += " AND created_at >= ?"
            params.append(date_from)
        if date_to:
            query += " AND created_at <= ?"
            params.append(date_to)
        query += f" GROUP BY {date_expr} ORDER BY period"

        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_total_stats(date_from: str = "", date_to: str = "") -> dict:
    base_where = "WHERE 1=1"
    params = []
    if date_from:
        base_where += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        base_where += " AND created_at <= ?"
        params.append(date_to)

    with get_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM job_listings {base_where}", params
        ).fetchone()["cnt"]

        avg_price = conn.execute(
            f"""SELECT AVG((COALESCE(unit_price_min,0) + COALESCE(unit_price_max,0)) / 2.0) as avg_price
                FROM job_listings {base_where} AND unit_price_min IS NOT NULL""",
            params,
        ).fetchone()["avg_price"]

        today = datetime.now().strftime("%Y-%m-%d")
        if conn.is_pg:
            today_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM job_listings WHERE created_at::date = ?",
                (today,),
            ).fetchone()["cnt"]
        else:
            today_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM job_listings WHERE date(created_at) = ?",
                (today,),
            ).fetchone()["cnt"]

        area_count = conn.execute(
            f"SELECT COUNT(DISTINCT work_area) as cnt FROM job_listings {base_where} AND work_area != ''",
            params,
        ).fetchone()["cnt"]

    return {
        "total": total,
        "avg_price": round(avg_price, 1) if avg_price else 0,
        "today_count": today_count,
        "area_count": area_count,
    }


def get_monthly_summary(months: int = 6) -> list[dict]:
    """月別の案件サマリーを返す（直近N月分）"""
    with get_connection() as conn:
        if conn.is_pg:
            month_expr = "to_char(created_at, 'YYYY-MM')"
        else:
            month_expr = "strftime('%Y-%m', created_at)"

        query = f"""
            SELECT
                {month_expr} as month,
                COUNT(*) as listing_count,
                AVG(
                    CASE WHEN unit_price_min IS NOT NULL AND unit_price_max IS NOT NULL
                         THEN (unit_price_min + unit_price_max) / 2.0
                         WHEN unit_price_min IS NOT NULL THEN unit_price_min
                         WHEN unit_price_max IS NOT NULL THEN unit_price_max
                         ELSE NULL END
                ) as avg_price,
                COUNT(DISTINCT CASE WHEN company_name != '' THEN company_name ELSE NULL END) as unique_companies
            FROM job_listings
            WHERE created_at IS NOT NULL
            GROUP BY {month_expr}
            ORDER BY month DESC
            LIMIT ?
        """
        rows = [dict(r) for r in conn.execute(query, (months,)).fetchall()]

        # 各月の最多エリアを取得
        for row in rows:
            area_query = f"""
                SELECT work_area, COUNT(*) as cnt
                FROM job_listings
                WHERE {month_expr} = ? AND work_area != ''
                GROUP BY work_area
                ORDER BY cnt DESC
                LIMIT 1
            """
            area_row = conn.execute(area_query, (row["month"],)).fetchone()
            row["top_area"] = dict(area_row)["work_area"] if area_row else ""
            if row["avg_price"] is not None:
                row["avg_price"] = round(float(row["avg_price"]), 1)

        # 古い順に並べ替え
        rows.reverse()
        return rows


def get_distinct_skills() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT skill_name FROM skills ORDER BY skill_name"
        ).fetchall()
        return [r["skill_name"] for r in rows]


def get_distinct_areas() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT work_area FROM job_listings WHERE work_area != '' ORDER BY work_area"
        ).fetchall()
        return [r["work_area"] for r in rows]


def get_distinct_job_types() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT job_type FROM job_listings WHERE job_type != '' ORDER BY job_type"
        ).fetchall()
        return [r["job_type"] for r in rows]


def get_distinct_companies() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT company_name FROM job_listings WHERE company_name != '' ORDER BY company_name"
        ).fetchall()
        return [r["company_name"] for r in rows]


# --- Fetch Log ---

def insert_fetch_log(query_used: str = "") -> int:
    with get_connection() as conn:
        sql = "INSERT INTO fetch_log (query_used) VALUES (?)"
        if conn.is_pg:
            cursor = conn.execute(sql + " RETURNING id", (query_used,))
            return cursor.fetchone()["id"]
        else:
            cursor = conn.execute(sql, (query_used,))
            return cursor.lastrowid


def update_fetch_log(
    log_id: int,
    status: str,
    emails_fetched: int = 0,
    emails_processed: int = 0,
    errors: list[str] | None = None,
):
    with get_connection() as conn:
        conn.execute(
            """UPDATE fetch_log
               SET finished_at = CURRENT_TIMESTAMP,
                   status = ?,
                   emails_fetched = ?,
                   emails_processed = ?,
                   errors = ?
               WHERE id = ?""",
            (
                status,
                emails_fetched,
                emails_processed,
                json.dumps(errors or [], ensure_ascii=False),
                log_id,
            ),
        )


def get_fetch_logs(limit: int = 10) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM fetch_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_listings_with_sender() -> list[dict]:
    """全案件とそのメール送信者を取得する（会社名修復用）"""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT jl.id, jl.company_name, e.sender
               FROM job_listings jl
               JOIN emails e ON jl.email_id = e.id"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_listings_with_sender_and_body() -> list[dict]:
    """全案件とそのメール送信者・本文を取得する（会社名修復v4用）"""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT jl.id, jl.company_name, e.sender, e.body_text
               FROM job_listings jl
               JOIN emails e ON jl.email_id = e.id"""
        ).fetchall()
        return [dict(r) for r in rows]


def batch_update_company_names(updates: list[tuple[str, int]]) -> int:
    """会社名を一括更新する。updates = [(new_name, listing_id), ...]"""
    if not updates:
        return 0
    with get_connection() as conn:
        for new_name, listing_id in updates:
            conn.execute(
                "UPDATE job_listings SET company_name = ? WHERE id = ?",
                (new_name, listing_id),
            )
        return len(updates)


def cleanup_stale_fetch_logs(stale_minutes: int = 10) -> int:
    """'running' のまま放置されたfetch_logを 'failed (stale)' に更新する"""
    with get_connection() as conn:
        if conn.is_pg:
            cursor = conn.execute(
                """UPDATE fetch_log
                   SET status = ?, finished_at = CURRENT_TIMESTAMP,
                       errors = ?
                   WHERE status = 'running'
                     AND started_at < NOW() - INTERVAL '1 minute' * ?""",
                (
                    "failed (stale)",
                    json.dumps(["サーバー再起動等により処理が中断されました"]),
                    stale_minutes,
                ),
            )
        else:
            cursor = conn.execute(
                """UPDATE fetch_log
                   SET status = ?, finished_at = CURRENT_TIMESTAMP,
                       errors = ?
                   WHERE status = 'running'
                     AND started_at < datetime('now', ? || ' minutes')""",
                (
                    "failed (stale)",
                    json.dumps(["サーバー再起動等により処理が中断されました"]),
                    f"-{stale_minutes}",
                ),
            )
        return cursor.rowcount


def clear_old_email_bodies(days: int = 7) -> int:
    """処理済みメールのうち、指定日数を超えた本文を空にする（容量節約）"""
    with get_connection() as conn:
        if conn.is_pg:
            cursor = conn.execute(
                """UPDATE emails
                   SET body_text = ''
                   WHERE is_processed = TRUE
                     AND body_text != ''
                     AND created_at < NOW() - INTERVAL '1 day' * ?""",
                (days,),
            )
        else:
            cursor = conn.execute(
                """UPDATE emails
                   SET body_text = ''
                   WHERE is_processed = TRUE
                     AND body_text != ''
                     AND created_at < datetime('now', ? || ' days')""",
                (f"-{days}",),
            )
        return cursor.rowcount


# --- Engineer CRUD ---

def insert_engineer(data: dict) -> int:
    """エンジニアを登録し、IDを返す。スキルも同時に挿入する。"""
    with get_connection() as conn:
        sql = """INSERT INTO engineers
                 (name, experience_years, current_price,
                  desired_price_min, desired_price_max,
                  status, preferred_areas, available_from, notes, processes,
                  job_type_experience, position_experience, remote_preference,
                  career_desired_job_type, career_desired_skills, career_notes,
                  birth_date, education, industry_experience,
                  skill_proficiency, certifications,
                  email, phone, name_kana, gender, hire_date,
                  office_branch, department, fairgrit_user_id,
                  address, nearest_station)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            data["name"],
            data.get("experience_years"),
            data.get("current_price"),
            data.get("desired_price_min"),
            data.get("desired_price_max"),
            data.get("status", "待機中"),
            data.get("preferred_areas", ""),
            data.get("available_from", ""),
            data.get("notes", ""),
            data.get("processes", ""),
            data.get("job_type_experience", ""),
            data.get("position_experience", ""),
            data.get("remote_preference", ""),
            data.get("career_desired_job_type", ""),
            data.get("career_desired_skills", ""),
            data.get("career_notes", ""),
            data.get("birth_date", ""),
            data.get("education", ""),
            data.get("industry_experience", ""),
            data.get("skill_proficiency", "{}"),
            data.get("certifications", ""),
            data.get("email", ""),
            data.get("phone", ""),
            data.get("name_kana", ""),
            data.get("gender", ""),
            data.get("hire_date", ""),
            data.get("office_branch", ""),
            data.get("department", ""),
            data.get("fairgrit_user_id", ""),
            data.get("address", ""),
            data.get("nearest_station", ""),
        )
        if conn.is_pg:
            cursor = conn.execute(sql + " RETURNING id", params)
            eng_id = cursor.fetchone()["id"]
        else:
            cursor = conn.execute(sql, params)
            eng_id = cursor.lastrowid

        for skill in data.get("skills", []):
            if skill.strip():
                conn.execute(
                    "INSERT INTO engineer_skills (engineer_id, skill_name) VALUES (?, ?)",
                    (eng_id, skill.strip()),
                )
        return eng_id


def update_engineer(eng_id: int, data: dict) -> bool:
    """エンジニア情報を更新する。スキルは全削除→再挿入。"""
    with get_connection() as conn:
        sets = []
        params = []
        field_map = {
            "name": "name", "experience_years": "experience_years",
            "current_price": "current_price",
            "desired_price_min": "desired_price_min",
            "desired_price_max": "desired_price_max",
            "status": "status", "preferred_areas": "preferred_areas",
            "available_from": "available_from", "notes": "notes",
            "processes": "processes",
            "job_type_experience": "job_type_experience",
            "position_experience": "position_experience",
            "remote_preference": "remote_preference",
            "career_desired_job_type": "career_desired_job_type",
            "career_desired_skills": "career_desired_skills",
            "career_notes": "career_notes",
            "birth_date": "birth_date",
            "education": "education",
            "industry_experience": "industry_experience",
            "skill_proficiency": "skill_proficiency",
            "certifications": "certifications",
            "email": "email",
            "phone": "phone",
            "name_kana": "name_kana",
            "gender": "gender",
            "hire_date": "hire_date",
            "office_branch": "office_branch",
            "department": "department",
            "fairgrit_user_id": "fairgrit_user_id",
            "address": "address",
            "nearest_station": "nearest_station",
        }
        for key, col in field_map.items():
            if key in data:
                sets.append(f"{col} = ?")
                params.append(data[key])

        if not sets:
            return False

        if conn.is_pg:
            sets.append("updated_at = NOW()")
        else:
            sets.append("updated_at = CURRENT_TIMESTAMP")

        params.append(eng_id)
        sql = f"UPDATE engineers SET {', '.join(sets)} WHERE id = ?"
        conn.execute(sql, params)

        # スキルが指定されていれば全削除→再挿入
        if "skills" in data:
            conn.execute(
                "DELETE FROM engineer_skills WHERE engineer_id = ?", (eng_id,)
            )
            for skill in data["skills"]:
                if skill.strip():
                    conn.execute(
                        "INSERT INTO engineer_skills (engineer_id, skill_name) VALUES (?, ?)",
                        (eng_id, skill.strip()),
                    )
        return True


def delete_engineer(eng_id: int) -> bool:
    """エンジニアを削除する（CASCADE でスキル・履歴も削除）。"""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM engineers WHERE id = ?", (eng_id,))
        return cursor.rowcount > 0


def get_engineer(eng_id: int) -> Optional[dict]:
    """エンジニア詳細をスキル+アサイン履歴付きで返す。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM engineers WHERE id = ?", (eng_id,)
        ).fetchone()
        if not row:
            return None
        eng = dict(row)

        skills = conn.execute(
            "SELECT skill_name FROM engineer_skills WHERE engineer_id = ? ORDER BY skill_name",
            (eng_id,),
        ).fetchall()
        eng["skills"] = [s["skill_name"] for s in skills]

        assignments = conn.execute(
            """SELECT ea.*, jl.work_area as listing_area
               FROM engineer_assignments ea
               LEFT JOIN job_listings jl ON ea.listing_id = jl.id
               WHERE ea.engineer_id = ?
               ORDER BY ea.start_date DESC""",
            (eng_id,),
        ).fetchall()
        eng["assignments"] = [dict(a) for a in assignments]

        return eng


def search_engineers(
    keyword: str = "",
    skills: list[str] | None = None,
    statuses: list[str] | None = None,
    areas: list[str] | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    job_types: list[str] | None = None,
    positions: list[str] | None = None,
    remote: list[str] | None = None,
) -> list[dict]:
    """エンジニアをフィルター検索する。"""
    query = """
        SELECT DISTINCT e.*
        FROM engineers e
        LEFT JOIN engineer_skills es ON es.engineer_id = e.id
        WHERE 1=1
    """
    params: list = []

    if keyword:
        query += " AND (e.name LIKE ? OR e.notes LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like])

    if skills:
        placeholders = ",".join("?" * len(skills))
        query += f" AND es.skill_name IN ({placeholders})"
        params.extend(skills)

    if statuses:
        placeholders = ",".join("?" * len(statuses))
        query += f" AND e.status IN ({placeholders})"
        params.extend(statuses)

    if areas:
        area_conditions = " OR ".join("e.preferred_areas LIKE ?" for _ in areas)
        query += f" AND ({area_conditions})"
        params.extend(f"%{a}%" for a in areas)

    if price_min is not None:
        query += " AND (e.desired_price_max >= ? OR e.current_price >= ?)"
        params.extend([price_min, price_min])

    if price_max is not None:
        query += " AND (e.desired_price_min <= ? OR e.current_price <= ?)"
        params.extend([price_max, price_max])

    if job_types:
        jt_conditions = " OR ".join("e.job_type_experience LIKE ?" for _ in job_types)
        query += f" AND ({jt_conditions})"
        params.extend(f"%{jt}%" for jt in job_types)

    if positions:
        pos_conditions = " OR ".join("e.position_experience LIKE ?" for _ in positions)
        query += f" AND ({pos_conditions})"
        params.extend(f"%{p}%" for p in positions)

    if remote:
        rem_conditions = " OR ".join("e.remote_preference LIKE ?" for _ in remote)
        query += f" AND ({rem_conditions})"
        params.extend(f"%{r}%" for r in remote)

    query += " ORDER BY e.updated_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        if not rows:
            return []

        results = [dict(row) for row in rows]
        eng_ids = [e["id"] for e in results]

        # 全エンジニアのスキルを1クエリで取得（N+1解消）
        placeholders = ",".join("?" * len(eng_ids))
        skill_rows = conn.execute(
            f"SELECT engineer_id, skill_name FROM engineer_skills WHERE engineer_id IN ({placeholders}) ORDER BY skill_name",
            eng_ids,
        ).fetchall()

        skills_map: dict[int, list[str]] = {e["id"]: [] for e in results}
        for s in skill_rows:
            skills_map[s["engineer_id"]].append(s["skill_name"])

        for eng in results:
            eng["skills"] = skills_map[eng["id"]]

        return results


def get_engineer_stats() -> dict:
    """エンジニアのステータス別統計を返す。"""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM engineers"
        ).fetchone()["cnt"]
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM engineers GROUP BY status"
        ).fetchall()
        by_status = {r["status"]: r["cnt"] for r in rows}
    return {
        "total": total,
        "waiting": by_status.get("待機中", 0),
        "active": by_status.get("稼働中", 0),
        "interview": by_status.get("面談中", 0),
        "inactive": by_status.get("休止中", 0),
    }


def get_distinct_engineer_skills() -> list[str]:
    """エンジニアに登録されたスキル一覧を返す。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT skill_name FROM engineer_skills ORDER BY skill_name"
        ).fetchall()
        return [r["skill_name"] for r in rows]


def get_distinct_engineer_areas() -> list[str]:
    """エンジニアに登録された希望エリア一覧を返す。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT preferred_areas FROM engineers WHERE preferred_areas != '' ORDER BY preferred_areas"
        ).fetchall()
        # カンマ区切りを展開してユニークにする
        areas = set()
        for r in rows:
            for a in r["preferred_areas"].split(","):
                a = a.strip()
                if a:
                    areas.add(a)
        return sorted(areas)


def insert_assignment(engineer_id: int, data: dict) -> int:
    """エンジニアのアサイン履歴を追加する。"""
    with get_connection() as conn:
        sql = """INSERT INTO engineer_assignments
                 (engineer_id, listing_id, company_name, project_name,
                  start_date, end_date, unit_price, status, notes,
                  contract_type, sales_person, client_company_name,
                  monthly_rate, work_hours_lower, work_hours_upper)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            engineer_id,
            data.get("listing_id"),
            data.get("company_name", ""),
            data.get("project_name", ""),
            data.get("start_date", ""),
            data.get("end_date", ""),
            data.get("unit_price"),
            data.get("status", "稼働中"),
            data.get("notes", ""),
            data.get("contract_type", ""),
            data.get("sales_person", ""),
            data.get("client_company_name", ""),
            data.get("monthly_rate"),
            data.get("work_hours_lower"),
            data.get("work_hours_upper"),
        )
        if conn.is_pg:
            cursor = conn.execute(sql + " RETURNING id", params)
            return cursor.fetchone()["id"]
        else:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid


def delete_assignment(assignment_id: int) -> bool:
    """アサイン履歴を削除する。"""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM engineer_assignments WHERE id = ?", (assignment_id,)
        )
        return cursor.rowcount > 0


# --- Matching ---

def _calc_match_score(engineer: dict, listing: dict) -> dict:
    """エンジニアと案件のマッチスコアを計算する（合計100点満点）。"""

    # --- スキルマッチ (0〜50点) ---
    listing_skills_raw = listing.get("required_skills") or "[]"
    if isinstance(listing_skills_raw, str):
        try:
            listing_skills = json.loads(listing_skills_raw)
        except (json.JSONDecodeError, TypeError):
            listing_skills = []
    else:
        listing_skills = listing_skills_raw

    eng_skills = set(engineer.get("skills") or [])
    listing_skill_set = set(listing_skills)

    if not listing_skill_set:
        skill_score = 25  # 中間値
    elif not eng_skills:
        skill_score = 0
    else:
        common = len(eng_skills & listing_skill_set)
        skill_score = round(common / len(listing_skill_set) * 50)

    # --- エリアマッチ (0〜25点) ---
    listing_area = (listing.get("work_area") or "").strip()
    eng_areas_raw = (engineer.get("preferred_areas") or "").strip()
    eng_areas = [a.strip() for a in eng_areas_raw.split(",") if a.strip()] if eng_areas_raw else []

    if not listing_area:
        area_score = 15  # 判定不能
    elif listing_area in eng_areas:
        area_score = 25
    elif "リモート" in listing_area or "フルリモート" in listing_area:
        area_score = 20
    elif not eng_areas:
        area_score = 15  # どこでもOK
    else:
        area_score = 0

    # --- 単価マッチ (0〜25点) ---
    l_min = listing.get("unit_price_min")
    l_max = listing.get("unit_price_max")
    e_min = engineer.get("desired_price_min") or engineer.get("current_price")
    e_max = engineer.get("desired_price_max") or engineer.get("current_price")

    if l_min is None and l_max is None:
        price_score = 15  # 案件側データなし
    elif e_min is None and e_max is None:
        price_score = 15  # エンジニア側データなし
    else:
        # 範囲の重なり判定
        r_min = l_min if l_min is not None else l_max
        r_max = l_max if l_max is not None else l_min
        e_lo = e_min if e_min is not None else e_max
        e_hi = e_max if e_max is not None else e_min
        if r_min <= e_hi and e_lo <= r_max:
            price_score = 25
        else:
            price_score = 0

    total = skill_score + area_score + price_score
    return {"skill": skill_score, "area": area_score, "price": price_score, "total": total}


def match_engineers_for_listing(listing_id: int, limit: int = 20) -> list[dict]:
    """案件に合うエンジニア一覧（待機中/面談中のみ、スコア降順）。"""
    with get_connection() as conn:
        listing_row = conn.execute(
            "SELECT * FROM job_listings WHERE id = ?", (listing_id,)
        ).fetchone()
        if not listing_row:
            return []
        listing = dict(listing_row)

        # 待機中・面談中のエンジニアを全件取得
        rows = conn.execute(
            "SELECT * FROM engineers WHERE status IN (?, ?)",
            ("待機中", "面談中"),
        ).fetchall()

        # 全エンジニアのスキルを一括取得
        eng_ids = [dict(r)["id"] for r in rows]
        skills_map: dict[int, list[str]] = {eid: [] for eid in eng_ids}
        if eng_ids:
            placeholders = ",".join("?" * len(eng_ids))
            sk_rows = conn.execute(
                f"SELECT engineer_id, skill_name FROM engineer_skills WHERE engineer_id IN ({placeholders})",
                eng_ids,
            ).fetchall()
            for sr in sk_rows:
                skills_map[sr["engineer_id"]].append(sr["skill_name"])

        # この案件に対する提案を一括取得
        prop_map: dict[int, dict] = {}
        prop_rows = conn.execute(
            "SELECT * FROM matching_proposals WHERE listing_id = ?",
            (listing_id,),
        ).fetchall()
        for pr in prop_rows:
            prop_map[pr["engineer_id"]] = dict(pr)

        results = []
        for row in rows:
            eng = dict(row)
            eng["skills"] = skills_map.get(eng["id"], [])
            score_detail = _calc_match_score(eng, listing)
            results.append({
                "engineer": eng,
                "score": score_detail["total"],
                "score_detail": {
                    "skill": score_detail["skill"],
                    "area": score_detail["area"],
                    "price": score_detail["price"],
                },
                "proposal": prop_map.get(eng["id"]),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


def match_listings_for_engineer(engineer_id: int, limit: int = 20) -> list[dict]:
    """エンジニアに合う案件一覧（直近30日、スコア降順）。"""
    with get_connection() as conn:
        eng_row = conn.execute(
            "SELECT * FROM engineers WHERE id = ?", (engineer_id,)
        ).fetchone()
        if not eng_row:
            return []
        eng = dict(eng_row)

        # スキルを付与
        sk = conn.execute(
            "SELECT skill_name FROM engineer_skills WHERE engineer_id = ?",
            (engineer_id,),
        ).fetchall()
        eng["skills"] = [s["skill_name"] for s in sk]

        # 直近30日の案件 — スコア計算に必要な列だけ取得（高速化）
        if _USE_PG:
            date_cond = "created_at > NOW() - INTERVAL '30 days'"
        else:
            date_cond = "created_at > datetime('now', '-30 days')"
        rows = conn.execute(
            f"""SELECT id, required_skills, work_area, unit_price_min, unit_price_max
                FROM job_listings WHERE {date_cond}"""
        ).fetchall()

        # Pythonでスコア計算（DBクエリなし）
        scored: list[tuple[int, dict]] = []
        for row in rows:
            listing_slim = dict(row)
            score_detail = _calc_match_score(eng, listing_slim)
            scored.append((listing_slim["id"], score_detail))

        # スコア上位のIDだけ取得
        scored.sort(key=lambda x: x[1]["total"], reverse=True)
        top = scored[:limit]
        if not top:
            return []

        top_ids = [t[0] for t in top]
        score_map = {t[0]: t[1] for t in top}

        # 上位案件のフルデータを一括取得
        placeholders = ",".join("?" * len(top_ids))
        full_rows = conn.execute(
            f"SELECT * FROM job_listings WHERE id IN ({placeholders})",
            top_ids,
        ).fetchall()
        listing_map = {dict(r)["id"]: dict(r) for r in full_rows}

        # 上位の提案を一括取得
        prop_map: dict[int, dict] = {}
        prop_rows = conn.execute(
            f"SELECT * FROM matching_proposals WHERE engineer_id = ? AND listing_id IN ({placeholders})",
            [engineer_id] + top_ids,
        ).fetchall()
        for pr in prop_rows:
            prop_map[pr["listing_id"]] = dict(pr)

        # スコア順で結果を組み立て
        results = []
        for lid, sd in top:
            listing = listing_map.get(lid)
            if not listing:
                continue
            results.append({
                "listing": listing,
                "score": sd["total"],
                "score_detail": {"skill": sd["skill"], "area": sd["area"], "price": sd["price"]},
                "proposal": prop_map.get(lid),
            })

        return results


def insert_proposal(engineer_id: int, listing_id: int, score: int = 0, notes: str = "") -> Optional[int]:
    """提案レコードを作成する（UNIQUE制約で重複防止）。"""
    with get_connection() as conn:
        try:
            if conn.is_pg:
                cursor = conn.execute(
                    """INSERT INTO matching_proposals (engineer_id, listing_id, score, notes)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT (engineer_id, listing_id) DO NOTHING
                       RETURNING id""",
                    (engineer_id, listing_id, score, notes),
                )
                row = cursor.fetchone()
                return row["id"] if row else None
            else:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO matching_proposals
                       (engineer_id, listing_id, score, notes)
                       VALUES (?, ?, ?, ?)""",
                    (engineer_id, listing_id, score, notes),
                )
                return cursor.lastrowid if cursor.rowcount > 0 else None
        except Exception:
            return None


def update_proposal_status(proposal_id: int, status: str, notes: Optional[str] = None) -> bool:
    """提案ステータスを変更する。"""
    with get_connection() as conn:
        if notes is not None:
            if conn.is_pg:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, notes = ?, updated_at = NOW() WHERE id = ?",
                    (status, notes, proposal_id),
                )
            else:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, notes, proposal_id),
                )
        else:
            if conn.is_pg:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, updated_at = NOW() WHERE id = ?",
                    (status, proposal_id),
                )
            else:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, proposal_id),
                )
        return True


def delete_proposal(proposal_id: int) -> bool:
    """提案を削除する。"""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM matching_proposals WHERE id = ?", (proposal_id,)
        )
        return cursor.rowcount > 0


def get_proposals(
    status: Optional[str] = None,
    engineer_id: Optional[int] = None,
    listing_id: Optional[int] = None,
) -> list[dict]:
    """提案一覧（フィルター付き）。"""
    with get_connection() as conn:
        query = """
            SELECT mp.*,
                   e.name as engineer_name,
                   jl.company_name as listing_company
            FROM matching_proposals mp
            JOIN engineers e ON mp.engineer_id = e.id
            JOIN job_listings jl ON mp.listing_id = jl.id
            WHERE 1=1
        """
        params: list = []
        if status:
            query += " AND mp.status = ?"
            params.append(status)
        if engineer_id:
            query += " AND mp.engineer_id = ?"
            params.append(engineer_id)
        if listing_id:
            query += " AND mp.listing_id = ?"
            params.append(listing_id)
        query += " ORDER BY mp.updated_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_matching_stats() -> dict:
    """提案のKPI統計（ステータス別件数）。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM matching_proposals GROUP BY status"
        ).fetchall()
        by_status = {r["status"]: r["cnt"] for r in rows}
        total = sum(by_status.values())
    return {
        "total": total,
        "candidate": by_status.get("候補", 0),
        "proposed": by_status.get("提案済み", 0),
        "interviewing": by_status.get("面談中", 0),
        "closed": by_status.get("成約", 0),
        "rejected": by_status.get("見送り", 0),
    }


# --- User Profiles ---

def get_user_profile(user_id: str) -> Optional[dict]:
    """Supabase Auth IDからユーザープロフィールを取得する。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def get_user_profile_by_email(email: str) -> Optional[dict]:
    """メールアドレスからユーザープロフィールを取得する。"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None


def upsert_user_profile(user_id: str, email: str, role: str = "engineer",
                        engineer_id: Optional[int] = None,
                        display_name: str = "") -> dict:
    """ユーザープロフィールを作成または更新する。"""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM user_profiles WHERE id = ?", (user_id,)
        ).fetchone()
        if existing:
            if conn.is_pg:
                conn.execute(
                    """UPDATE user_profiles
                       SET email = ?, role = ?, engineer_id = ?,
                           display_name = ?, updated_at = NOW()
                       WHERE id = ?""",
                    (email, role, engineer_id, display_name, user_id),
                )
            else:
                conn.execute(
                    """UPDATE user_profiles
                       SET email = ?, role = ?, engineer_id = ?,
                           display_name = ?, updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (email, role, engineer_id, display_name, user_id),
                )
        else:
            conn.execute(
                """INSERT INTO user_profiles (id, email, role, engineer_id, display_name)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, email, role, engineer_id, display_name),
            )
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row)


def list_user_profiles() -> list[dict]:
    """全ユーザープロフィールを返す。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM user_profiles ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_user_profile(user_id: str) -> bool:
    """ユーザープロフィールを削除する。"""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM user_profiles WHERE id = ?", (user_id,)
        )
        return cursor.rowcount > 0


# --- Invite Logs ---

def create_invite_log(user_id: str, email: str, invited_by: str) -> dict:
    """招待ログを記録する。"""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO invite_logs (user_id, email, invited_by)
               VALUES (?, ?, ?)""",
            (user_id, email, invited_by),
        )
        row = conn.execute(
            "SELECT * FROM invite_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row) if row else {}


# --- Companies ---

def insert_company(data: dict) -> int:
    """取引先を登録し、IDを返す。"""
    with get_connection() as conn:
        sql = """INSERT INTO companies
                 (name, name_kana, phone, url, prefecture, tags,
                  contact_name, contact_email, notes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            data["name"],
            data.get("name_kana", ""),
            data.get("phone", ""),
            data.get("url", ""),
            data.get("prefecture", ""),
            data.get("tags", ""),
            data.get("contact_name", ""),
            data.get("contact_email", ""),
            data.get("notes", ""),
        )
        if conn.is_pg:
            cursor = conn.execute(sql + " RETURNING id", params)
            return cursor.fetchone()["id"]
        else:
            cursor = conn.execute(sql, params)
            return cursor.lastrowid


def search_companies(keyword: str = "") -> list[dict]:
    """取引先を検索する。"""
    with get_connection() as conn:
        query = "SELECT * FROM companies WHERE 1=1"
        params: list = []
        if keyword:
            query += " AND (name LIKE ? OR name_kana LIKE ? OR contact_name LIKE ?)"
            like = f"%{keyword}%"
            params.extend([like, like, like])
        query += " ORDER BY name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
