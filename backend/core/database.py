"""database.py — ファサード（後方互換性維持）

全関数を分割先モジュールから再エクスポートする。
既存の `from core.database import xxx` は一切変更不要。

分割先:
  - db_core.py      : 接続・スキーマ・マイグレーション
  - db_listings.py  : メール・案件・ダッシュボード集計・Fetchログ
  - db_engineers.py : エンジニア・スキル・担当案件
  - db_matching.py  : マッチング・提案
  - db_users.py     : ユーザー・取引先
"""

# --- db_core ---
from core.db_core import (  # noqa: F401
    get_connection,
    init_db,
    MIGRATIONS,
    _USE_PG,
    _safe_add_column,
)

# --- db_listings ---
from core.db_listings import (  # noqa: F401
    insert_email,
    get_existing_gmail_ids,
    get_unprocessed_emails,
    mark_email_processed,
    check_duplicate_listing,
    insert_job_listing,
    search_listings,
    get_skill_counts,
    get_price_distribution,
    get_area_counts,
    get_trend_data,
    get_total_stats,
    get_monthly_summary,
    get_distinct_skills,
    get_distinct_areas,
    get_distinct_job_types,
    get_distinct_companies,
    insert_fetch_log,
    update_fetch_log,
    get_fetch_logs,
    get_all_listings_with_sender,
    get_all_listings_with_sender_and_body,
    batch_update_company_names,
    cleanup_stale_fetch_logs,
    clear_old_email_bodies,
)

# --- db_engineers ---
from core.db_engineers import (  # noqa: F401
    insert_engineer,
    update_engineer,
    delete_engineer,
    get_engineer,
    create_engineer_self,
    save_engineer_careers,
    get_engineer_careers,
    search_engineers,
    get_engineer_stats,
    get_distinct_engineer_skills,
    get_distinct_engineer_areas,
    insert_assignment,
    delete_assignment,
)

# --- db_matching ---
from core.db_matching import (  # noqa: F401
    match_engineers_for_listing,
    match_listings_for_engineer,
    insert_proposal,
    update_proposal_status,
    delete_proposal,
    get_proposals,
    get_matching_stats,
)

# --- db_users ---
from core.db_users import (  # noqa: F401
    get_user_profile,
    get_user_profile_by_email,
    upsert_user_profile,
    list_user_profiles,
    delete_user_profile,
    create_invite_log,
    insert_company,
    search_companies,
)
