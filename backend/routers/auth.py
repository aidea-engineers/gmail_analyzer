"""認証関連APIルーター"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import CurrentUser, require_auth, require_admin
from core import supabase_admin
from core.database import (
    get_user_profile,
    upsert_user_profile,
    list_user_profiles,
    delete_user_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Schemas ---

class UserProfileUpdate(BaseModel):
    role: Optional[str] = None
    engineer_id: Optional[int] = None
    display_name: Optional[str] = None


class UserProfileCreate(BaseModel):
    email: str
    password: str
    role: str = "engineer"
    engineer_id: Optional[int] = None
    display_name: str = ""


class InviteRequest(BaseModel):
    email: str
    role: str = "engineer"
    engineer_id: Optional[int] = None
    display_name: str = ""


class PasswordReset(BaseModel):
    new_password: str


class PasswordChange(BaseModel):
    new_password: str


# --- Endpoints ---

@router.get("/me")
async def get_me(user: CurrentUser = Depends(require_auth)):
    """現在ログイン中のユーザー情報を返す。"""
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "engineer_id": user.engineer_id,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
    }


@router.get("/users")
async def list_users(user: CurrentUser = Depends(require_admin)):
    """全ユーザー一覧を返す（管理者のみ）。"""
    return {"users": list_user_profiles()}


@router.post("/users")
async def create_user(
    body: UserProfileCreate,
    user: CurrentUser = Depends(require_admin),
):
    """ユーザーアカウントを作成する（管理者のみ）。

    1. Supabase Auth にユーザーを作成
    2. user_profiles に紐付けレコードを作成
    """
    # Supabase Auth にユーザー作成
    if supabase_admin.is_configured():
        try:
            auth_uid = await supabase_admin.create_user(body.email, body.password)
        except RuntimeError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        # ローカル開発用: Supabase未設定時はダミーID
        import uuid
        auth_uid = str(uuid.uuid4())
        logger.warning("Supabase Admin未設定 — ダミーUID(%s)でユーザー作成", auth_uid)

    # user_profiles に保存
    profile = upsert_user_profile(
        user_id=auth_uid,
        email=body.email,
        role=body.role,
        engineer_id=body.engineer_id,
        display_name=body.display_name,
    )
    return {"message": "作成しました", "profile": profile}


@router.post("/invite")
async def invite_user(
    body: InviteRequest,
    user: CurrentUser = Depends(require_admin),
):
    """エンジニアを招待する（管理者のみ）。

    1. Supabase Auth に招待メールを送信（パスワード未設定で作成）
    2. user_profiles にengineerロールで紐付けレコードを作成
    """
    if not supabase_admin.is_configured():
        raise HTTPException(status_code=400, detail="Supabase Admin APIが未設定です")

    # 既存ユーザーチェック
    from core.database import get_user_profile_by_email
    existing = get_user_profile_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="このメールアドレスは既に登録されています")

    # リダイレクト先を許可ドメインに固定
    frontend_url = os.getenv("FRONTEND_URL", "https://gmail-analyzer-nu.vercel.app").strip()
    redirect_to = f"{frontend_url}/set-password"

    try:
        auth_uid = await supabase_admin.invite_user(body.email, redirect_to=redirect_to)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # user_profiles に保存
    role = body.role if body.role in ("admin", "engineer") else "engineer"
    profile = upsert_user_profile(
        user_id=auth_uid,
        email=body.email,
        role=role,
        engineer_id=body.engineer_id,
        display_name=body.display_name,
    )

    # 招待履歴を記録
    from core.database import create_invite_log
    create_invite_log(
        user_id=auth_uid,
        email=body.email,
        invited_by=user.id,
    )

    return {"message": "招待メールを送信しました", "profile": profile}


@router.post("/reinvite/{user_id}")
async def reinvite_user(
    user_id: str,
    user: CurrentUser = Depends(require_admin),
):
    """招待メールを再送する（管理者のみ）。

    GoTrue の /invite は既存ユーザーに使えないため、
    Auth側のユーザーを削除→再招待→user_profilesのIDを更新する。
    """
    existing = get_user_profile(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    if not supabase_admin.is_configured():
        raise HTTPException(status_code=400, detail="Supabase Admin APIが未設定です")

    # 1. Supabase Auth から既存ユーザーを削除（パスワード未設定なので安全）
    try:
        await supabase_admin.delete_user(user_id)
    except RuntimeError as e:
        logger.warning("再招待時のAuth削除失敗（続行）: %s", e)

    # 2. 再招待（新しいAuthユーザー作成 + メール送信）
    frontend_url = os.getenv("FRONTEND_URL", "https://gmail-analyzer-nu.vercel.app").strip().strip()
    redirect_to = f"{frontend_url}/set-password"

    try:
        new_auth_uid = await supabase_admin.invite_user(existing["email"], redirect_to=redirect_to)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. user_profilesのIDを新しいAuth UIDに更新
    from core.database import delete_user_profile
    delete_user_profile(user_id)
    new_profile = upsert_user_profile(
        user_id=new_auth_uid,
        email=existing["email"],
        role=existing.get("role", "engineer"),
        engineer_id=existing.get("engineer_id"),
        display_name=existing.get("display_name", ""),
    )

    # 再招待履歴を記録
    from core.database import create_invite_log
    create_invite_log(
        user_id=new_auth_uid,
        email=existing["email"],
        invited_by=user.id,
    )

    return {"message": "招待メールを再送しました", "profile": new_profile}


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserProfileUpdate,
    user: CurrentUser = Depends(require_admin),
):
    """ユーザープロフィールを更新する（管理者のみ）。"""
    existing = get_user_profile(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    profile = upsert_user_profile(
        user_id=user_id,
        email=existing["email"],
        role=body.role if body.role is not None else existing["role"],
        engineer_id=body.engineer_id if body.engineer_id is not None else existing.get("engineer_id"),
        display_name=body.display_name if body.display_name is not None else existing.get("display_name", ""),
    )
    return {"message": "更新しました", "profile": profile}


@router.delete("/users/{user_id}")
async def remove_user(
    user_id: str,
    user: CurrentUser = Depends(require_admin),
):
    """ユーザーを削除する（管理者のみ）。Supabase Auth + user_profiles 両方削除。"""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="自分自身は削除できません")

    # Supabase Auth からも削除
    if supabase_admin.is_configured():
        try:
            await supabase_admin.delete_user(user_id)
        except RuntimeError as e:
            logger.warning("Supabase Auth削除失敗（プロフィールのみ削除）: %s", e)

    if not delete_user_profile(user_id):
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    return {"message": "削除しました"}


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    body: PasswordReset,
    user: CurrentUser = Depends(require_admin),
):
    """管理者がユーザーのパスワードをリセットする。"""
    existing = get_user_profile(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    if not supabase_admin.is_configured():
        raise HTTPException(status_code=400, detail="Supabase Admin APIが未設定です")

    try:
        await supabase_admin.update_user_password(user_id, body.new_password)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "パスワードをリセットしました"}


@router.put("/me/password")
async def change_my_password(
    body: PasswordChange,
    user: CurrentUser = Depends(require_auth),
):
    """ログイン中のユーザーが自分のパスワードを変更する。"""
    if not supabase_admin.is_configured():
        raise HTTPException(status_code=400, detail="Supabase Admin APIが未設定です")

    try:
        await supabase_admin.update_user_password(user.id, body.new_password)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "パスワードを変更しました"}
