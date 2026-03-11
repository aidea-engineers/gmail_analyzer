"""ユーザー・取引先関連のDB操作"""
from __future__ import annotations

import logging
from typing import Optional

from core.db_core import get_connection

logger = logging.getLogger(__name__)


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
