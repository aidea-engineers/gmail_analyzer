import streamlit as st
import pandas as pd
from core.database import get_fetch_logs, get_connection, init_db
from core.mock_data import generate_and_insert, clear_all_data
from core.gmail_client import is_authenticated, get_gmail_service
from core.batch_processor import run_full_pipeline, run_extraction_only
from config import Config

st.header("📧 メール取得・処理")

# --- Gmail接続状態 ---
gmail_connected = is_authenticated()
if gmail_connected:
    st.success("Gmail: 接続済み")
else:
    st.warning("Gmail: 未接続（設定ページからGmailを接続してください）")

st.divider()

# --- メール取得・処理 ---
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("メール取得・AI解析 実行", type="primary", disabled=not gmail_connected):
        service = get_gmail_service()
        if service:
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(status):
                total = status.get("total", 1)
                current = status.get("current", 0)
                if total > 0:
                    progress_bar.progress(min(current / total, 1.0))
                status_text.text(status.get("message", ""))

            with st.spinner("処理中..."):
                result = run_full_pipeline(
                    gmail_service=service, progress_callback=update_progress
                )

            progress_bar.empty()
            status_text.empty()

            if result.status == "completed":
                st.success(
                    f"完了: 取得 {result.emails_fetched}件 / "
                    f"処理 {result.emails_processed}件 / "
                    f"案件 {result.listings_created}件"
                )
            else:
                st.error(f"エラーが発生しました: {', '.join(result.errors[:3])}")

with col2:
    if st.button("未処理メールをAI解析", disabled=not Config.GEMINI_API_KEY):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress_extract(status):
            total = status.get("total", 1)
            current = status.get("current", 0)
            if total > 0:
                progress_bar.progress(min(current / total, 1.0))
            status_text.text(status.get("message", ""))

        with st.spinner("AI解析中..."):
            result = run_extraction_only(progress_callback=update_progress_extract)

        progress_bar.empty()
        status_text.empty()

        if result.status == "completed":
            st.success(
                f"完了: 処理 {result.emails_processed}件 / 案件 {result.listings_created}件"
            )
        else:
            st.error(f"エラー: {', '.join(result.errors[:3])}")

with col3:
    pass  # 空きスペース

st.divider()

# --- モックデータ管理（プロトタイプ用） ---
st.subheader("モックデータ（プロトタイプ用）")
st.caption("Gmail接続前にUIの動作確認ができます")

mock_col1, mock_col2, mock_col3 = st.columns(3)

with mock_col1:
    mock_count = st.number_input("生成件数", min_value=10, max_value=500, value=150, step=10)

with mock_col2:
    if st.button("モックデータ投入"):
        with st.spinner("モックデータ生成中..."):
            inserted = generate_and_insert(count=mock_count)
        st.success(f"モックデータ {inserted}件を投入しました")
        st.rerun()

with mock_col3:
    if st.button("全データ削除", type="secondary"):
        clear_all_data()
        st.warning("全データを削除しました")
        st.rerun()

st.divider()

# --- 処理統計 ---
st.subheader("データ統計")
with get_connection() as conn:
    email_count = conn.execute("SELECT COUNT(*) as cnt FROM emails").fetchone()["cnt"]
    processed_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM emails WHERE is_processed = 1"
    ).fetchone()["cnt"]
    unprocessed_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM emails WHERE is_processed = 0"
    ).fetchone()["cnt"]
    listing_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM job_listings"
    ).fetchone()["cnt"]

stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
with stat_col1:
    st.metric("総メール数", email_count)
with stat_col2:
    st.metric("処理済み", processed_count)
with stat_col3:
    st.metric("未処理", unprocessed_count)
with stat_col4:
    st.metric("抽出済み案件", listing_count)

st.divider()

# --- 取得ログ ---
st.subheader("取得ログ")
logs = get_fetch_logs(limit=10)

if logs:
    log_rows = []
    for log in logs:
        log_rows.append(
            {
                "日時": log.get("started_at", ""),
                "完了": log.get("finished_at", ""),
                "取得数": log.get("emails_fetched", 0),
                "処理数": log.get("emails_processed", 0),
                "ステータス": log.get("status", ""),
            }
        )
    st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)
else:
    st.info("取得ログはまだありません")
