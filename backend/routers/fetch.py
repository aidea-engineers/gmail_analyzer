"""メール取得・解析 API（読み取り + 書き込み + SSE進捗）"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import StreamingResponse

from core.database import get_connection, get_fetch_logs
from core.mock_data import generate_and_insert, clear_all_data, clear_mock_data
from core.gmail_client import is_authenticated
from config import Config

router = APIRouter(prefix="/api/fetch", tags=["fetch"])

# 進行中ジョブの進捗を保持
_job_progress: dict[str, dict] = {}


@router.get("/status")
def fetch_status():
    gmail_connected = is_authenticated()
    with get_connection() as conn:
        total_emails = conn.execute(
            "SELECT COUNT(*) as cnt FROM emails"
        ).fetchone()["cnt"]
        processed_emails = conn.execute(
            "SELECT COUNT(*) as cnt FROM emails WHERE is_processed = TRUE"
        ).fetchone()["cnt"]
        unprocessed_emails = total_emails - processed_emails
        total_listings = conn.execute(
            "SELECT COUNT(*) as cnt FROM job_listings"
        ).fetchone()["cnt"]

    return {
        "gmail_connected": gmail_connected,
        "gemini_api_key_set": bool(Config.GEMINI_API_KEY),
        "total_emails": total_emails,
        "processed_emails": processed_emails,
        "unprocessed_emails": unprocessed_emails,
        "total_listings": total_listings,
    }


@router.get("/logs")
def fetch_logs(limit: int = Query(10, ge=1, le=100)):
    logs = get_fetch_logs(limit=limit)
    return {"logs": logs}


def _run_pipeline(job_id: str, mode: str):
    """バックグラウンドでパイプラインを実行する"""
    def progress_cb(status: dict):
        _job_progress[job_id] = {
            "phase": status.get("phase", ""),
            "current": status.get("current", 0),
            "total": status.get("total", 0),
            "message": status.get("message", ""),
        }

    try:
        if mode == "full":
            from core.gmail_client import get_gmail_service
            from core.batch_processor import run_full_pipeline
            service = get_gmail_service()
            if not service:
                _job_progress[job_id] = {
                    "phase": "error",
                    "current": 0,
                    "total": 0,
                    "message": "Gmail接続に失敗しました",
                    "done": True,
                }
                return
            result = run_full_pipeline(gmail_service=service, progress_callback=progress_cb)
        else:
            from core.batch_processor import run_extraction_only
            result = run_extraction_only(progress_callback=progress_cb)

        _job_progress[job_id] = {
            "phase": "done",
            "current": 0,
            "total": 0,
            "message": f"完了: 処理{result.emails_processed}件 / 案件{result.listings_created}件"
            + (f" / 失敗{result.api_errors}件" if result.api_errors > 0 else ""),
            "done": True,
            "result": {
                "emails_fetched": result.emails_fetched,
                "emails_processed": result.emails_processed,
                "listings_created": result.listings_created,
                "api_errors": result.api_errors,
                "status": result.status,
            },
        }
    except Exception as e:
        _job_progress[job_id] = {
            "phase": "error",
            "current": 0,
            "total": 0,
            "message": f"エラー: {str(e)}",
            "done": True,
        }


@router.post("/full-pipeline")
def start_full_pipeline(background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex[:12]
    _job_progress[job_id] = {
        "phase": "starting",
        "current": 0,
        "total": 0,
        "message": "パイプライン開始...",
    }
    background_tasks.add_task(_run_pipeline, job_id, "full")
    return {"job_id": job_id}


@router.post("/ai-only")
def start_ai_only(background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex[:12]
    _job_progress[job_id] = {
        "phase": "starting",
        "current": 0,
        "total": 0,
        "message": "AI解析開始...",
    }
    background_tasks.add_task(_run_pipeline, job_id, "ai_only")
    return {"job_id": job_id}


@router.get("/progress/{job_id}")
async def stream_progress(job_id: str):
    """SSE で進捗をストリーミング"""
    async def event_generator():
        while True:
            progress = _job_progress.get(job_id)
            if progress is None:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break
            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"
            if progress.get("done"):
                # クリーンアップ
                _job_progress.pop(job_id, None)
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/mock")
def insert_mock_data(count: int = Query(150, ge=10, le=500)):
    inserted = generate_and_insert(count=count)
    return {"inserted": inserted}


@router.delete("/mock")
def delete_mock_data():
    deleted = clear_mock_data()
    return {"deleted": deleted, "message": f"モックデータ{deleted}件を削除しました"}


@router.delete("/data")
def delete_all_data():
    clear_all_data()
    return {"message": "全データを削除しました"}
