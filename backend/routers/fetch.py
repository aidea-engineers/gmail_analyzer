"""メール取得・解析状態 API（読み取りのみ）"""
from __future__ import annotations

from fastapi import APIRouter, Query

from core.database import get_connection, get_fetch_logs

router = APIRouter(prefix="/api/fetch", tags=["fetch"])


@router.get("/status")
def fetch_status():
    with get_connection() as conn:
        total_emails = conn.execute(
            "SELECT COUNT(*) as cnt FROM emails"
        ).fetchone()["cnt"]
        processed_emails = conn.execute(
            "SELECT COUNT(*) as cnt FROM emails WHERE is_processed = 1"
        ).fetchone()["cnt"]
        unprocessed_emails = total_emails - processed_emails
        total_listings = conn.execute(
            "SELECT COUNT(*) as cnt FROM job_listings"
        ).fetchone()["cnt"]

    return {
        "total_emails": total_emails,
        "processed_emails": processed_emails,
        "unprocessed_emails": unprocessed_emails,
        "total_listings": total_listings,
    }


@router.get("/logs")
def fetch_logs(limit: int = Query(10, ge=1, le=100)):
    logs = get_fetch_logs(limit=limit)
    return {"logs": logs}
