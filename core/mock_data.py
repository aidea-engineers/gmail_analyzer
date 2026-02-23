import random
import json
import uuid
from datetime import datetime, timedelta

from core.database import get_connection, init_db

# --- リアルなSES案件モックデータ定義 ---

COMPANIES = [
    "テクノプロ株式会社", "株式会社リクルートスタッフィング", "パーソルテクノロジースタッフ株式会社",
    "株式会社インテリジェンス", "アデコ株式会社", "株式会社VSN", "株式会社メイテック",
    "TIS株式会社", "SCSK株式会社", "富士ソフト株式会社", "株式会社NSD",
    "株式会社システナ", "株式会社DTS", "株式会社ラック", "株式会社ビジョナリー",
    "株式会社クロスキャット", "フューチャー株式会社", "株式会社ブレインパッド",
    "株式会社エクストリーム", "ギークス株式会社", "レバテック株式会社",
    "株式会社Branding Engineer", "株式会社PE-BANK", "株式会社ITプロパートナーズ",
]

AREAS = [
    "東京都千代田区", "東京都港区", "東京都渋谷区", "東京都新宿区", "東京都中央区",
    "東京都品川区", "東京都江東区", "東京都文京区", "東京都豊島区",
    "横浜市西区", "川崎市中原区", "大阪市北区", "大阪市中央区",
    "名古屋市中区", "福岡市博多区", "札幌市中央区",
    "リモート", "フルリモート", "一部リモート（週2出社）", "一部リモート（週3出社）",
]

SKILL_SETS = [
    # Web系
    (["Java", "Spring Boot", "MySQL", "AWS"], "バックエンドエンジニア", "ECサイトのバックエンド開発・API設計"),
    (["Java", "Spring Boot", "Oracle", "Linux"], "SE", "金融系基幹システムの保守開発"),
    (["Python", "Django", "PostgreSQL", "Docker"], "バックエンドエンジニア", "SaaS型業務管理システムの開発"),
    (["Python", "FastAPI", "AWS", "Terraform"], "バックエンドエンジニア", "マイクロサービスアーキテクチャの設計・開発"),
    (["React", "TypeScript", "Next.js", "AWS"], "フロントエンドエンジニア", "大手ECサイトのフロントエンド刷新"),
    (["React", "TypeScript", "Node.js", "GraphQL"], "フルスタックエンジニア", "HR Techプロダクトの新機能開発"),
    (["Vue.js", "TypeScript", "Nuxt.js", "Firebase"], "フロントエンドエンジニア", "BtoB SaaSのUI/UX改善・フロント開発"),
    (["Angular", "TypeScript", "Java", "AWS"], "フルスタックエンジニア", "物流管理システムのフルスタック開発"),
    (["PHP", "Laravel", "MySQL", "Docker"], "バックエンドエンジニア", "不動産ポータルサイトの機能追加"),
    (["Ruby", "Ruby on Rails", "PostgreSQL", "Redis"], "バックエンドエンジニア", "Fintechサービスの決済基盤開発"),
    (["Go", "Kubernetes", "AWS", "Terraform"], "SRE", "大規模Webサービスの信頼性向上・基盤構築"),
    (["Go", "gRPC", "Docker", "Kubernetes"], "バックエンドエンジニア", "動画配信プラットフォームのAPI開発"),
    # インフラ・クラウド系
    (["AWS", "Terraform", "Docker", "Linux"], "インフラエンジニア", "AWS環境構築・IaC推進プロジェクト"),
    (["AWS", "Azure", "Kubernetes", "Ansible"], "クラウドエンジニア", "マルチクラウド環境の設計・構築"),
    (["GCP", "Kubernetes", "Terraform", "Python"], "SRE", "GCP基盤上のSRE業務・監視体制構築"),
    (["Linux", "Docker", "Ansible", "Shell"], "インフラエンジニア", "オンプレミスからクラウドへの移行支援"),
    # データ系
    (["Python", "SQL", "Tableau", "AWS"], "データエンジニア", "データ基盤構築・BIダッシュボード開発"),
    (["Python", "Spark", "Airflow", "GCP"], "データエンジニア", "大規模データパイプラインの設計・構築"),
    (["Python", "TensorFlow", "AWS", "Docker"], "MLエンジニア", "レコメンドエンジンの開発・運用"),
    # モバイル
    (["Swift", "iOS", "Firebase", "Git"], "iOSエンジニア", "ヘルスケアアプリのiOS版開発"),
    (["Kotlin", "Android", "Firebase", "Git"], "Androidエンジニア", "決済アプリのAndroid版機能追加"),
    (["Flutter", "Dart", "Firebase", "REST API"], "モバイルエンジニア", "クロスプラットフォームアプリの新規開発"),
    # PM/PMO
    (["PM経験", "Agile", "Jira", "コミュニケーション"], "PM", "DXプロジェクトのマネジメント"),
    (["PMO経験", "Excel", "PowerPoint", "調整力"], "PMO", "大手金融機関のシステム刷新PMO支援"),
    # セキュリティ
    (["セキュリティ", "AWS", "Linux", "ネットワーク"], "セキュリティエンジニア", "SOC運用・脆弱性診断業務"),
]

PRICE_RANGES = [
    (40, 50), (45, 55), (50, 60), (50, 65), (55, 65),
    (55, 70), (60, 70), (60, 75), (65, 75), (65, 80),
    (70, 80), (70, 85), (75, 85), (75, 90), (80, 90),
    (80, 95), (85, 95), (85, 100), (90, 100), (90, 110),
    (95, 110), (100, 120),
]


def _generate_mock_email(idx: int, listing_date: datetime) -> dict:
    """1件分のモックメールデータを生成"""
    company = random.choice(COMPANIES)
    skills, job_type, details = random.choice(SKILL_SETS)
    area = random.choice(AREAS)
    price_min, price_max = random.choice(PRICE_RANGES)

    subject = f"【案件情報】{job_type}募集 {'/'.join(skills[:2])} {area} {price_min}〜{price_max}万"
    sender = f"info@{company.replace('株式会社', '').strip().lower()}.co.jp"

    body = f"""
いつもお世話になっております。
{company}の営業担当です。

下記案件のご紹介です。ご興味ございましたらお気軽にご連絡ください。

■案件概要
【職種】{job_type}
【内容】{details}
【必要スキル】{', '.join(skills)}
【単価】{price_min}〜{price_max}万円/月（スキル見合い）
【勤務地】{area}
【期間】長期（3ヶ月〜）
【面談】1回

ご検討のほどよろしくお願いいたします。
""".strip()

    return {
        "gmail_message_id": f"mock_{uuid.uuid4().hex[:16]}",
        "subject": subject,
        "sender": sender,
        "received_at": listing_date.isoformat(),
        "body_text": body,
        "labels": "SES案件",
        "company_name": company,
        "work_area": area,
        "unit_price": f"{price_min}〜{price_max}万円/月",
        "unit_price_min": price_min,
        "unit_price_max": price_max,
        "required_skills": skills,
        "project_details": details,
        "job_type": job_type,
        "confidence": round(random.uniform(0.75, 0.98), 2),
    }


def generate_and_insert(count: int = 150) -> int:
    """モックデータを生成してDBに投入する。投入件数を返す。"""
    init_db()
    now = datetime.now()
    inserted = 0

    with get_connection() as conn:
        for i in range(count):
            # 過去30日間でランダムな日時
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            listing_date = now - timedelta(days=days_ago, hours=hours_ago)

            mock = _generate_mock_email(i, listing_date)

            # emails テーブルに挿入
            try:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO emails
                       (gmail_message_id, subject, sender, received_at, body_text, labels, is_processed)
                       VALUES (?, ?, ?, ?, ?, ?, 1)""",
                    (
                        mock["gmail_message_id"],
                        mock["subject"],
                        mock["sender"],
                        mock["received_at"],
                        mock["body_text"],
                        mock["labels"],
                    ),
                )
                if cursor.rowcount == 0:
                    continue
                email_id = cursor.lastrowid
            except Exception:
                continue

            # job_listings テーブルに挿入
            skills_json = json.dumps(mock["required_skills"], ensure_ascii=False)
            raw_json = json.dumps(mock, ensure_ascii=False, default=str)

            cursor = conn.execute(
                """INSERT INTO job_listings
                   (email_id, company_name, work_area, unit_price,
                    unit_price_min, unit_price_max, required_skills,
                    project_details, job_type, raw_extraction, confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email_id,
                    mock["company_name"],
                    mock["work_area"],
                    mock["unit_price"],
                    mock["unit_price_min"],
                    mock["unit_price_max"],
                    skills_json,
                    mock["project_details"],
                    mock["job_type"],
                    raw_json,
                    mock["confidence"],
                    listing_date.isoformat(),
                ),
            )
            listing_id = cursor.lastrowid

            # skills テーブルに挿入
            for skill in mock["required_skills"]:
                conn.execute(
                    "INSERT INTO skills (listing_id, skill_name) VALUES (?, ?)",
                    (listing_id, skill),
                )

            inserted += 1

    return inserted


def clear_all_data():
    """全データを削除する"""
    with get_connection() as conn:
        conn.execute("DELETE FROM skills")
        conn.execute("DELETE FROM job_listings")
        conn.execute("DELETE FROM emails")
        conn.execute("DELETE FROM fetch_log")
