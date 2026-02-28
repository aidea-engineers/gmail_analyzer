"""FastAPI エントリポイント - AIdea Platform バックエンド"""
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from core.database import init_db, cleanup_stale_fetch_logs, clear_old_email_bodies
from routers import auth, dashboard, search, fetch, settings, engineers, matching, import_data

# ロギング設定（Renderログに出力するためstdoutに設定）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

app = FastAPI(
    title="AIdea Platform API",
    description="SES事業管理システム API",
    version="1.0.0",
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
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(fetch.router)
app.include_router(settings.router)
app.include_router(engineers.router)
app.include_router(matching.router)
app.include_router(import_data.router)


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
