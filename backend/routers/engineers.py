"""エンジニア管理 API"""
from __future__ import annotations

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

from core.database import (
    insert_engineer,
    update_engineer,
    delete_engineer,
    get_engineer,
    search_engineers,
    get_engineer_stats,
    get_distinct_engineer_skills,
    get_distinct_engineer_areas,
    insert_assignment,
    delete_assignment,
)
from models.schemas import EngineerCreate, EngineerUpdate, AssignmentCreate
from utils.text_helpers import normalize_skill_name

router = APIRouter(prefix="/api/engineers", tags=["engineers"])


# --- 固定パスのエンドポイント（/{id} より前に定義） ---


@router.get("/stats")
def engineer_stats():
    """エンジニアのKPI統計"""
    try:
        return get_engineer_stats()
    except Exception as e:
        logger.exception("engineer_stats error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters")
def engineer_filters():
    """フィルター選択肢を返す"""
    try:
        return {
            "skills": get_distinct_engineer_skills(),
            "areas": get_distinct_engineer_areas(),
            "statuses": ["待機中", "稼働中", "面談中", "休止中"],
        }
    except Exception as e:
        logger.exception("engineer_filters error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
def engineer_list(
    keyword: str = "",
    skills: Optional[str] = Query(None, description="カンマ区切りスキル"),
    statuses: Optional[str] = Query(None, description="カンマ区切りステータス"),
    areas: Optional[str] = Query(None, description="カンマ区切りエリア"),
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
):
    """エンジニア一覧（フィルター付き）"""
    try:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
        statuses_list = [s.strip() for s in statuses.split(",") if s.strip()] if statuses else None
        areas_list = [a.strip() for a in areas.split(",") if a.strip()] if areas else None

        results = search_engineers(
            keyword=keyword,
            skills=skills_list,
            statuses=statuses_list,
            areas=areas_list,
            price_min=price_min if price_min and price_min > 0 else None,
            price_max=price_max if price_max and price_max < 300 else None,
        )

        engineers = []
        for r in results:
            engineers.append({
                "id": r["id"],
                "name": r["name"],
                "experience_years": r.get("experience_years"),
                "current_price": r.get("current_price"),
                "desired_price_min": r.get("desired_price_min"),
                "desired_price_max": r.get("desired_price_max"),
                "status": r.get("status", "待機中"),
                "preferred_areas": r.get("preferred_areas", ""),
                "available_from": r.get("available_from", ""),
                "notes": r.get("notes", ""),
                "skills": r.get("skills", []),
                "created_at": str(r.get("created_at", "")),
                "updated_at": str(r.get("updated_at", "")),
            })

        return {"total": len(engineers), "engineers": engineers}
    except Exception as e:
        logger.exception("engineer_list error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
def engineer_export(
    keyword: str = "",
    skills: Optional[str] = None,
    statuses: Optional[str] = None,
    areas: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
):
    """エンジニア一覧をCSVエクスポート（BOM付きUTF-8）"""
    skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    statuses_list = [s.strip() for s in statuses.split(",") if s.strip()] if statuses else None
    areas_list = [a.strip() for a in areas.split(",") if a.strip()] if areas else None

    results = search_engineers(
        keyword=keyword,
        skills=skills_list,
        statuses=statuses_list,
        areas=areas_list,
        price_min=price_min if price_min and price_min > 0 else None,
        price_max=price_max if price_max and price_max < 300 else None,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "名前", "ステータス", "スキル", "経験年数",
        "現在単価(万円)", "希望単価下限(万円)", "希望単価上限(万円)",
        "希望エリア", "稼働可能日", "備考",
    ])

    for r in results:
        writer.writerow([
            r.get("name", ""),
            r.get("status", ""),
            "; ".join(r.get("skills", [])),
            r.get("experience_years") or "",
            r.get("current_price") or "",
            r.get("desired_price_min") or "",
            r.get("desired_price_max") or "",
            r.get("preferred_areas", ""),
            r.get("available_from", ""),
            r.get("notes", ""),
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=engineers.csv"},
    )


@router.post("/import-csv")
async def engineer_import_csv(file: UploadFile = File(...)):
    """CSVファイルからエンジニアを一括インポート（UTF-8/Shift_JIS両対応）"""
    content = await file.read()

    # エンコーディング判定（UTF-8 → Shift_JIS フォールバック）
    text = None
    for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            text = content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        raise HTTPException(status_code=400, detail="CSVファイルのエンコーディングを判定できません")

    reader = csv.DictReader(io.StringIO(text))
    imported = 0
    errors = []

    for i, row in enumerate(reader, start=2):  # ヘッダー行=1なのでデータは2行目から
        name = (row.get("名前") or row.get("name") or "").strip()
        if not name:
            errors.append(f"{i}行目: 名前が空のためスキップ")
            continue

        # スキル解析（セミコロンまたはカンマ区切り）
        skills_raw = row.get("スキル") or row.get("skills") or ""
        if ";" in skills_raw:
            skills = [normalize_skill_name(s.strip()) for s in skills_raw.split(";") if s.strip()]
        else:
            skills = [normalize_skill_name(s.strip()) for s in skills_raw.split(",") if s.strip()]

        # 数値フィールドの安全なパース
        def safe_int(val):
            if not val:
                return None
            try:
                return int(float(str(val).strip()))
            except (ValueError, TypeError):
                return None

        data = {
            "name": name,
            "skills": skills,
            "experience_years": safe_int(row.get("経験年数") or row.get("experience_years")),
            "current_price": safe_int(row.get("現在単価(万円)") or row.get("current_price")),
            "desired_price_min": safe_int(row.get("希望単価下限(万円)") or row.get("desired_price_min")),
            "desired_price_max": safe_int(row.get("希望単価上限(万円)") or row.get("desired_price_max")),
            "status": (row.get("ステータス") or row.get("status") or "待機中").strip(),
            "preferred_areas": (row.get("希望エリア") or row.get("preferred_areas") or "").strip(),
            "available_from": (row.get("稼働可能日") or row.get("available_from") or "").strip(),
            "notes": (row.get("備考") or row.get("notes") or "").strip(),
        }

        try:
            insert_engineer(data)
            imported += 1
        except Exception as e:
            errors.append(f"{i}行目: {name} のインポートに失敗 ({e})")

    return {"imported": imported, "errors": errors}


# --- 個別リソースのエンドポイント ---


@router.post("")
def create_engineer(body: EngineerCreate):
    """エンジニア新規登録"""
    try:
        data = body.model_dump()
        # スキル正規化
        data["skills"] = [normalize_skill_name(s) for s in data.get("skills", [])]
        eng_id = insert_engineer(data)
        return {"id": eng_id, "message": "登録しました"}
    except Exception as e:
        logger.exception("create_engineer error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{eng_id}")
def get_engineer_detail(eng_id: int):
    """エンジニア詳細（スキル+アサイン履歴付き）"""
    eng = get_engineer(eng_id)
    if not eng:
        raise HTTPException(status_code=404, detail="エンジニアが見つかりません")
    # datetime を文字列に変換
    for key in ("created_at", "updated_at"):
        if eng.get(key):
            eng[key] = str(eng[key])
    for a in eng.get("assignments", []):
        if a.get("created_at"):
            a["created_at"] = str(a["created_at"])
    return eng


@router.put("/{eng_id}")
def update_engineer_api(eng_id: int, body: EngineerUpdate):
    """エンジニア更新"""
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="更新するフィールドがありません")
    # スキル正規化
    if "skills" in data:
        data["skills"] = [normalize_skill_name(s) for s in data["skills"]]
    ok = update_engineer(eng_id, data)
    if not ok:
        raise HTTPException(status_code=404, detail="エンジニアが見つかりません")
    return {"message": "更新しました"}


@router.delete("/{eng_id}")
def delete_engineer_api(eng_id: int):
    """エンジニア削除"""
    ok = delete_engineer(eng_id)
    if not ok:
        raise HTTPException(status_code=404, detail="エンジニアが見つかりません")
    return {"message": "削除しました"}


@router.post("/{eng_id}/assignments")
def create_assignment(eng_id: int, body: AssignmentCreate):
    """アサイン履歴追加"""
    # エンジニアの存在確認
    eng = get_engineer(eng_id)
    if not eng:
        raise HTTPException(status_code=404, detail="エンジニアが見つかりません")
    data = body.model_dump()
    assignment_id = insert_assignment(eng_id, data)
    return {"id": assignment_id, "message": "アサインを追加しました"}


@router.delete("/assignments/{assignment_id}")
def delete_assignment_api(assignment_id: int):
    """アサイン履歴削除"""
    ok = delete_assignment(assignment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="アサインが見つかりません")
    return {"message": "アサインを削除しました"}
