import streamlit as st
from pathlib import Path
from config import Config
from core.gmail_client import is_authenticated, get_gmail_service

st.header("⚙️ 設定")

PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def load_env() -> dict:
    """現在の.envファイルを読み込む"""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def save_env(env: dict):
    """設定を.envファイルに保存する"""
    lines = []
    lines.append("# Gemini API")
    lines.append(f"GEMINI_API_KEY={env.get('GEMINI_API_KEY', '')}")
    lines.append(f"GEMINI_MODEL={env.get('GEMINI_MODEL', 'gemini-2.0-flash')}")
    lines.append("")
    lines.append("# Gmail")
    lines.append(f"GMAIL_CREDENTIALS_PATH={env.get('GMAIL_CREDENTIALS_PATH', 'credentials/credentials.json')}")
    lines.append(f"GMAIL_TOKEN_PATH={env.get('GMAIL_TOKEN_PATH', 'credentials/token.json')}")
    lines.append("")
    lines.append("# Filters")
    lines.append(f"GMAIL_LABELS={env.get('GMAIL_LABELS', '')}")
    lines.append(f"GMAIL_KEYWORDS={env.get('GMAIL_KEYWORDS', '案件,募集,エンジニア,SE,PG')}")
    lines.append("")
    lines.append("# Processing")
    lines.append(f"BATCH_SIZE={env.get('BATCH_SIZE', '50')}")
    lines.append(f"MAX_EMAILS_PER_FETCH={env.get('MAX_EMAILS_PER_FETCH', '500')}")
    lines.append(f"GEMINI_DELAY_SECONDS={env.get('GEMINI_DELAY_SECONDS', '1.0')}")
    lines.append("")
    lines.append("# Database")
    lines.append(f"DB_PATH={env.get('DB_PATH', 'data/gmail_analyzer.db')}")
    lines.append("")

    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")


# 現在の設定を読み込み
current_env = load_env()

# --- Gmail設定 ---
st.subheader("Gmail設定")

gmail_connected = is_authenticated()
if gmail_connected:
    st.success("Gmail: 接続済み")
else:
    st.warning("Gmail: 未接続")
    st.caption(
        "1. Google Cloud Consoleでプロジェクトを作成し、Gmail APIを有効化\n"
        "2. OAuth 2.0 クライアントID（デスクトップアプリ）を作成\n"
        "3. credentials.jsonをダウンロードして `credentials/` フォルダに配置\n"
        "4. 下のボタンでGmailに接続"
    )

    if st.button("Gmail接続"):
        with st.spinner("ブラウザでGoogleアカウントの認証を行ってください..."):
            service = get_gmail_service()
        if service:
            st.success("Gmail接続に成功しました")
            st.rerun()
        else:
            st.error("Gmail接続に失敗しました。credentials.jsonを確認してください。")

gmail_labels = st.text_input(
    "対象ラベル（カンマ区切り）",
    value=current_env.get("GMAIL_LABELS", "SES案件"),
    help="Gmail上のラベル名。複数の場合はカンマ区切り。",
)

gmail_keywords = st.text_input(
    "検索キーワード（カンマ区切り）",
    value=current_env.get("GMAIL_KEYWORDS", "案件,募集,エンジニア,SE,PG"),
    help="メール件名・本文の検索キーワード。OR条件で結合されます。",
)

st.divider()

# --- Gemini API設定 ---
st.subheader("Gemini API設定")

gemini_api_key = st.text_input(
    "APIキー",
    value=current_env.get("GEMINI_API_KEY", ""),
    type="password",
    help="Google AI StudioからGemini APIキーを取得してください。",
)

gemini_model = st.selectbox(
    "モデル",
    ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"],
    index=["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"].index(
        current_env.get("GEMINI_MODEL", "gemini-2.0-flash")
    )
    if current_env.get("GEMINI_MODEL", "gemini-2.0-flash")
    in ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
    else 0,
)

st.divider()

# --- 処理設定 ---
st.subheader("処理設定")

batch_size = st.number_input(
    "バッチサイズ",
    min_value=10,
    max_value=500,
    value=int(current_env.get("BATCH_SIZE", "50")),
    step=10,
    help="1回のAI解析で処理するメール数の上限",
)

max_emails = st.number_input(
    "最大メール取得数",
    min_value=50,
    max_value=2000,
    value=int(current_env.get("MAX_EMAILS_PER_FETCH", "500")),
    step=50,
    help="1回のGmail取得で取得するメール数の上限",
)

gemini_delay = st.number_input(
    "API呼び出し間隔（秒）",
    min_value=0.5,
    max_value=10.0,
    value=float(current_env.get("GEMINI_DELAY_SECONDS", "1.0")),
    step=0.5,
    help="Gemini API呼び出し間のウェイト。レート制限対策。",
)

st.divider()

# --- 保存ボタン ---
if st.button("設定を保存", type="primary"):
    new_env = {
        "GEMINI_API_KEY": gemini_api_key,
        "GEMINI_MODEL": gemini_model,
        "GMAIL_CREDENTIALS_PATH": current_env.get(
            "GMAIL_CREDENTIALS_PATH", "credentials/credentials.json"
        ),
        "GMAIL_TOKEN_PATH": current_env.get(
            "GMAIL_TOKEN_PATH", "credentials/token.json"
        ),
        "GMAIL_LABELS": gmail_labels,
        "GMAIL_KEYWORDS": gmail_keywords,
        "BATCH_SIZE": str(batch_size),
        "MAX_EMAILS_PER_FETCH": str(max_emails),
        "GEMINI_DELAY_SECONDS": str(gemini_delay),
        "DB_PATH": current_env.get("DB_PATH", "data/gmail_analyzer.db"),
    }
    save_env(new_env)
    st.success("設定を保存しました。アプリを再起動すると反映されます。")
    st.caption("ヒント: ブラウザを更新するか、Streamlitを再起動してください。")
