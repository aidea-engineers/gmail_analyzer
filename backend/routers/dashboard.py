"""ダッシュボード関連 API"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from core.auth import CurrentUser, require_admin
from core.database import (
    get_total_stats,
    get_skill_counts,
    get_price_distribution,
    get_area_counts,
    get_trend_data,
    get_monthly_summary,
)
from utils.date_helpers import get_date_range

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis")
def dashboard_kpis(
    period: str = Query("30日", description="表示期間: 7日, 30日, 90日, 全期間"),
    user: CurrentUser = Depends(require_admin),
):
    date_from, date_to = get_date_range(period)
    stats = get_total_stats(date_from=date_from, date_to=date_to)
    return stats


@router.get("/charts")
def dashboard_charts(
    period: str = Query("30日"),
    granularity: str = Query("daily", description="トレンド粒度: daily, weekly"),
    user: CurrentUser = Depends(require_admin),
):
    date_from, date_to = get_date_range(period)

    skills = get_skill_counts(date_from=date_from, date_to=date_to)
    prices = get_price_distribution(date_from=date_from, date_to=date_to)
    areas = get_area_counts(date_from=date_from, date_to=date_to)
    trend = get_trend_data(
        granularity=granularity, date_from=date_from, date_to=date_to
    )

    return {
        "skills": skills,
        "prices": prices,
        "areas": areas,
        "trend": trend,
    }


@router.get("/monthly-summary")
def dashboard_monthly_summary(
    months: int = Query(6, description="取得する月数", ge=1, le=24),
    user: CurrentUser = Depends(require_admin),
):
    return get_monthly_summary(months=months)
