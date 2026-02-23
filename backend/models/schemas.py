from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class JobListingExtraction(BaseModel):
    """Gemini APIからの抽出結果スキーマ"""
    company_name: Optional[str] = Field(None, description="会社名・企業名")
    work_area: Optional[str] = Field(None, description="勤務地・エリア (例: 東京都港区, リモート)")
    unit_price: Optional[str] = Field(
        None, description="単価・報酬 (原文のまま, 例: '60-70万', '~80万円/月')"
    )
    unit_price_min: Optional[int] = Field(
        None, description="単価の下限 (万円単位の整数, 例: 60)"
    )
    unit_price_max: Optional[int] = Field(
        None, description="単価の上限 (万円単位の整数, 例: 70)"
    )
    required_skills: list[str] = Field(
        default_factory=list,
        description="必要スキル・言語のリスト (例: ['Java', 'Spring Boot', 'AWS'])",
    )
    project_details: Optional[str] = Field(None, description="案件内容・要件の要約")
    job_type: Optional[str] = Field(
        None, description="募集職種 (例: バックエンドエンジニア, PMO)"
    )
    confidence: float = Field(0.5, description="抽出の確信度 0.0-1.0")
    is_job_listing: bool = Field(True, description="このメールがSES案件情報かどうか")


class EmailRecord(BaseModel):
    """メールデータの転送モデル"""
    gmail_message_id: str
    subject: str = ""
    sender: str = ""
    received_at: Optional[datetime] = None
    body_text: str = ""
    labels: str = ""


class SearchFilters(BaseModel):
    """検索フィルタ"""
    keyword: str = ""
    skills: list[str] = Field(default_factory=list)
    areas: list[str] = Field(default_factory=list)
    job_types: list[str] = Field(default_factory=list)
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class BatchResult(BaseModel):
    """バッチ処理の結果"""
    emails_fetched: int = 0
    emails_processed: int = 0
    listings_created: int = 0
    api_errors: int = 0
    errors: list[str] = Field(default_factory=list)
    status: str = "completed"
