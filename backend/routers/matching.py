"""マッチング API"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

logger = logging.getLogger(__name__)

from core.database import (
    match_engineers_for_listing,
    match_listings_for_engineer,
    insert_proposal,
    update_proposal_status,
    delete_proposal,
    get_proposals,
    get_matching_stats,
    search_engineers,
)
from models.schemas import ProposalCreate, ProposalUpdate

router = APIRouter(prefix="/api/matching", tags=["matching"])


def _serialize_datetime(obj: dict) -> dict:
    """datetime を文字列に変換する。"""
    for key in ("created_at", "updated_at", "received_at"):
        if key in obj and obj[key] is not None:
            obj[key] = str(obj[key])
    return obj


def _serialize_listing(listing: dict) -> dict:
    """案件情報のシリアライズ（required_skillsのJSON解析含む）。"""
    listing = _serialize_datetime(listing)
    raw = listing.get("required_skills", "[]")
    if isinstance(raw, str):
        try:
            listing["required_skills"] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            listing["required_skills"] = []
    return listing


@router.get("/stats")
def matching_stats():
    """マッチングKPI統計"""
    try:
        return get_matching_stats()
    except Exception as e:
        logger.exception("matching_stats error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engineers-for-listing/{listing_id}")
def engineers_for_listing(listing_id: int, limit: int = Query(20, ge=1, le=100)):
    """案件に合うエンジニア一覧（スコア付き）"""
    try:
        matches = match_engineers_for_listing(listing_id, limit=limit)
        for m in matches:
            m["engineer"] = _serialize_datetime(m["engineer"])
            if m["proposal"]:
                m["proposal"] = _serialize_datetime(m["proposal"])
        return {"matches": matches}
    except Exception as e:
        logger.exception("engineers_for_listing error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings-for-engineer/{engineer_id}")
def listings_for_engineer(engineer_id: int, limit: int = Query(20, ge=1, le=100)):
    """エンジニアに合う案件一覧（スコア付き）"""
    try:
        matches = match_listings_for_engineer(engineer_id, limit=limit)
        for m in matches:
            m["listing"] = _serialize_listing(m["listing"])
            if m["proposal"]:
                m["proposal"] = _serialize_datetime(m["proposal"])
        return {"matches": matches}
    except Exception as e:
        logger.exception("listings_for_engineer error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proposals")
def create_proposal(body: ProposalCreate):
    """提案登録"""
    try:
        pid = insert_proposal(
            body.engineer_id, body.listing_id,
            score=body.score, notes=body.notes,
        )
        if pid is None:
            raise HTTPException(status_code=409, detail="この組み合わせは既に提案済みです")
        return {"id": pid, "message": "提案を登録しました"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("create_proposal error")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/proposals/{proposal_id}")
def update_proposal(proposal_id: int, body: ProposalUpdate):
    """提案ステータス更新"""
    valid = {"候補", "提案済み", "面談中", "成約", "見送り"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"無効なステータスです: {body.status}")
    try:
        update_proposal_status(proposal_id, body.status, body.notes)
        return {"message": "更新しました"}
    except Exception as e:
        logger.exception("update_proposal error")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/proposals/{proposal_id}")
def remove_proposal(proposal_id: int):
    """提案削除"""
    ok = delete_proposal(proposal_id)
    if not ok:
        raise HTTPException(status_code=404, detail="提案が見つかりません")
    return {"message": "削除しました"}


@router.get("/proposals")
def list_proposals(
    status: Optional[str] = None,
    engineer_id: Optional[int] = None,
    listing_id: Optional[int] = None,
):
    """提案一覧（フィルター付き）"""
    try:
        rows = get_proposals(
            status=status,
            engineer_id=engineer_id,
            listing_id=listing_id,
        )
        for r in rows:
            _serialize_datetime(r)
        return {"proposals": rows}
    except Exception as e:
        logger.exception("list_proposals error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engineers-brief")
def engineers_brief():
    """エンジニア簡易一覧（待機中/面談中のみ、ドロップダウン用）"""
    try:
        results = search_engineers(statuses=["待機中", "面談中"])
        return [
            {"id": r["id"], "name": r["name"], "status": r.get("status", "")}
            for r in results
        ]
    except Exception as e:
        logger.exception("engineers_brief error")
        raise HTTPException(status_code=500, detail=str(e))
