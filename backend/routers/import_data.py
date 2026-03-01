"""Fairgritデータインポート API（管理者専用）"""
from __future__ import annotations

import csv
import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from core.auth import CurrentUser, require_admin
from core.database import (
    get_connection,
    insert_engineer,
    update_engineer,
    insert_company,
    insert_assignment,
    search_engineers,
    search_companies,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/import", tags=["import"])


def _decode_csv(content: bytes) -> str:
    """CSVバイト列をデコードする。Shift-JIS（cp932）優先。"""
    for encoding in ("cp932", "shift_jis", "utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise HTTPException(status_code=400, detail="CSVファイルのエンコーディングを判定できません")


def _safe_int(val: str | None) -> Optional[int]:
    if not val or not val.strip():
        return None
    try:
        # カンマ除去して整数変換
        return int(float(val.strip().replace(",", "")))
    except (ValueError, TypeError):
        return None


def _safe_float(val: str | None) -> Optional[float]:
    if not val or not val.strip():
        return None
    try:
        return float(val.strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def _strip_yen(val: str | None) -> str | None:
    """「850000円」→「850000」のように円記号を除去する"""
    if not val:
        return val
    return val.strip().replace("円", "").replace("¥", "")


def _strip_hours(val: str | None) -> str | None:
    """「140時間」→「140」のように時間単位を除去する"""
    if not val:
        return val
    return val.strip().replace("時間", "").replace("分", "")


@router.post("/employees")
async def import_employees(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
):
    """社員情報CSVインポート（Fairgrit形式: 1行目メタデータ→スキップ、2行目ヘッダー）"""
    content = await file.read()
    text = _decode_csv(content)
    lines = text.splitlines()

    # 1行目がメタデータかどうか判定（ヘッダー行を探す）
    start_line = 0
    if len(lines) > 1:
        for i, line in enumerate(lines[:3]):
            if "名前" in line or "氏名" in line or "name" in line.lower():
                start_line = i
                break

    csv_text = "\n".join(lines[start_line:])
    reader = csv.DictReader(io.StringIO(csv_text))
    imported = 0
    updated = 0
    errors = []

    # 全エンジニアを一括取得してキャッシュ
    all_engineers = search_engineers(keyword="")
    engineer_map: dict[str, dict] = {e["name"]: e for e in all_engineers}

    for i, row in enumerate(reader, start=start_line + 2):
        name = (
            row.get("名前(漢字)") or row.get("氏名") or row.get("名前") or ""
        ).strip()
        if not name:
            continue

        exact_match = engineer_map.get(name)

        data = {
            "name": name,
            "name_kana": (row.get("名前(カナ)") or row.get("氏名（カナ）") or row.get("フリガナ") or "").strip(),
            "email": (row.get("メールアドレス") or row.get("email") or "").strip(),
            "phone": (row.get("電話番号") or row.get("phone") or "").strip(),
            "gender": (row.get("性別") or row.get("gender") or "").strip(),
            "birth_date": (row.get("生年月日") or row.get("birth_date") or "").strip(),
            "hire_date": (row.get("入社日") or row.get("hire_date") or "").strip(),
            "office_branch": (row.get("支社・事業所") or row.get("所属拠点") or "").strip(),
            "department": (row.get("所属・部門") or row.get("部署") or "").strip(),
            "address": (row.get("現住所") or row.get("住所") or "").strip(),
            "nearest_station": (row.get("最寄駅名") or row.get("最寄り駅") or "").strip(),
            "fairgrit_user_id": (row.get("ユーザーID") or row.get("fairgrit_user_id") or "").strip(),
        }

        try:
            if exact_match:
                update_engineer(exact_match["id"], data)
                updated += 1
            else:
                data["skills"] = []
                insert_engineer(data)
                imported += 1
        except Exception as e:
            errors.append(f"{i}行目: {name} — {e}")

    return {
        "imported": imported,
        "updated": updated,
        "errors": errors,
    }


@router.post("/assignments")
async def import_assignments(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
):
    """案件情報CSVインポート（Fairgrit形式）"""
    content = await file.read()
    text = _decode_csv(content)
    lines = text.splitlines()

    start_line = 0
    if len(lines) > 1:
        for i, line in enumerate(lines[:3]):
            if "氏名" in line or "案件" in line or "参画者" in line or "name" in line.lower():
                start_line = i
                break

    csv_text = "\n".join(lines[start_line:])
    reader = csv.DictReader(io.StringIO(csv_text))
    imported = 0
    skipped = 0
    errors = []

    # 全エンジニアを一括取得してキャッシュ（行ごとにDB検索しない）
    all_engineers = search_engineers(keyword="")
    engineer_map: dict[str, int] = {e["name"]: e["id"] for e in all_engineers}

    # Fairgrit案件CSVは月ごとの請求行なので、同じ(参画者+案件名+契約期間)は重複排除
    seen_assignments: set[tuple[str, str, str, str]] = set()

    for i, row in enumerate(reader, start=start_line + 2):
        eng_name = (
            row.get("参画者") or row.get("氏名") or row.get("名前") or row.get("name") or ""
        ).strip()
        if not eng_name:
            continue

        project_name = (row.get("案件名") or row.get("project_name") or "").strip()
        start_date = (row.get("契約期間(開始)") or row.get("参画開始日") or row.get("start_date") or "").strip()
        end_date = (row.get("契約期間(終了)") or row.get("参画終了日") or row.get("end_date") or "").strip()

        # 重複チェック
        dedup_key = (eng_name, project_name, start_date, end_date)
        if dedup_key in seen_assignments:
            skipped += 1
            continue
        seen_assignments.add(dedup_key)

        # エンジニアをキャッシュから検索
        eng_id = engineer_map.get(eng_name)
        if not eng_id:
            errors.append(f"{i}行目: エンジニア '{eng_name}' が見つかりません")
            continue

        # 単金額の円・¥記号を除去
        raw_price = _strip_yen(
            row.get("単金額") or row.get("単価") or row.get("unit_price")
        )
        raw_monthly = _strip_yen(
            row.get("月額") or row.get("monthly_rate")
        )
        unit_price = _safe_int(raw_price)
        monthly_rate = _safe_int(raw_monthly)
        # 報酬形態が「月額」で月額未設定なら単金額を月額にも設定
        payment_type = (row.get("報酬形態") or "").strip()
        if payment_type == "月額" and not monthly_rate and unit_price:
            monthly_rate = unit_price

        data = {
            "company_name": (row.get("取引先会社名") or row.get("企業名") or row.get("SES先企業名") or "").strip(),
            "project_name": project_name,
            "start_date": start_date,
            "end_date": end_date,
            "unit_price": unit_price,
            "monthly_rate": monthly_rate,
            "contract_type": (row.get("契約種別") or row.get("契約形態") or row.get("contract_type") or "").strip(),
            "sales_person": (row.get("営業担当者") or row.get("営業担当") or row.get("sales_person") or "").strip(),
            "client_company_name": (row.get("エンド企業名") or row.get("client_company_name") or "").strip(),
            "work_hours_lower": _safe_float(_strip_hours(row.get("精算枠(下限)") or row.get("稼働時間下限") or row.get("work_hours_lower"))),
            "work_hours_upper": _safe_float(_strip_hours(row.get("精算枠(上限)") or row.get("稼働時間上限") or row.get("work_hours_upper"))),
            "status": (row.get("ステータス") or "稼働中").strip(),
        }

        try:
            insert_assignment(eng_id, data)
            imported += 1
        except Exception as e:
            errors.append(f"{i}行目: {eng_name} — {e}")

    return {"imported": imported, "skipped": skipped, "errors": errors}


@router.post("/companies")
async def import_companies(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
):
    """取引先情報CSVインポート"""
    content = await file.read()
    text = _decode_csv(content)
    lines = text.splitlines()

    start_line = 0
    if len(lines) > 1:
        for i, line in enumerate(lines[:3]):
            if "企業名" in line or "会社名" in line or "社名" in line or "name" in line.lower():
                start_line = i
                break

    csv_text = "\n".join(lines[start_line:])
    reader = csv.DictReader(io.StringIO(csv_text))
    imported = 0
    skipped = 0
    errors = []

    # Fairgrit取引先CSVは支社・担当者ごとに行があるので社名で重複排除（最初の行を採用）
    seen_companies: set[str] = set()

    for i, row in enumerate(reader, start=start_line + 2):
        name = (
            row.get("社名") or row.get("企業名") or row.get("会社名") or row.get("name") or ""
        ).strip()
        if not name:
            continue

        if name in seen_companies:
            skipped += 1
            continue
        seen_companies.add(name)

        data = {
            "name": name,
            "name_kana": (row.get("社名(カナ)") or row.get("企業名（カナ）") or row.get("フリガナ") or "").strip(),
            "phone": (row.get("電話番号") or row.get("phone") or "").strip(),
            "url": (row.get("URL") or row.get("ホームページ") or "").strip(),
            "prefecture": (row.get("都道府県") or row.get("prefecture") or "").strip(),
            "tags": (row.get("タグ") or row.get("tags") or "").strip(),
            "contact_name": (row.get("社員：名前(漢字)") or row.get("担当者名") or row.get("contact_name") or "").strip(),
            "contact_email": (row.get("社員：営業用メールアドレス") or row.get("担当者メール") or row.get("contact_email") or "").strip(),
            "notes": (row.get("備考") or row.get("notes") or "").strip(),
        }

        try:
            insert_company(data)
            imported += 1
        except Exception as e:
            errors.append(f"{i}行目: {name} — {e}")

    return {"imported": imported, "skipped": skipped, "errors": errors}
