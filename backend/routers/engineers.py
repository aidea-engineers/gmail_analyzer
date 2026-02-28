"""エンジニア管理 API"""
from __future__ import annotations

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from core.auth import CurrentUser, require_auth, require_admin

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
from utils.text_helpers import (
    normalize_skill_name, categorize_skills, PROCESS_OPTIONS,
    JOB_TYPE_OPTIONS, POSITION_OPTIONS, REMOTE_OPTIONS, AREA_OPTIONS,
    EDUCATION_OPTIONS, INDUSTRY_OPTIONS, PROFICIENCY_OPTIONS,
)

router = APIRouter(prefix="/api/engineers", tags=["engineers"])


# --- 固定パスのエンドポイント（/{id} より前に定義） ---


@router.get("/stats")
def engineer_stats(user: CurrentUser = Depends(require_admin)):
    """エンジニアのKPI統計"""
    try:
        return get_engineer_stats()
    except Exception as e:
        logger.exception("engineer_stats error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/filters")
def engineer_filters(user: CurrentUser = Depends(require_admin)):
    """フィルター選択肢を返す"""
    try:
        return {
            "skills": get_distinct_engineer_skills(),
            "areas": get_distinct_engineer_areas(),
            "statuses": ["待機中", "稼働中", "面談中", "休止中"],
            "process_options": PROCESS_OPTIONS,
            "job_type_options": JOB_TYPE_OPTIONS,
            "position_options": POSITION_OPTIONS,
            "remote_options": REMOTE_OPTIONS,
            "area_options": AREA_OPTIONS,
            "education_options": EDUCATION_OPTIONS,
            "industry_options": INDUSTRY_OPTIONS,
            "proficiency_options": PROFICIENCY_OPTIONS,
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
    job_types: Optional[str] = Query(None, description="カンマ区切り職種経験"),
    positions: Optional[str] = Query(None, description="カンマ区切りポジション"),
    remote: Optional[str] = Query(None, description="カンマ区切りリモート希望"),
    user: CurrentUser = Depends(require_admin),
):
    """エンジニア一覧（フィルター付き）"""
    try:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
        statuses_list = [s.strip() for s in statuses.split(",") if s.strip()] if statuses else None
        areas_list = [a.strip() for a in areas.split(",") if a.strip()] if areas else None
        job_types_list = [s.strip() for s in job_types.split(",") if s.strip()] if job_types else None
        positions_list = [s.strip() for s in positions.split(",") if s.strip()] if positions else None
        remote_list = [s.strip() for s in remote.split(",") if s.strip()] if remote else None

        results = search_engineers(
            keyword=keyword,
            skills=skills_list,
            statuses=statuses_list,
            areas=areas_list,
            price_min=price_min if price_min and price_min > 0 else None,
            price_max=price_max if price_max and price_max < 300 else None,
            job_types=job_types_list,
            positions=positions_list,
            remote=remote_list,
        )

        engineers = []
        for r in results:
            skills = r.get("skills", [])
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
                "skills": skills,
                "processes": r.get("processes", ""),
                "job_type_experience": r.get("job_type_experience", ""),
                "position_experience": r.get("position_experience", ""),
                "remote_preference": r.get("remote_preference", ""),
                "career_desired_job_type": r.get("career_desired_job_type", ""),
                "career_desired_skills": r.get("career_desired_skills", ""),
                "career_notes": r.get("career_notes", ""),
                "birth_date": r.get("birth_date", ""),
                "education": r.get("education", ""),
                "industry_experience": r.get("industry_experience", ""),
                "skill_proficiency": r.get("skill_proficiency", "{}"),
                "certifications": r.get("certifications", ""),
                "categorized_skills": categorize_skills(skills),
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
    job_types: Optional[str] = Query(None, description="カンマ区切り職種経験"),
    positions: Optional[str] = Query(None, description="カンマ区切りポジション"),
    remote: Optional[str] = Query(None, description="カンマ区切りリモート希望"),
    user: CurrentUser = Depends(require_admin),
):
    """エンジニア一覧をCSVエクスポート（BOM付きUTF-8）"""
    skills_list = [s.strip() for s in skills.split(",") if s.strip()] if skills else None
    statuses_list = [s.strip() for s in statuses.split(",") if s.strip()] if statuses else None
    areas_list = [a.strip() for a in areas.split(",") if a.strip()] if areas else None
    job_types_list = [s.strip() for s in job_types.split(",") if s.strip()] if job_types else None
    positions_list = [s.strip() for s in positions.split(",") if s.strip()] if positions else None
    remote_list = [s.strip() for s in remote.split(",") if s.strip()] if remote else None

    results = search_engineers(
        keyword=keyword,
        skills=skills_list,
        statuses=statuses_list,
        areas=areas_list,
        price_min=price_min if price_min and price_min > 0 else None,
        price_max=price_max if price_max and price_max < 300 else None,
        job_types=job_types_list,
        positions=positions_list,
        remote=remote_list,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "名前", "ステータス", "スキル", "経験年数",
        "現在単価(万円)", "希望単価下限(万円)", "希望単価上限(万円)",
        "希望エリア", "稼働可能日", "対応工程",
        "職種経験", "ポジション経験", "リモート希望",
        "キャリア希望職種", "習得したいスキル", "キャリアメモ",
        "生年月日", "最終学歴", "業種経験",
        "スキル習熟度", "資格・認定",
        "備考",
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
            r.get("processes", ""),
            r.get("job_type_experience", ""),
            r.get("position_experience", ""),
            r.get("remote_preference", ""),
            r.get("career_desired_job_type", ""),
            r.get("career_desired_skills", ""),
            r.get("career_notes", ""),
            r.get("birth_date", ""),
            r.get("education", ""),
            r.get("industry_experience", ""),
            r.get("skill_proficiency", "{}"),
            r.get("certifications", ""),
            r.get("notes", ""),
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=engineers.csv"},
    )


@router.post("/import-csv")
async def engineer_import_csv(file: UploadFile = File(...), user: CurrentUser = Depends(require_admin)):
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
            "processes": (row.get("対応工程") or row.get("processes") or "").strip(),
            "job_type_experience": (row.get("職種経験") or row.get("job_type_experience") or "").strip(),
            "position_experience": (row.get("ポジション経験") or row.get("position_experience") or "").strip(),
            "remote_preference": (row.get("リモート希望") or row.get("remote_preference") or "").strip(),
            "career_desired_job_type": (row.get("キャリア希望職種") or row.get("career_desired_job_type") or "").strip(),
            "career_desired_skills": (row.get("習得したいスキル") or row.get("career_desired_skills") or "").strip(),
            "career_notes": (row.get("キャリアメモ") or row.get("career_notes") or "").strip(),
            "birth_date": (row.get("生年月日") or row.get("birth_date") or "").strip(),
            "education": (row.get("最終学歴") or row.get("education") or "").strip(),
            "industry_experience": (row.get("業種経験") or row.get("industry_experience") or "").strip(),
            "skill_proficiency": (row.get("スキル習熟度") or row.get("skill_proficiency") or "{}").strip(),
            "certifications": (row.get("資格・認定") or row.get("certifications") or "").strip(),
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
def create_engineer(body: EngineerCreate, user: CurrentUser = Depends(require_admin)):
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
def get_engineer_detail(eng_id: int, user: CurrentUser = Depends(require_auth)):
    """エンジニア詳細（スキル+アサイン履歴付き）。エンジニアは自分の情報のみ閲覧可。"""
    if not user.is_admin and user.engineer_id != eng_id:
        raise HTTPException(status_code=403, detail="自分の情報のみ閲覧できます")
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
    eng["categorized_skills"] = categorize_skills(eng.get("skills", []))
    return eng


# エンジニア本人が編集不可のフィールド（管理者のみ変更可）
_ADMIN_ONLY_FIELDS = {"name", "status", "current_price", "desired_price_min", "desired_price_max", "experience_years"}


@router.put("/{eng_id}")
def update_engineer_api(eng_id: int, body: EngineerUpdate, user: CurrentUser = Depends(require_auth)):
    """エンジニア更新。エンジニアは自分の情報のみ更新可。"""
    if not user.is_admin and user.engineer_id != eng_id:
        raise HTTPException(status_code=403, detail="自分の情報のみ更新できます")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    # エンジニア本人の更新時は管理者専用フィールドを除外
    if not user.is_admin:
        data = {k: v for k, v in data.items() if k not in _ADMIN_ONLY_FIELDS}
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
def delete_engineer_api(eng_id: int, user: CurrentUser = Depends(require_admin)):
    """エンジニア削除"""
    ok = delete_engineer(eng_id)
    if not ok:
        raise HTTPException(status_code=404, detail="エンジニアが見つかりません")
    return {"message": "削除しました"}


@router.post("/{eng_id}/assignments")
def create_assignment(eng_id: int, body: AssignmentCreate, user: CurrentUser = Depends(require_admin)):
    """アサイン履歴追加"""
    # エンジニアの存在確認
    eng = get_engineer(eng_id)
    if not eng:
        raise HTTPException(status_code=404, detail="エンジニアが見つかりません")
    data = body.model_dump()
    assignment_id = insert_assignment(eng_id, data)
    return {"id": assignment_id, "message": "アサインを追加しました"}


@router.delete("/assignments/{assignment_id}")
def delete_assignment_api(assignment_id: int, user: CurrentUser = Depends(require_admin)):
    """アサイン履歴削除"""
    ok = delete_assignment(assignment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="アサインが見つかりません")
    return {"message": "アサインを削除しました"}
