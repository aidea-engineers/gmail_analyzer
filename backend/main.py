"""FastAPI エントリポイント - Gmail Analyzer バックエンド"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from core.database import init_db
from routers import dashboard, search, fetch, settings

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


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
