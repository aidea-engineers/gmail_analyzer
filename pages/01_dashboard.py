import streamlit as st
from core.database import (
    get_skill_counts,
    get_price_distribution,
    get_area_counts,
    get_trend_data,
    get_total_stats,
)
from utils.chart_helpers import (
    build_skill_bar_chart,
    build_price_histogram,
    build_area_pie_chart,
    build_trend_line_chart,
)
from utils.date_helpers import get_date_range

st.header("📊 SES案件ダッシュボード")

# --- 期間選択 ---
period = st.radio(
    "表示期間",
    ["7日", "30日", "90日", "全期間"],
    horizontal=True,
    index=1,
)
date_from, date_to = get_date_range(period)

# --- KPI指標 ---
stats = get_total_stats(date_from=date_from, date_to=date_to)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("総案件数", f"{stats['total']}件")
with col2:
    st.metric("平均単価", f"{stats['avg_price']}万円")
with col3:
    st.metric("本日の新着", f"{stats['today_count']}件")
with col4:
    st.metric("エリア数", f"{stats['area_count']}")

st.divider()

# --- グラフ 2x2 ---
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    skill_data = get_skill_counts(date_from=date_from, date_to=date_to)
    fig_skills = build_skill_bar_chart(skill_data)
    st.plotly_chart(fig_skills, use_container_width=True)

with chart_col2:
    price_data = get_price_distribution(date_from=date_from, date_to=date_to)
    fig_price = build_price_histogram(price_data)
    st.plotly_chart(fig_price, use_container_width=True)

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    area_data = get_area_counts(date_from=date_from, date_to=date_to)
    fig_area = build_area_pie_chart(area_data)
    st.plotly_chart(fig_area, use_container_width=True)

with chart_col4:
    granularity_label = st.radio(
        "トレンド粒度",
        ["日別", "週別"],
        horizontal=True,
        key="trend_granularity",
    )
    granularity = "weekly" if granularity_label == "週別" else "daily"
    trend_data = get_trend_data(
        granularity=granularity, date_from=date_from, date_to=date_to
    )
    fig_trend = build_trend_line_chart(trend_data, granularity=granularity_label)
    st.plotly_chart(fig_trend, use_container_width=True)
