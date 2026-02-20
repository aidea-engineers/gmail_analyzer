from __future__ import annotations

from datetime import datetime, timedelta


def get_date_range(period: str) -> tuple[str, str]:
    """期間文字列からdate_from, date_toを返す（YYYY-MM-DD形式）"""
    now = datetime.now()
    date_to = now.strftime("%Y-%m-%d 23:59:59")

    if period == "7日":
        date_from = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
    elif period == "30日":
        date_from = (now - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
    elif period == "90日":
        date_from = (now - timedelta(days=90)).strftime("%Y-%m-%d 00:00:00")
    else:
        date_from = ""
        date_to = ""

    return date_from, date_to


def format_date_jp(dt_str: str) -> str:
    """日時文字列を日本語表記にフォーマットする"""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(str(dt_str))
        return dt.strftime("%Y/%m/%d %H:%M")
    except (ValueError, TypeError):
        return str(dt_str)
