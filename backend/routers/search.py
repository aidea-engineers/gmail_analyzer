"""案件検索 API"""
from __future__ import annotations

import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from core.database import (
    search_listings,
    get_distinct_skills,
    get_distinct_areas,
    get_distinct_job_types,
    get_distinct_companies,
)
from utils.date_helpers import format_date_jp

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/filters")
def search_filters():
    return {
        "skills": get_distinct_skills(),
        "areas": get_distinct_areas(),
        "job_types": get_distinct_job_types(),
        "companies": get_distinct_companies(),
    }


@router.get("/listings")
def search_listings_api(
    keyword: str = "",
    keyword_mode: str = Query("and", description="and または or"),
    skills: Optional[str] = Query(None, description="カンマ区切りスキル"),
    areas: Optional[str] = Query(None, description="カンマ区切りエリア"),
    job_types: Optional[str] = Query(None, description="カンマ区切り職種"),
    companies: Optional[str] = Query(None, description="カンマ区切り会社名"),
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    areas_list = [a.strip() for a in areas.split(",") if a.strip()] if areas else None
    types_list = [t.strip() for t in job_types.split(",") if t.strip()] if job_types else None
    companies_list = [c.strip() for c in companies.split(",") if c.strip()] if companies else None

    results = search_listings(
        keyword=keyword,
        keyword_mode=keyword_mode,
        skills=skills_list,
        areas=areas_list,
        job_types=types_list,
        companies=companies_list,
        price_min=price_min if price_min and price_min > 0 else None,
        price_max=price_max if price_max and price_max < 200 else None,
        date_from=date_from,
        date_to=f"{date_to} 23:59:59" if date_to else None,
    )

    listings = []
    for r in results:
        skills_raw = r.get("required_skills", "[]")
        if isinstance(skills_raw, str):
            try:
                skills_parsed = json.loads(skills_raw)
            except json.JSONDecodeError:
                skills_parsed = []
        else:
            skills_parsed = skills_raw

        listings.append({
            "id": r.get("id"),
            "company_name": r.get("company_name", ""),
            "job_type": r.get("job_type", ""),
            "work_area": r.get("work_area", ""),
            "unit_price": r.get("unit_price", ""),
            "unit_price_min": r.get("unit_price_min"),
            "unit_price_max": r.get("unit_price_max"),
            "required_skills": skills_parsed,
            "project_details": r.get("project_details", ""),
            "requirements": r.get("requirements", ""),
            "confidence": r.get("confidence", 0),
            "start_month": r.get("start_month", ""),
            "subject": r.get("subject", ""),
            "sender": r.get("sender", ""),
            "received_at": r.get("received_at", ""),
            "created_at": r.get("created_at", ""),
        })

    return {"total": len(listings), "listings": listings}


@router.get("/export")
def export_csv(
    keyword: str = "",
    keyword_mode: str = Query("and", description="and または or"),
    skills: Optional[str] = None,
    areas: Optional[str] = None,
    job_types: Optional[str] = None,
    companies: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    areas_list = [a.strip() for a in areas.split(",") if a.strip()] if areas else None
    types_list = [t.strip() for t in job_types.split(",") if t.strip()] if job_types else None
    companies_list = [c.strip() for c in companies.split(",") if c.strip()] if companies else None

    results = search_listings(
        keyword=keyword,
        keyword_mode=keyword_mode,
        skills=skills_list,
        areas=areas_list,
        job_types=types_list,
        companies=companies_list,
        price_min=price_min if price_min and price_min > 0 else None,
        price_max=price_max if price_max and price_max < 200 else None,
        date_from=date_from,
        date_to=f"{date_to} 23:59:59" if date_to else None,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["日付", "会社名", "職種", "エリア", "単価", "スキル", "案件内容", "必須要件・求める人物像", "確信度"])

    for r in results:
        skills_raw = r.get("required_skills", "[]")
        if isinstance(skills_raw, str):
            try:
                skills_parsed = json.loads(skills_raw)
            except json.JSONDecodeError:
                skills_parsed = []
        else:
            skills_parsed = skills_raw

        writer.writerow([
            format_date_jp(r.get("created_at", "")),
            r.get("company_name", ""),
            r.get("job_type", ""),
            r.get("work_area", ""),
            r.get("unit_price", ""),
            ", ".join(skills_parsed) if isinstance(skills_parsed, list) else str(skills_parsed),
            r.get("project_details", ""),
            r.get("requirements", ""),
            f'{r.get("confidence", 0):.0%}',
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ses_listings.csv"},
    )
