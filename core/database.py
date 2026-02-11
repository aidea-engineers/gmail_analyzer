from __future__ import annotations

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import Config


def _ensure_db_dir():
    Config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    _ensure_db_dir()
    conn = sqlite3.connect(str(Config.DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript("""
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
        """)


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
            cursor = conn.execute(
                """INSERT OR IGNORE INTO emails
                   (gmail_message_id, subject, sender, received_at, body_text, labels)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (gmail_message_id, subject, sender, received_at, body_text, labels),
            )
            return cursor.lastrowid if cursor.rowcount > 0 else None
        except sqlite3.IntegrityError:
            return None


def get_unprocessed_emails(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM emails WHERE is_processed = 0 ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_email_processed(email_id: int):
    with get_connection() as conn:
        conn.execute(
            "UPDATE emails SET is_processed = 1 WHERE id = ?", (email_id,)
        )


# --- Job Listing CRUD ---

def insert_job_listing(email_id: int, extraction: dict) -> int:
    skills_list = extraction.get("required_skills", [])
    skills_json = json.dumps(skills_list, ensure_ascii=False)
    raw_json = json.dumps(extraction, ensure_ascii=False, default=str)

    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO job_listings
               (email_id, company_name, work_area, unit_price,
                unit_price_min, unit_price_max, required_skills,
                project_details, job_type, raw_extraction, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                email_id,
                extraction.get("company_name", ""),
                extraction.get("work_area", ""),
                extraction.get("unit_price", ""),
                extraction.get("unit_price_min"),
                extraction.get("unit_price_max"),
                skills_json,
                extraction.get("project_details", ""),
                extraction.get("job_type", ""),
                raw_json,
                extraction.get("confidence", 0.0),
            ),
        )
        listing_id = cursor.lastrowid

        for skill in skills_list:
            conn.execute(
                "INSERT INTO skills (listing_id, skill_name) VALUES (?, ?)",
                (listing_id, skill.strip()),
            )

        return listing_id


def search_listings(
    keyword: str = "",
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
        query += """ AND (
            jl.company_name LIKE ? OR jl.work_area LIKE ?
            OR jl.project_details LIKE ? OR jl.required_skills LIKE ?
            OR e.subject LIKE ?
        )"""
        like = f"%{keyword}%"
        params.extend([like] * 5)

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

    with get_connection() as conn:
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
        today_count = conn.execute(
            f"SELECT COUNT(*) as cnt FROM job_listings WHERE date(created_at) = ?",
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
        cursor = conn.execute(
            "INSERT INTO fetch_log (query_used) VALUES (?)", (query_used,)
        )
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
