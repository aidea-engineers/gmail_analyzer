import streamlit as st
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from core.database import init_db

st.set_page_config(
    page_title="SES案件アナライザー",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# DB初期化
init_db()

# ページ定義
dashboard = st.Page("pages/01_dashboard.py", title="ダッシュボード", icon="📊", default=True)
search = st.Page("pages/02_search.py", title="案件検索", icon="🔍")
email_fetch = st.Page("pages/03_email_fetch.py", title="メール取得", icon="📧")
settings = st.Page("pages/04_settings.py", title="設定", icon="⚙️")

pg = st.navigation(
    {
        "メイン": [dashboard, search],
        "管理": [email_fetch, settings],
    }
)

pg.run()
