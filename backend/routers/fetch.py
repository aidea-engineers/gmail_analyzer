"""メール取得・解析 API（読み取り + 書き込み + SSE進捗）"""
from __future__ import annotations

import asyncio
import json
import threading
import uuid
from typing import Optional

import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from core.database import (
    get_connection,
    get_fetch_logs,
    get_all_listings_with_sender,
    batch_update_company_names,
)
from core.mock_data import generate_and_insert, clear_all_data, clear_mock_data
from core.gmail_client import is_authenticated
from utils.text_helpers import extract_company_from_sender, _extract_domain_company
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fetch", tags=["fetch"])

# 進行中ジョブの進捗を保持
_job_progress: dict[str, dict] = {}

# 重複実行防止用ロック
_pipeline_lock = threading.Lock()
_running_job_id: Optional[str] = None


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
    """バックグラウンドでパイプラインを実行する（排他制御付き）"""
    global _running_job_id

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
    finally:
        with _pipeline_lock:
            _running_job_id = None


@router.post("/full-pipeline")
def start_full_pipeline(background_tasks: BackgroundTasks):
    global _running_job_id
    with _pipeline_lock:
        if _running_job_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"別のジョブが実行中です (job_id: {_running_job_id})",
            )
        job_id = uuid.uuid4().hex[:12]
        _running_job_id = job_id

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
    global _running_job_id
    with _pipeline_lock:
        if _running_job_id is not None:
            raise HTTPException(
                status_code=409,
                detail=f"別のジョブが実行中です (job_id: {_running_job_id})",
            )
        job_id = uuid.uuid4().hex[:12]
        _running_job_id = job_id

    _job_progress[job_id] = {
        "phase": "starting",
        "current": 0,
        "total": 0,
        "message": "AI解析開始...",
    }
    background_tasks.add_task(_run_pipeline, job_id, "ai_only")
    return {"job_id": job_id}


def _run_cron_pipeline_bg():
    """cronパイプラインをバックグラウンドで実行する（未処理が0になるまでループ）"""
    global _running_job_id
    try:
        from core.gmail_client import get_gmail_service
        from core.batch_processor import run_full_pipeline, run_extraction_only

        service = get_gmail_service()
        if not service:
            logger.error("Cron pipeline: Gmail接続に失敗しました")
            # fetch_logは run_full_pipeline 内で作られるため、
            # ここでは作成されていない → staleにはならない
            return

        # Phase 1: メール取得 + 初回AI解析（200件まで）
        result = run_full_pipeline(gmail_service=service)
        total_fetched = result.emails_fetched
        total_processed = result.emails_processed
        total_listings = result.listings_created
        total_errors = result.api_errors

        # Phase 2: 未処理が残っている場合はループで全件処理
        batch_num = 1
        max_batches = 20  # 無限ループ防止（最大20バッチ = 4,000件）
        while result.emails_processed > 0 and batch_num < max_batches:
            batch_num += 1
            logger.info("Cron pipeline: extraction batch %d starting", batch_num)
            result = run_extraction_only()
            total_processed += result.emails_processed
            total_listings += result.listings_created
            total_errors += result.api_errors

        logger.info(
            "Cron pipeline completed: fetched=%d processed=%d listings=%d errors=%d batches=%d",
            total_fetched, total_processed, total_listings, total_errors, batch_num,
        )
    except Exception:
        logger.exception("Cron pipeline failed")
    finally:
        with _pipeline_lock:
            _running_job_id = None


@router.post("/cron")
def run_cron_pipeline(
    background_tasks: BackgroundTasks,
    authorization: str = Header(None),
):
    """cron専用エンドポイント（GitHub Actions等から呼び出し）"""
    # トークン認証
    if not Config.CRON_SECRET:
        raise HTTPException(status_code=500, detail="CRON_SECRET is not configured")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer "):]
    if token != Config.CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid token")

    # 重複実行チェック
    global _running_job_id
    with _pipeline_lock:
        if _running_job_id is not None:
            logger.warning("Cron pipeline skipped: another job is running (%s)", _running_job_id)
            return {"status": "skipped", "message": f"別のジョブが実行中のためスキップ (job_id: {_running_job_id})"}
        _running_job_id = f"cron-{uuid.uuid4().hex[:8]}"

    # バックグラウンドで実行（即座にレスポンスを返す）
    logger.info("Cron pipeline started (background)")
    background_tasks.add_task(_run_cron_pipeline_bg)

    return {"status": "started", "message": "Pipeline started in background"}


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


@router.post("/reanalyze-old")
def reanalyze_old_listings(
    authorization: str = Header(None),
    cutoff: str = Query("2026-02-25T04:20:00", description="この日時より前の案件を再解析"),
):
    """旧フォーマットの案件を削除して再解析対象にする"""
    if not Config.CRON_SECRET:
        raise HTTPException(status_code=500, detail="CRON_SECRET is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = authorization[len("Bearer "):]
    if token != Config.CRON_SECRET:
        raise HTTPException(status_code=403, detail="Invalid token")

    with get_connection() as conn:
        # 旧案件のemail_idを取得
        rows = conn.execute(
            "SELECT DISTINCT email_id FROM job_listings WHERE created_at < ?",
            (cutoff,),
        ).fetchall()
        email_ids = [r["email_id"] for r in rows]

        if not email_ids:
            return {"message": "再解析対象の旧案件がありません", "deleted_listings": 0, "reset_emails": 0}

        # 旧案件のIDを取得
        old_listings = conn.execute(
            "SELECT id FROM job_listings WHERE created_at < ?",
            (cutoff,),
        ).fetchall()
        old_listing_ids = [r["id"] for r in old_listings]

        # スキルを削除
        if old_listing_ids:
            placeholders = ",".join("?" * len(old_listing_ids))
            conn.execute(
                f"DELETE FROM skills WHERE listing_id IN ({placeholders})",
                old_listing_ids,
            )

        # 旧案件を削除
        deleted = conn.execute(
            "DELETE FROM job_listings WHERE created_at < ?",
            (cutoff,),
        ).rowcount

        # 該当メールを未処理に戻す
        placeholders = ",".join("?" * len(email_ids))
        reset = conn.execute(
            f"UPDATE emails SET is_processed = FALSE WHERE id IN ({placeholders})",
            email_ids,
        ).rowcount

    return {
        "message": f"旧案件{deleted}件を削除、メール{reset}件を再解析対象にしました",
        "deleted_listings": deleted,
        "reset_emails": reset,
    }


@router.post("/fix-company-names")
def fix_company_names(
    authorization: str = Header(None),
):
    """既存案件の会社名を再抽出して修復する（担当者名・部署名を除去）"""
    # TODO: 修復完了後に認証を復元する

    listings = get_all_listings_with_sender()

    # デバッグ: 変更があるもの + 最新20件を返す
    debug_mode = True
    if debug_mode:
        changes = []
        latest = []
        for row in listings:
            sender = row.get("sender", "")
            old_name = row.get("company_name", "")
            new_name = extract_company_from_sender(sender)
            if not new_name:
                new_name = _extract_domain_company(sender)
            item = {
                "id": row["id"],
                "sender": sender[:100],
                "old": old_name,
                "new": new_name,
            }
            if new_name and new_name != old_name:
                changes.append(item)
        # 最新20件（ID降順）
        sorted_listings = sorted(listings, key=lambda x: x["id"], reverse=True)
        for row in sorted_listings[:20]:
            sender = row.get("sender", "")
            old_name = row.get("company_name", "")
            new_name = extract_company_from_sender(sender)
            if not new_name:
                new_name = _extract_domain_company(sender)
            latest.append({
                "id": row["id"],
                "sender": sender[:100],
                "old": old_name,
                "new": new_name,
                "changed": new_name != old_name and bool(new_name),
            })
        return {"changes_count": len(changes), "changes_sample": changes[:10], "latest": latest, "total": len(listings)}

    updates = []
    for row in listings:
        sender = row.get("sender", "")
        old_name = row.get("company_name", "")
        new_name = extract_company_from_sender(sender)

        if not new_name:
            new_name = _extract_domain_company(sender)

        if new_name and new_name != old_name:
            updates.append((new_name, row["id"]))

    updated = batch_update_company_names(updates)

    return {
        "message": f"会社名を{updated}件修復しました（全{len(listings)}件中）",
        "total": len(listings),
        "updated": updated,
    }
