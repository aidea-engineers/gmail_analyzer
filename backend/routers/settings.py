"""設定情報 API（読み取り + 書き込み）"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from config import Config
from core.auth import CurrentUser, require_admin

router = APIRouter(prefix="/api/settings", tags=["settings"])

ENV_PATH = Path(__file__).parent.parent / ".env"


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    gmail_labels: Optional[str] = None
    gmail_keywords: Optional[str] = None
    batch_size: Optional[int] = None
    max_emails_per_fetch: Optional[int] = None
    gemini_delay_seconds: Optional[float] = None


def _load_env() -> dict:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def _save_env(env: dict):
    lines = [
        "# Gemini API",
        f"GEMINI_API_KEY={env.get('GEMINI_API_KEY', '')}",
        f"GEMINI_MODEL={env.get('GEMINI_MODEL', 'gemini-2.0-flash')}",
        "",
        "# Gmail",
        f"GMAIL_CREDENTIALS_PATH={env.get('GMAIL_CREDENTIALS_PATH', 'credentials/credentials.json')}",
        f"GMAIL_TOKEN_PATH={env.get('GMAIL_TOKEN_PATH', 'credentials/token.json')}",
        "",
        "# Filters",
        f"GMAIL_LABELS={env.get('GMAIL_LABELS', '')}",
        f"GMAIL_KEYWORDS={env.get('GMAIL_KEYWORDS', '案件,募集,エンジニア,SE,PG')}",
        "",
        "# Processing",
        f"BATCH_SIZE={env.get('BATCH_SIZE', '50')}",
        f"MAX_EMAILS_PER_FETCH={env.get('MAX_EMAILS_PER_FETCH', '500')}",
        f"GEMINI_DELAY_SECONDS={env.get('GEMINI_DELAY_SECONDS', '1.0')}",
        "",
        "# Database",
        f"DB_PATH={env.get('DB_PATH', 'data/gmail_analyzer.db')}",
        "",
    ]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


@router.get("")
def get_settings(user: CurrentUser = Depends(require_admin)):
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


@router.put("")
def update_settings(body: SettingsUpdate, user: CurrentUser = Depends(require_admin)):
    env = _load_env()

    if body.gemini_api_key is not None:
        env["GEMINI_API_KEY"] = body.gemini_api_key
    if body.gemini_model is not None:
        env["GEMINI_MODEL"] = body.gemini_model
    if body.gmail_labels is not None:
        env["GMAIL_LABELS"] = body.gmail_labels
    if body.gmail_keywords is not None:
        env["GMAIL_KEYWORDS"] = body.gmail_keywords
    if body.batch_size is not None:
        env["BATCH_SIZE"] = str(body.batch_size)
    if body.max_emails_per_fetch is not None:
        env["MAX_EMAILS_PER_FETCH"] = str(body.max_emails_per_fetch)
    if body.gemini_delay_seconds is not None:
        env["GEMINI_DELAY_SECONDS"] = str(body.gemini_delay_seconds)

    _save_env(env)

    return {"message": "設定を保存しました。サーバー再起動後に反映されます。"}
