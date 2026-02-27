from __future__ import annotations

import json
import time
import logging
from typing import Optional

from google import genai
from google.genai import types

from config import Config
from models.schemas import JobListingExtraction, EmailExtractionResult
from utils.text_helpers import (
    clean_email_body,
    truncate_for_gemini,
    normalize_skill_name,
    normalize_area,
    extract_company_from_sender,
    extract_company_from_signature,
    _extract_domain_company,
    _company_name_quality,
)

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """あなたはSES（システムエンジニアリングサービス）の案件情報を抽出する専門AIです。

以下のメールから案件情報を正確に抽出してください。
**1通のメールに複数案件が含まれる場合は、すべて個別に抽出してlistingsに格納してください。**

## is_job_listing（案件判定）
各案件について以下の条件で判定する:
- true: エンジニアを募集しているSES案件情報（プロジェクトに人を探している）
- false: 以下のようなメールは必ずfalseにすること
  - 人材紹介・要員提案メール（「弊社エンジニアをご紹介」「○○さんをご提案」等、人を売り込んでいるメール）
  - 営業メール、広告、ニュースレター
  - 案件情報が含まれないメール
案件でない場合はis_job_listing=falseの要素を1つだけ返してください。

## company_name（会社名）＝メール送信元の企業名
**メールを送ってきた企業（送信者の所属企業）の正式名称を記載すること。**
送信者名「{sender}」から企業名を抽出して使用する。
**必ず「株式会社」「合同会社」等の法人格を含めた正式名称で記載すること。**
例: ○「株式会社ABC」 ✕「ABC」 ✕「abc」
送信者名がドメイン断片（例: ses, proud-g, code-d）や人名のみの場合は、メール本文末尾の署名欄・フッターから送信者の所属企業名（法人格付き）を探して記載すること。
本文中に記載された案件先・クライアント企業名は使用しないこと（それはproject_detailsに含める）。
「○○サービス運営企業」のような案件先の説明をcompany_nameに入れてはいけない。
**必ず送信者の企業名のみを記載すること。担当者名・部署名は含めないこと。**
例: ○「株式会社ABC」 ✕「株式会社ABC 田中」 ✕「株式会社ABC営業部」

## work_area（エリア/勤務地）
以下のカテゴリから最も適切なものを選択すること（駅名や住所ではなく大分類で記載）:
- 東京23区
- 埼玉
- 千葉
- 神奈川
- 大阪
- 大阪近郊（京都・奈良・兵庫）
- 名古屋
- 愛知（名古屋除く）
- 福岡
- フルリモート
- その他（具体的な地域名を記載）

リモートワークがある場合の記載ルール:
- 完全リモート/フルリモート → 「フルリモート」
- リモート併用（出社あり） → 「リモート（東京23区）」のように「リモート（エリア名）」形式
- 複数エリアの場合はカンマ区切り（例: 「東京23区, 大阪」）

## その他のフィールド
- unit_price: 原文のまま（例: "55-65万", "〜80万円/月"）
- unit_price_min: 万円単位の整数の下限（例: 55）。不明ならnull
- unit_price_max: 万円単位の整数の上限（例: 65）。単一数値ならmin=max。不明ならnull
- required_skills: 言語・フレームワーク・ツール名を個別にリスト化。正式名称で記載
- project_details: 業務内容・要件を簡潔に要約（100文字以内）
- requirements: 必須要件・求める人物像を記載。メール本文に必須スキル・経験年数・資格・求める人物像が明記されていればそのまま抽出する。明記されていない場合は、業務内容から「このような経験・スキルが必要」と推測して記載する（200文字以内）
- job_type: 募集職種名（例: バックエンドエンジニア, PM, SE）
- confidence: 情報の確実性（0.0-1.0）。明確に記載があれば高く、推測が多ければ低く
- start_month: 参画開始時期（例: "2026年4月", "即日"）。記載なしならnull

## メール送信者:
{sender}

## メール件名:
{subject}

## メール本文:
{body}
"""


def _get_client() -> genai.Client:
    """Gemini APIクライアントを取得（60秒タイムアウト付き）"""
    return genai.Client(
        api_key=Config.GEMINI_API_KEY,
        http_options={"timeout": 60_000},
    )


def extract_from_email(
    subject: str, body_text: str, sender: str = ""
) -> Optional[list[JobListingExtraction]]:
    """1件のメールからSES案件情報を抽出する（複数案件対応）

    Returns:
        案件リスト。APIエラー時はNone。
    """
    if not Config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY が設定されていません")
        return None

    # 署名を保持してGeminiに渡す（署名から会社名を抽出させるため）
    cleaned_body = clean_email_body(body_text, keep_signature=True)
    truncated_body = truncate_for_gemini(cleaned_body)

    prompt = EXTRACTION_PROMPT.format(
        subject=subject, body=truncated_body, sender=sender
    )

    client = _get_client()

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EmailExtractionResult,
                    temperature=0.1,
                ),
            )

            result = EmailExtractionResult.model_validate_json(response.text)

            # 後処理: スキル正規化 + エリア正規化 + 社名補正
            sender_company = extract_company_from_sender(sender)
            sig_company = extract_company_from_signature(body_text)
            domain_company = _extract_domain_company(sender)
            for listing in result.listings:
                listing.required_skills = [
                    normalize_skill_name(s) for s in listing.required_skills
                ]
                if listing.work_area:
                    listing.work_area = normalize_area(listing.work_area)
                # 会社名の品質ベース優先順位:
                # 各ソースの品質スコアを比較し、最も高いものを採用
                # 署名(法人格付き) > sender(法人格付き) > Gemini結果 > sender(普通) > ドメイン
                candidates = []
                if sig_company:
                    candidates.append((_company_name_quality(sig_company), sig_company))
                if sender_company:
                    candidates.append((_company_name_quality(sender_company), sender_company))
                gemini_company = listing.company_name or ""
                if gemini_company:
                    candidates.append((_company_name_quality(gemini_company), gemini_company))
                if domain_company:
                    candidates.append((_company_name_quality(domain_company), domain_company))

                if candidates:
                    # 品質スコアが最も高いものを選択
                    best_quality, best_name = max(candidates, key=lambda x: x[0])
                    if best_name:
                        listing.company_name = best_name

            return result.listings

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
