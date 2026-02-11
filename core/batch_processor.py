from __future__ import annotations

import logging
from typing import Optional, Callable

from core.database import (
    get_unprocessed_emails,
    mark_email_processed,
    insert_job_listing,
    insert_fetch_log,
    update_fetch_log,
)
from core.gemini_extractor import extract_from_email
from models.schemas import BatchResult
from config import Config

logger = logging.getLogger(__name__)


def run_extraction_only(
    progress_callback: Optional[Callable] = None,
) -> BatchResult:
    """未処理メールのGemini抽出のみ実行する（Gmail取得なし）"""
    result = BatchResult()
    errors = []

    log_id = insert_fetch_log(query_used="extraction_only")

    try:
        # 未処理メールを取得
        unprocessed = get_unprocessed_emails(limit=Config.BATCH_SIZE)
        total = len(unprocessed)

        if total == 0:
            update_fetch_log(log_id, status="completed", errors=["未処理メールなし"])
            result.status = "completed"
            return result

        if progress_callback:
            progress_callback(
                {
                    "phase": "extraction",
                    "current": 0,
                    "total": total,
                    "message": f"AI解析開始: {total}件のメール",
                }
            )

        for i, email in enumerate(unprocessed):
            email_id = email["id"]
            subject = email.get("subject", "")
            body = email.get("body_text", "")

            try:
                extraction = extract_from_email(subject, body)

                if extraction and extraction.is_job_listing:
                    insert_job_listing(email_id, extraction.model_dump())
                    result.listings_created += 1

                mark_email_processed(email_id)
                result.emails_processed += 1

            except Exception as e:
                error_msg = f"メールID {email_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                mark_email_processed(email_id)

            if progress_callback:
                progress_callback(
                    {
                        "phase": "extraction",
                        "current": i + 1,
                        "total": total,
                        "message": f"AI解析中: {i + 1}/{total} メール (案件: {result.listings_created}件)",
                    }
                )

        result.status = "completed"
        result.errors = errors

    except Exception as e:
        result.status = "failed"
        result.errors = [str(e)]
        logger.error(f"バッチ処理エラー: {e}")

    update_fetch_log(
        log_id,
        status=result.status,
        emails_fetched=result.emails_fetched,
        emails_processed=result.emails_processed,
        errors=result.errors,
    )

    return result


def run_full_pipeline(
    gmail_service=None,
    progress_callback: Optional[Callable] = None,
) -> BatchResult:
    """Gmail取得 + Gemini抽出のフルパイプラインを実行する"""
    result = BatchResult()
    errors = []

    log_id = insert_fetch_log(query_used="full_pipeline")

    try:
        # Phase 1: Gmail取得
        if gmail_service:
            if progress_callback:
                progress_callback(
                    {
                        "phase": "fetch",
                        "current": 0,
                        "total": 0,
                        "message": "Gmailからメール取得中...",
                    }
                )

            from core.gmail_client import fetch_and_store_emails

            fetched = fetch_and_store_emails(gmail_service, progress_callback)
            result.emails_fetched = fetched

            if progress_callback:
                progress_callback(
                    {
                        "phase": "fetch",
                        "current": fetched,
                        "total": fetched,
                        "message": f"メール取得完了: {fetched}件",
                    }
                )

        # Phase 2: Gemini抽出
        extraction_result = run_extraction_only(progress_callback)
        result.emails_processed = extraction_result.emails_processed
        result.listings_created = extraction_result.listings_created
        result.errors = extraction_result.errors
        result.status = extraction_result.status

    except Exception as e:
        result.status = "failed"
        result.errors = [str(e)]
        logger.error(f"パイプラインエラー: {e}")

    update_fetch_log(
        log_id,
        status=result.status,
        emails_fetched=result.emails_fetched,
        emails_processed=result.emails_processed,
        errors=result.errors,
    )

    return result
