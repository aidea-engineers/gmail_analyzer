"""エンジニア関連のDB操作"""
from __future__ import annotations

import json
import logging
from typing import Optional

from core.db_core import get_connection

logger = logging.getLogger(__name__)


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

        skill_years = data.get("skill_years", {})
        for skill in data.get("skills", []):
            if skill.strip():
                years = skill_years.get(skill.strip())
                conn.execute(
                    "INSERT INTO engineer_skills (engineer_id, skill_name, years) VALUES (?, ?, ?)",
                    (eng_id, skill.strip(), years),
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
            skill_years = data.get("skill_years", {})
            for skill in data["skills"]:
                if skill.strip():
                    years = skill_years.get(skill.strip())
                    conn.execute(
                        "INSERT INTO engineer_skills (engineer_id, skill_name, years) VALUES (?, ?, ?)",
                        (eng_id, skill.strip(), years),
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
            "SELECT skill_name, years FROM engineer_skills WHERE engineer_id = ? ORDER BY skill_name",
            (eng_id,),
        ).fetchall()
        eng["skills"] = [s["skill_name"] for s in skills]
        eng["skill_years"] = {s["skill_name"]: s["years"] for s in skills if s["years"] is not None}

        # 職歴
        careers = conn.execute(
            "SELECT id, company_name, job_title, period_start, period_end, description FROM engineer_careers WHERE engineer_id = ? ORDER BY period_start DESC",
            (eng_id,),
        ).fetchall()
        eng["careers"] = [dict(c) for c in careers]

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


def create_engineer_self(user_id: str, data: dict) -> dict:
    """エンジニアが自分のプロフィールを自己登録する。engineersテーブルにレコード作成 + user_profilesのengineer_idを自動紐付け。"""
    # Check if already linked
    with get_connection() as conn:
        profile = conn.execute("SELECT engineer_id FROM user_profiles WHERE id = ?", (user_id,)).fetchone()
        if profile and profile["engineer_id"]:
            raise ValueError("既にエンジニア情報が登録されています")

    # Check if engineer with same email exists (admin pre-created)
    email = data.get("email", "")
    if email:
        with get_connection() as conn:
            existing = conn.execute("SELECT id FROM engineers WHERE email = ?", (email,)).fetchone()
            if existing:
                eng_id = existing["id"]
                conn.execute("UPDATE user_profiles SET engineer_id = ? WHERE id = ?", (eng_id, user_id))
                conn.commit()
                update_engineer(eng_id, data)
                return get_engineer(eng_id)

    # Create new engineer record
    eng_id = insert_engineer(data)

    # Link to user_profiles
    with get_connection() as conn:
        conn.execute("UPDATE user_profiles SET engineer_id = ? WHERE id = ?", (eng_id, user_id))
        conn.commit()
    return get_engineer(eng_id)


def save_engineer_careers(engineer_id: int, careers: list[dict]) -> None:
    """エンジニアの職歴を保存する（全削除→再挿入）。"""
    with get_connection() as conn:
        conn.execute("DELETE FROM engineer_careers WHERE engineer_id = ?", (engineer_id,))
        for c in careers:
            conn.execute(
                "INSERT INTO engineer_careers (engineer_id, company_name, job_title, period_start, period_end, description) VALUES (?, ?, ?, ?, ?, ?)",
                (engineer_id, c.get("company_name", ""), c.get("job_title", ""), c.get("period_start", ""), c.get("period_end", ""), c.get("description", "")),
            )
        conn.commit()


def get_engineer_careers(engineer_id: int) -> list[dict]:
    """エンジニアの職歴一覧を返す。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, company_name, job_title, period_start, period_end, description FROM engineer_careers WHERE engineer_id = ? ORDER BY period_start DESC",
            (engineer_id,),
        ).fetchall()
        return [dict(r) for r in rows]


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
