import streamlit as st
import pandas as pd
import json
from core.database import (
    search_listings,
    get_distinct_skills,
    get_distinct_areas,
    get_distinct_job_types,
)
from utils.date_helpers import format_date_jp

st.header("🔍 案件検索")

# --- サイドバーにフィルタ ---
with st.sidebar:
    st.subheader("検索フィルタ")

    keyword = st.text_input("フリーワード検索", placeholder="会社名・スキル・内容など")

    available_skills = get_distinct_skills()
    selected_skills = st.multiselect("スキル", available_skills)

    available_areas = get_distinct_areas()
    selected_areas = st.multiselect("エリア", available_areas)

    available_job_types = get_distinct_job_types()
    selected_job_types = st.multiselect("職種", available_job_types)

    st.markdown("**単価範囲（万円/月）**")
    price_col1, price_col2 = st.columns(2)
    with price_col1:
        price_min = st.number_input("下限", min_value=0, max_value=200, value=0, step=5)
    with price_col2:
        price_max = st.number_input("上限", min_value=0, max_value=200, value=200, step=5)

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        date_from = st.date_input("開始日", value=None)
    with date_col2:
        date_to = st.date_input("終了日", value=None)

# --- 検索実行 ---
results = search_listings(
    keyword=keyword,
    skills=selected_skills if selected_skills else None,
    areas=selected_areas if selected_areas else None,
    job_types=selected_job_types if selected_job_types else None,
    price_min=price_min if price_min > 0 else None,
    price_max=price_max if price_max < 200 else None,
    date_from=date_from.isoformat() if date_from else None,
    date_to=f"{date_to.isoformat()} 23:59:59" if date_to else None,
)

st.markdown(f"**検索結果: {len(results)}件**")

if results:
    # DataFrameの構築
    rows = []
    for r in results:
        skills_list = r.get("required_skills", "[]")
        if isinstance(skills_list, str):
            try:
                skills_list = json.loads(skills_list)
            except json.JSONDecodeError:
                skills_list = []

        rows.append(
            {
                "日付": format_date_jp(r.get("created_at", "")),
                "会社名": r.get("company_name", ""),
                "職種": r.get("job_type", ""),
                "エリア": r.get("work_area", ""),
                "単価": r.get("unit_price", ""),
                "スキル": ", ".join(skills_list) if isinstance(skills_list, list) else str(skills_list),
                "案件内容": r.get("project_details", ""),
                "確信度": f'{r.get("confidence", 0):.0%}',
            }
        )

    df = pd.DataFrame(rows)

    # テーブル表示
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "日付": st.column_config.TextColumn("日付", width="small"),
            "会社名": st.column_config.TextColumn("会社名", width="medium"),
            "職種": st.column_config.TextColumn("職種", width="small"),
            "エリア": st.column_config.TextColumn("エリア", width="medium"),
            "単価": st.column_config.TextColumn("単価", width="small"),
            "スキル": st.column_config.TextColumn("スキル", width="large"),
            "案件内容": st.column_config.TextColumn("案件内容", width="large"),
            "確信度": st.column_config.TextColumn("確信度", width="small"),
        },
    )

    # 詳細表示
    st.subheader("案件詳細")
    for i, r in enumerate(results):
        skills_list = r.get("required_skills", "[]")
        if isinstance(skills_list, str):
            try:
                skills_list = json.loads(skills_list)
            except json.JSONDecodeError:
                skills_list = []

        with st.expander(
            f'{r.get("company_name", "不明")} - {r.get("job_type", "")} ({r.get("unit_price", "")})',
            expanded=False,
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**会社名:** {r.get('company_name', '')}")
                st.markdown(f"**職種:** {r.get('job_type', '')}")
                st.markdown(f"**エリア:** {r.get('work_area', '')}")
                st.markdown(f"**単価:** {r.get('unit_price', '')}")
            with col2:
                st.markdown(f"**スキル:** {', '.join(skills_list)}")
                st.markdown(f"**確信度:** {r.get('confidence', 0):.0%}")
                st.markdown(f"**受信日:** {format_date_jp(r.get('received_at', ''))}")
            st.markdown(f"**案件内容:** {r.get('project_details', '')}")
            if r.get("subject"):
                st.caption(f"メール件名: {r['subject']}")

    # CSVダウンロード
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="CSVダウンロード",
        data=csv,
        file_name="ses_listings.csv",
        mime="text/csv",
    )
else:
    st.info("条件に一致する案件がありません。フィルタを調整するか、メール取得ページでデータを投入してください。")
