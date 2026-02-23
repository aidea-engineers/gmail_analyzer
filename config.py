from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    GMAIL_CREDENTIALS_PATH: Path = PROJECT_ROOT / os.getenv(
        "GMAIL_CREDENTIALS_PATH", "credentials/credentials.json"
    )
    GMAIL_TOKEN_PATH: Path = PROJECT_ROOT / os.getenv(
        "GMAIL_TOKEN_PATH", "credentials/token.json"
    )
    GMAIL_LABELS: list[str] = [
        l.strip()
        for l in os.getenv("GMAIL_LABELS", "").split(",")
        if l.strip()
    ]
    GMAIL_KEYWORDS: list[str] = [
        k.strip()
        for k in os.getenv("GMAIL_KEYWORDS", "案件,募集").split(",")
        if k.strip()
    ]

    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "50"))
    MAX_EMAILS_PER_FETCH: int = int(os.getenv("MAX_EMAILS_PER_FETCH", "500"))
    GEMINI_DELAY_SECONDS: float = float(os.getenv("GEMINI_DELAY_SECONDS", "1.0"))

    DB_PATH: Path = PROJECT_ROOT / os.getenv("DB_PATH", "data/gmail_analyzer.db")
