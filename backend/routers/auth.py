"""認証関連APIルーター"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.auth import CurrentUser, require_auth, require_admin
from core.database import (
    get_user_profile,
    upsert_user_profile,
    list_user_profiles,
    delete_user_profile,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Schemas ---

class UserProfileUpdate(BaseModel):
    role: Optional[str] = None
    engineer_id: Optional[int] = None
    display_name: Optional[str] = None


class UserProfileCreate(BaseModel):
    user_id: str
    email: str
    role: str = "engineer"
    engineer_id: Optional[int] = None
    display_name: str = ""


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
async def create_user_profile(
    body: UserProfileCreate,
    user: CurrentUser = Depends(require_admin),
):
    """ユーザープロフィールを作成する（管理者のみ）。"""
    profile = upsert_user_profile(
        user_id=body.user_id,
        email=body.email,
        role=body.role,
        engineer_id=body.engineer_id,
        display_name=body.display_name,
    )
    return {"message": "作成しました", "profile": profile}


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
    """ユーザープロフィールを削除する（管理者のみ）。"""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="自分自身は削除できません")
    if not delete_user_profile(user_id):
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    return {"message": "削除しました"}
