"""JWT認証モジュール — Supabase Auth JWTを検証し、user_profilesからロールを取得する。

AUTH_ENABLED=false の場合はすべてのリクエストを許可する（デプロイ移行用）。
Supabase は ES256 (ECC P-256) で JWT を署名するため、JWKS エンドポイントから公開鍵を取得して検証する。
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request

from core.database import get_user_profile, get_user_profile_by_email, upsert_user_profile

logger = logging.getLogger(__name__)

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")

# JWKS クライアント（ES256 公開鍵を自動取得・キャッシュ）
_jwks_client: Optional[PyJWKClient] = None
if SUPABASE_URL:
    _jwks_client = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")


@dataclass
class CurrentUser:
    """認証済みユーザー情報。"""
    id: str  # Supabase Auth UUID
    email: str
    role: str  # "admin" | "engineer"
    engineer_id: Optional[int] = None
    display_name: str = ""

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _dummy_admin() -> CurrentUser:
    """AUTH_ENABLED=false 時のダミー管理者。"""
    return CurrentUser(
        id="__auth_disabled__",
        email="admin@localhost",
        role="admin",
    )


async def get_current_user(request: Request) -> CurrentUser:
    """AuthorizationヘッダからJWTを検証し、CurrentUserを返す。

    AUTH_ENABLED=false の場合はダミー管理者を返す。
    """
    if not AUTH_ENABLED:
        return _dummy_admin()

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="認証トークンがありません")

    token = auth_header[7:]

    try:
        if _jwks_client:
            # ES256: JWKS エンドポイントから公開鍵を取得して検証
            signing_key = _jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            # フォールバック: HS256 (レガシー JWT シークレット)
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="トークンの有効期限が切れています")
    except jwt.InvalidTokenError as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(status_code=401, detail="無効なトークンです")

    sub = payload.get("sub")
    email = payload.get("email", "")
    if not sub:
        raise HTTPException(status_code=401, detail="トークンにユーザーIDがありません")

    # user_profilesからロール取得（なければ自動作成）
    profile = get_user_profile(sub)
    if not profile:
        profile = upsert_user_profile(
            user_id=sub,
            email=email,
            role="engineer",  # デフォルトはエンジニア
        )

    return CurrentUser(
        id=profile["id"],
        email=profile["email"],
        role=profile["role"],
        engineer_id=profile.get("engineer_id"),
        display_name=profile.get("display_name", ""),
    )


async def require_auth(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """認証済みユーザーのみ許可する依存関数。"""
    return user


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """管理者のみ許可する依存関数。"""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return user
