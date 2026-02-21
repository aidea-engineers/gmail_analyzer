"""設定情報 API（読み取りのみ）"""
from __future__ import annotations

from fastapi import APIRouter

from config import Config

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return {
        "gemini_model": Config.GEMINI_MODEL,
        "gemini_api_key_set": bool(Config.GEMINI_API_KEY),
        "gmail_labels": Config.GMAIL_LABELS,
        "gmail_keywords": Config.GMAIL_KEYWORDS,
        "batch_size": Config.BATCH_SIZE,
        "max_emails_per_fetch": Config.MAX_EMAILS_PER_FETCH,
        "gemini_delay_seconds": Config.GEMINI_DELAY_SECONDS,
        "db_path": str(Config.DB_PATH),
    }
