"""案件・メール・ダッシュボード集計関連のDB操作"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from core.db_core import get_connection, _USE_PG

logger = logging.getLogger(__name__)


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

        if project_details:
            sql2 = f"""SELECT project_details FROM job_listings jl WHERE {where}"""
            rows = conn.execute(sql2, params).fetchall()
            for r in rows:
                existing = r["project_details"] or ""
                if existing and project_details:
                    shorter = min(existing, project_details, key=len)
                    longer = max(existing, project_details, key=len)
                    if shorter in longer:
                        return True
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
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
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
            query += """ AND (
                jl.company_name LIKE ? OR jl.work_area LIKE ?
                OR jl.project_details LIKE ? OR jl.required_skills LIKE ?
                OR jl.requirements LIKE ? OR e.subject LIKE ?
            )"""
            like = f"%{keyword.strip()}%"
            params.extend([like] * 6)
        else:
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
        count_query = f"SELECT COUNT(*) as cnt FROM ({query}) sub"
        total = conn.execute(count_query, params).fetchone()["cnt"]

        query += " LIMIT ? OFFSET ?"
        rows = conn.execute(query, params + [limit, offset]).fetchall()
        return [dict(r) for r in rows], total


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
    """KPI統計を1クエリで取得"""
    base_where = "WHERE 1=1"
    params: list = []
    if date_from:
        base_where += " AND created_at >= ?"
        params.append(date_from)
    if date_to:
        base_where += " AND created_at <= ?"
        params.append(date_to)

    today = datetime.now().strftime("%Y-%m-%d")

    with get_connection() as conn:
        if conn.is_pg:
            today_expr = "created_at::date = ?"
        else:
            today_expr = "date(created_at) = ?"

        query = f"""
            SELECT
                COUNT(*) as total,
                AVG(CASE WHEN unit_price_min IS NOT NULL
                    THEN (COALESCE(unit_price_min,0) + COALESCE(unit_price_max,0)) / 2.0
                    ELSE NULL END) as avg_price,
                COUNT(DISTINCT CASE WHEN work_area != '' THEN work_area ELSE NULL END) as area_count,
                SUM(CASE WHEN {today_expr} THEN 1 ELSE 0 END) as today_count
            FROM job_listings {base_where}
        """
        row = conn.execute(query, [today] + params).fetchone()
        row = dict(row)

    return {
        "total": row["total"] or 0,
        "avg_price": round(float(row["avg_price"]), 1) if row["avg_price"] else 0,
        "today_count": row["today_count"] or 0,
        "area_count": row["area_count"] or 0,
    }


def get_monthly_summary(months: int = 6) -> list[dict]:
    """月別の案件サマリーを返す（直近N月分）— 1クエリで完結"""
    with get_connection() as conn:
        if conn.is_pg:
            month_expr = "to_char(created_at, 'YYYY-MM')"
        else:
            month_expr = "strftime('%Y-%m', created_at)"

        query = f"""
            SELECT
                m.month, m.listing_count, m.avg_price, m.unique_companies,
                COALESCE(ta.work_area, '') as top_area
            FROM (
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
            ) m
            LEFT JOIN LATERAL (
                SELECT work_area
                FROM job_listings
                WHERE {month_expr} = m.month AND work_area != ''
                GROUP BY work_area
                ORDER BY COUNT(*) DESC
                LIMIT 1
            ) ta ON true
            ORDER BY m.month ASC
        """

        if conn.is_pg:
            rows = [dict(r) for r in conn.execute(query, (months,)).fetchall()]
        else:
            main_query = f"""
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
            rows = [dict(r) for r in conn.execute(main_query, (months,)).fetchall()]
            for row in rows:
                area_query = f"""
                    SELECT work_area FROM job_listings
                    WHERE {month_expr} = ? AND work_area != ''
                    GROUP BY work_area ORDER BY COUNT(*) DESC LIMIT 1
                """
                area_row = conn.execute(area_query, (row["month"],)).fetchone()
                row["top_area"] = dict(area_row)["work_area"] if area_row else ""
            rows.reverse()

        for row in rows:
            if row["avg_price"] is not None:
                row["avg_price"] = round(float(row["avg_price"]), 1)

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
