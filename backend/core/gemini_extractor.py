from __future__ import annotations

import json
import time
import logging
from typing import Optional

from google import genai
from google.genai import types

from config import Config
from models.schemas import JobListingExtraction
from utils.text_helpers import clean_email_body, truncate_for_gemini, normalize_skill_name

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """あなたはSES（システムエンジニアリングサービス）の案件情報を抽出する専門AIです。

以下のメールから案件情報を正確に抽出してください。

## 抽出ルール:
1. company_name（会社名）: メール送信元や本文中の企業名。不明な場合はnull
2. work_area（エリア/勤務地）: 具体的な場所。「リモート」「フルリモート」も含む。複数ある場合はカンマ区切り
3. unit_price（単価）: 原文のまま抽出（例: "55-65万", "〜80万円/月"）
4. unit_price_min: 数値の下限を万円単位の整数で（例: 55）。不明ならnull
5. unit_price_max: 数値の上限を万円単位の整数で（例: 65）。単一の数値の場合はmin=maxとする。不明ならnull
6. required_skills: プログラミング言語、フレームワーク、ツール名を個別にリスト化。正式名称で記載
7. project_details: 業務内容・要件を簡潔に要約（100文字以内）
8. job_type: 募集職種名を抽出（例: バックエンドエンジニア, PM, SE）
9. confidence: 情報の確実性（0.0-1.0）。明確に記載があれば高く、推測が多ければ低く
10. is_job_listing: SES案件情報でない場合（広告、ニュースレター、営業メール等）はfalse

## メール件名:
{subject}

## メール本文:
{body}
"""


def _get_client() -> genai.Client:
    """Gemini APIクライアントを取得"""
    return genai.Client(api_key=Config.GEMINI_API_KEY)


def extract_from_email(
    subject: str, body_text: str
) -> Optional[JobListingExtraction]:
    """1件のメールからSES案件情報を抽出する"""
    if not Config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY が設定されていません")
        return None

    cleaned_body = clean_email_body(body_text)
    truncated_body = truncate_for_gemini(cleaned_body)

    prompt = EXTRACTION_PROMPT.format(subject=subject, body=truncated_body)

    client = _get_client()

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=JobListingExtraction,
                    temperature=0.1,
                ),
            )

            result = JobListingExtraction.model_validate_json(response.text)

            # スキル名を正規化
            result.required_skills = [
                normalize_skill_name(s) for s in result.required_skills
            ]

            return result

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "resource" in error_str:
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    f"レート制限 (attempt {attempt + 1}/{max_retries}), {wait_time}秒待機..."
                )
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"Gemini API エラー: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None

    logger.error("最大リトライ回数に達しました")
    return None


def extract_batch(
    emails: list[dict],
    progress_callback=None,
) -> list[tuple[int, Optional[JobListingExtraction]]]:
    """複数メールをバッチ処理で抽出する"""
    results = []
    total = len(emails)

    for i, email in enumerate(emails):
        email_id = email["id"]
        subject = email.get("subject", "")
        body = email.get("body_text", "")

        extraction = extract_from_email(subject, body)
        results.append((email_id, extraction))

        if progress_callback:
            progress_callback(
                {
                    "phase": "extraction",
                    "current": i + 1,
                    "total": total,
                    "message": f"AI解析中: {i + 1}/{total} メール",
                }
            )

        # レート制限対策
        if i < total - 1:
            time.sleep(Config.GEMINI_DELAY_SECONDS)

    return results
