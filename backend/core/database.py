from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config

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
"""


def init_db():
    with get_connection() as conn:
        conn.executescript(_PG_SCHEMA if conn.is_pg else _SQLITE_SCHEMA)
        # マイグレーション: start_month カラム追加
        try:
            conn.execute(
                "ALTER TABLE job_listings ADD COLUMN start_month TEXT DEFAULT ''"
            )
            conn.commit()
        except Exception:
            conn.rollback()  # カラムが既に存在する場合は無視
        # マイグレーション: requirements カラム追加
        try:
            conn.execute(
                "ALTER TABLE job_listings ADD COLUMN requirements TEXT DEFAULT ''"
            )
            conn.commit()
        except Exception:
            conn.rollback()  # カラムが既に存在する場合は無視


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


def update_listing_company_name(listing_id: int, company_name: str):
    """案件の会社名を更新する"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE job_listings SET company_name = ? WHERE id = ?",
            (company_name, listing_id),
        )


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
