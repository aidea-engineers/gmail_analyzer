"""Supabase Admin API ラッパー — GoTrue Admin API を httpx で直接呼び出す。

環境変数:
  SUPABASE_URL: Supabase プロジェクト URL (例: https://xxx.supabase.co)
  SUPABASE_SERVICE_ROLE_KEY: Service Role キー (Settings > API > service_role)
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_GOTRUE_BASE = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else ""


def _headers() -> dict[str, str]:
    return {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    """Supabase Admin API が利用可能かどうか。"""
    return bool(SUPABASE_URL and SERVICE_ROLE_KEY)


async def create_user(email: str, password: str) -> str:
    """Supabase Auth にユーザーを作成し、UUID を返す。

    Raises:
        RuntimeError: API エラー時
    """
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY が未設定です")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_GOTRUE_BASE}/admin/users",
            headers=_headers(),
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
            },
        )
    if resp.status_code not in (200, 201):
        detail = resp.text
        try:
            detail = resp.json().get("msg", resp.text)
        except Exception:
            pass
        logger.error("Supabase create_user failed: %s %s", resp.status_code, detail)
        raise RuntimeError(f"ユーザー作成に失敗しました: {detail}")

    return resp.json()["id"]


async def delete_user(user_id: str) -> None:
    """Supabase Auth からユーザーを削除する。"""
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY が未設定です")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(
            f"{_GOTRUE_BASE}/admin/users/{user_id}",
            headers=_headers(),
        )
    if resp.status_code not in (200, 204):
        detail = resp.text
        try:
            detail = resp.json().get("msg", resp.text)
        except Exception:
            pass
        logger.error("Supabase delete_user failed: %s %s", resp.status_code, detail)
        raise RuntimeError(f"ユーザー削除に失敗しました: {detail}")


async def update_user_password(user_id: str, new_password: str) -> None:
    """Supabase Auth ユーザーのパスワードを変更する。"""
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY が未設定です")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{_GOTRUE_BASE}/admin/users/{user_id}",
            headers=_headers(),
            json={"password": new_password},
        )
    if resp.status_code not in (200, 201):
        detail = resp.text
        try:
            detail = resp.json().get("msg", resp.text)
        except Exception:
            pass
        logger.error("Supabase update_password failed: %s %s", resp.status_code, detail)
        raise RuntimeError(f"パスワード変更に失敗しました: {detail}")
