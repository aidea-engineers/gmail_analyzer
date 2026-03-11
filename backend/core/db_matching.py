"""マッチング・提案関連のDB操作"""
from __future__ import annotations

import json
import logging
from typing import Optional

from core.db_core import get_connection, _USE_PG

logger = logging.getLogger(__name__)


def _calc_match_score(engineer: dict, listing: dict) -> dict:
    """エンジニアと案件のマッチスコアを計算する（合計100点満点）。"""

    # --- スキルマッチ (0〜50点) ---
    listing_skills_raw = listing.get("required_skills") or "[]"
    if isinstance(listing_skills_raw, str):
        try:
            listing_skills = json.loads(listing_skills_raw)
        except (json.JSONDecodeError, TypeError):
            listing_skills = []
    else:
        listing_skills = listing_skills_raw

    eng_skills = set(engineer.get("skills") or [])
    listing_skill_set = set(listing_skills)

    if not listing_skill_set:
        skill_score = 25  # 中間値
    elif not eng_skills:
        skill_score = 0
    else:
        common = len(eng_skills & listing_skill_set)
        skill_score = round(common / len(listing_skill_set) * 50)

    # --- エリアマッチ (0〜25点) ---
    listing_area = (listing.get("work_area") or "").strip()
    eng_areas_raw = (engineer.get("preferred_areas") or "").strip()
    eng_areas = [a.strip() for a in eng_areas_raw.split(",") if a.strip()] if eng_areas_raw else []

    if not listing_area:
        area_score = 15  # 判定不能
    elif listing_area in eng_areas:
        area_score = 25
    elif "リモート" in listing_area or "フルリモート" in listing_area:
        area_score = 20
    elif not eng_areas:
        area_score = 15  # どこでもOK
    else:
        area_score = 0

    # --- 単価マッチ (0〜25点) ---
    l_min = listing.get("unit_price_min")
    l_max = listing.get("unit_price_max")
    e_min = engineer.get("desired_price_min") or engineer.get("current_price")
    e_max = engineer.get("desired_price_max") or engineer.get("current_price")

    if l_min is None and l_max is None:
        price_score = 15  # 案件側データなし
    elif e_min is None and e_max is None:
        price_score = 15  # エンジニア側データなし
    else:
        # 範囲の重なり判定
        r_min = l_min if l_min is not None else l_max
        r_max = l_max if l_max is not None else l_min
        e_lo = e_min if e_min is not None else e_max
        e_hi = e_max if e_max is not None else e_min
        if r_min <= e_hi and e_lo <= r_max:
            price_score = 25
        else:
            price_score = 0

    total = skill_score + area_score + price_score
    return {"skill": skill_score, "area": area_score, "price": price_score, "total": total}


def match_engineers_for_listing(listing_id: int, limit: int = 20) -> list[dict]:
    """案件に合うエンジニア一覧（待機中/面談中のみ、スコア降順）。"""
    with get_connection() as conn:
        listing_row = conn.execute(
            "SELECT * FROM job_listings WHERE id = ?", (listing_id,)
        ).fetchone()
        if not listing_row:
            return []
        listing = dict(listing_row)

        # 待機中・面談中のエンジニアを全件取得
        rows = conn.execute(
            "SELECT * FROM engineers WHERE status IN (?, ?)",
            ("待機中", "面談中"),
        ).fetchall()

        # 全エンジニアのスキルを一括取得
        eng_ids = [dict(r)["id"] for r in rows]
        skills_map: dict[int, list[str]] = {eid: [] for eid in eng_ids}
        if eng_ids:
            placeholders = ",".join("?" * len(eng_ids))
            sk_rows = conn.execute(
                f"SELECT engineer_id, skill_name FROM engineer_skills WHERE engineer_id IN ({placeholders})",
                eng_ids,
            ).fetchall()
            for sr in sk_rows:
                skills_map[sr["engineer_id"]].append(sr["skill_name"])

        # この案件に対する提案を一括取得
        prop_map: dict[int, dict] = {}
        prop_rows = conn.execute(
            "SELECT * FROM matching_proposals WHERE listing_id = ?",
            (listing_id,),
        ).fetchall()
        for pr in prop_rows:
            prop_map[pr["engineer_id"]] = dict(pr)

        results = []
        for row in rows:
            eng = dict(row)
            eng["skills"] = skills_map.get(eng["id"], [])
            score_detail = _calc_match_score(eng, listing)
            results.append({
                "engineer": eng,
                "score": score_detail["total"],
                "score_detail": {
                    "skill": score_detail["skill"],
                    "area": score_detail["area"],
                    "price": score_detail["price"],
                },
                "proposal": prop_map.get(eng["id"]),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]


def match_listings_for_engineer(engineer_id: int, limit: int = 20) -> list[dict]:
    """エンジニアに合う案件一覧（直近30日、スコア降順）。"""
    with get_connection() as conn:
        eng_row = conn.execute(
            "SELECT * FROM engineers WHERE id = ?", (engineer_id,)
        ).fetchone()
        if not eng_row:
            return []
        eng = dict(eng_row)

        # スキルを付与
        sk = conn.execute(
            "SELECT skill_name FROM engineer_skills WHERE engineer_id = ?",
            (engineer_id,),
        ).fetchall()
        eng["skills"] = [s["skill_name"] for s in sk]

        # 直近30日の案件 — スコア計算に必要な列だけ取得（高速化）
        if _USE_PG:
            date_cond = "created_at > NOW() - INTERVAL '30 days'"
        else:
            date_cond = "created_at > datetime('now', '-30 days')"
        rows = conn.execute(
            f"""SELECT id, required_skills, work_area, unit_price_min, unit_price_max
                FROM job_listings WHERE {date_cond}"""
        ).fetchall()

        # Pythonでスコア計算（DBクエリなし）
        scored: list[tuple[int, dict]] = []
        for row in rows:
            listing_slim = dict(row)
            score_detail = _calc_match_score(eng, listing_slim)
            scored.append((listing_slim["id"], score_detail))

        # スコア上位のIDだけ取得
        scored.sort(key=lambda x: x[1]["total"], reverse=True)
        top = scored[:limit]
        if not top:
            return []

        top_ids = [t[0] for t in top]
        score_map = {t[0]: t[1] for t in top}

        # 上位案件のフルデータを一括取得
        placeholders = ",".join("?" * len(top_ids))
        full_rows = conn.execute(
            f"SELECT * FROM job_listings WHERE id IN ({placeholders})",
            top_ids,
        ).fetchall()
        listing_map = {dict(r)["id"]: dict(r) for r in full_rows}

        # 上位の提案を一括取得
        prop_map: dict[int, dict] = {}
        prop_rows = conn.execute(
            f"SELECT * FROM matching_proposals WHERE engineer_id = ? AND listing_id IN ({placeholders})",
            [engineer_id] + top_ids,
        ).fetchall()
        for pr in prop_rows:
            prop_map[pr["listing_id"]] = dict(pr)

        # スコア順で結果を組み立て
        results = []
        for lid, sd in top:
            listing = listing_map.get(lid)
            if not listing:
                continue
            results.append({
                "listing": listing,
                "score": sd["total"],
                "score_detail": {"skill": sd["skill"], "area": sd["area"], "price": sd["price"]},
                "proposal": prop_map.get(lid),
            })

        return results


def insert_proposal(engineer_id: int, listing_id: int, score: int = 0, notes: str = "") -> Optional[int]:
    """提案レコードを作成する（UNIQUE制約で重複防止）。"""
    with get_connection() as conn:
        try:
            if conn.is_pg:
                cursor = conn.execute(
                    """INSERT INTO matching_proposals (engineer_id, listing_id, score, notes)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT (engineer_id, listing_id) DO NOTHING
                       RETURNING id""",
                    (engineer_id, listing_id, score, notes),
                )
                row = cursor.fetchone()
                return row["id"] if row else None
            else:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO matching_proposals
                       (engineer_id, listing_id, score, notes)
                       VALUES (?, ?, ?, ?)""",
                    (engineer_id, listing_id, score, notes),
                )
                return cursor.lastrowid if cursor.rowcount > 0 else None
        except Exception:
            return None


def update_proposal_status(proposal_id: int, status: str, notes: Optional[str] = None) -> bool:
    """提案ステータスを変更する。"""
    with get_connection() as conn:
        if notes is not None:
            if conn.is_pg:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, notes = ?, updated_at = NOW() WHERE id = ?",
                    (status, notes, proposal_id),
                )
            else:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, notes, proposal_id),
                )
        else:
            if conn.is_pg:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, updated_at = NOW() WHERE id = ?",
                    (status, proposal_id),
                )
            else:
                conn.execute(
                    "UPDATE matching_proposals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, proposal_id),
                )
        return True


def delete_proposal(proposal_id: int) -> bool:
    """提案を削除する。"""
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM matching_proposals WHERE id = ?", (proposal_id,)
        )
        return cursor.rowcount > 0


def get_proposals(
    status: Optional[str] = None,
    engineer_id: Optional[int] = None,
    listing_id: Optional[int] = None,
) -> list[dict]:
    """提案一覧（フィルター付き）。"""
    with get_connection() as conn:
        query = """
            SELECT mp.*,
                   e.name as engineer_name,
                   jl.company_name as listing_company
            FROM matching_proposals mp
            JOIN engineers e ON mp.engineer_id = e.id
            JOIN job_listings jl ON mp.listing_id = jl.id
            WHERE 1=1
        """
        params: list = []
        if status:
            query += " AND mp.status = ?"
            params.append(status)
        if engineer_id:
            query += " AND mp.engineer_id = ?"
            params.append(engineer_id)
        if listing_id:
            query += " AND mp.listing_id = ?"
            params.append(listing_id)
        query += " ORDER BY mp.updated_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_matching_stats() -> dict:
    """提案のKPI統計（ステータス別件数）。"""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM matching_proposals GROUP BY status"
        ).fetchall()
        by_status = {r["status"]: r["cnt"] for r in rows}
        total = sum(by_status.values())
    return {
        "total": total,
        "candidate": by_status.get("候補", 0),
        "proposed": by_status.get("提案済み", 0),
        "interviewing": by_status.get("面談中", 0),
        "closed": by_status.get("成約", 0),
        "rejected": by_status.get("見送り", 0),
    }
