"""FastAPI エントリポイント - Gmail Analyzer バックエンド"""
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from core.database import init_db, cleanup_stale_fetch_logs, clear_old_email_bodies
from routers import dashboard, search, fetch, settings, engineers

# ロギング設定（Renderログに出力するためstdoutに設定）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

app = FastAPI(
    title="Gmail Analyzer API",
    description="SES案件メール解析 API",
    version="0.1.0",
)

# CORS設定（環境変数で動的に設定）
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(fetch.router)
app.include_router(settings.router)
app.include_router(engineers.router)


logger = logging.getLogger(__name__)


@app.on_event("startup")
def startup():
    init_db()
    cleaned = cleanup_stale_fetch_logs()
    if cleaned:
        logger.info("Stale fetch logs cleaned up: %d entries", cleaned)
    cleared = clear_old_email_bodies(days=7)
    if cleared:
        logger.info("Old email bodies cleared: %d emails", cleared)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
