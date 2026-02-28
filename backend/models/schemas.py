from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class JobListingExtraction(BaseModel):
    """Gemini APIからの1案件の抽出結果スキーマ"""
    company_name: Optional[str] = Field(None, description="会社名・企業名")
    work_area: Optional[str] = Field(None, description="勤務地・エリア")
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
    requirements: Optional[str] = Field(None, description="必須要件・求める人物像")
    job_type: Optional[str] = Field(
        None, description="募集職種 (例: バックエンドエンジニア, PMO)"
    )
    confidence: float = Field(0.5, description="抽出の確信度 0.0-1.0")
    start_month: Optional[str] = Field(None, description="参画開始時期 (例: '2026年4月', '即日')")
    is_job_listing: bool = Field(True, description="このメールがSES案件情報かどうか")


class EmailExtractionResult(BaseModel):
    """1通のメールからの抽出結果（複数案件対応）"""
    listings: list[JobListingExtraction] = Field(
        default_factory=list,
        description="メール内の案件リスト。案件がない場合はis_job_listing=falseの要素を1つ返す",
    )


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


# --- Engineer schemas ---

class EngineerCreate(BaseModel):
    """エンジニア新規登録リクエスト"""
    name: str = Field(..., description="氏名（必須）")
    skills: list[str] = Field(default_factory=list, description="スキル一覧")
    experience_years: Optional[int] = Field(None, description="経験年数")
    current_price: Optional[int] = Field(None, description="現在の単価（万円）")
    desired_price_min: Optional[int] = Field(None, description="希望単価下限（万円）")
    desired_price_max: Optional[int] = Field(None, description="希望単価上限（万円）")
    status: str = Field("待機中", description="ステータス（待機中/稼働中/面談中/休止中）")
    preferred_areas: str = Field("", description="希望エリア（カンマ区切り）")
    available_from: str = Field("", description="稼働可能日（YYYY-MM-DD）")
    notes: str = Field("", description="備考")
    processes: str = Field("", description="対応工程（カンマ区切り）")
    job_type_experience: str = Field("", description="職種経験（カンマ区切り）")
    position_experience: str = Field("", description="ポジション経験（カンマ区切り）")
    remote_preference: str = Field("", description="リモート希望")
    career_desired_job_type: str = Field("", description="今後の希望職種（カンマ区切り）")
    career_desired_skills: str = Field("", description="習得したいスキル")
    career_notes: str = Field("", description="キャリアメモ")


class EngineerUpdate(BaseModel):
    """エンジニア更新リクエスト（部分更新可）"""
    name: Optional[str] = None
    skills: Optional[list[str]] = None
    experience_years: Optional[int] = None
    current_price: Optional[int] = None
    desired_price_min: Optional[int] = None
    desired_price_max: Optional[int] = None
    status: Optional[str] = None
    preferred_areas: Optional[str] = None
    available_from: Optional[str] = None
    notes: Optional[str] = None
    processes: Optional[str] = None
    job_type_experience: Optional[str] = None
    position_experience: Optional[str] = None
    remote_preference: Optional[str] = None
    career_desired_job_type: Optional[str] = None
    career_desired_skills: Optional[str] = None
    career_notes: Optional[str] = None


class AssignmentCreate(BaseModel):
    """アサイン履歴追加リクエスト"""
    listing_id: Optional[int] = Field(None, description="案件ID（任意）")
    company_name: str = Field("", description="会社名")
    project_name: str = Field("", description="案件名")
    start_date: str = Field("", description="開始日")
    end_date: str = Field("", description="終了日")
    unit_price: Optional[int] = Field(None, description="単価（万円）")
    status: str = Field("稼働中", description="ステータス")
    notes: str = Field("", description="備考")


# --- Matching schemas ---

class ProposalCreate(BaseModel):
    """提案登録リクエスト"""
    engineer_id: int = Field(..., description="エンジニアID")
    listing_id: int = Field(..., description="案件ID")
    score: int = Field(0, description="マッチスコア")
    notes: str = Field("", description="メモ")


class ProposalUpdate(BaseModel):
    """提案更新リクエスト"""
    status: str = Field(..., description="ステータス（候補/提案済み/面談中/成約/見送り）")
    notes: Optional[str] = Field(None, description="メモ")
