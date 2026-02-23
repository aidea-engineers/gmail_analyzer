from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional

from config import Config

logger = logging.getLogger(__name__)


def _load_credentials_from_env():
    """環境変数からOAuth認証情報を読み込む"""
    from google.oauth2.credentials import Credentials

    token_json = Config.GMAIL_TOKEN_JSON
    if not token_json:
        return None
    try:
        return Credentials.from_authorized_user_info(
            json.loads(token_json),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
    except Exception as e:
        logger.warning(f"環境変数からのトークン読み込みエラー: {e}")
        return None


def _load_credentials_from_file():
    """ファイルからOAuth認証情報を読み込む"""
    from google.oauth2.credentials import Credentials

    token_path = Config.GMAIL_TOKEN_PATH
    if not token_path.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(
            str(token_path),
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
    except Exception as e:
        logger.warning(f"トークン読み込みエラー: {e}")
        return None


def is_authenticated() -> bool:
    """Gmail OAuth トークンが有効か確認する（期限切れならリフレッシュを試みる）"""
    from google.auth.transport.requests import Request

    creds = _load_credentials_from_env() or _load_credentials_from_file()
    if creds is None:
        return False
    if creds.valid:
        return True
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            return creds.valid
        except Exception as e:
            logger.warning(f"トークンリフレッシュ失敗: {e}")
            return False
    return False


def get_gmail_service():
    """Gmail API サービスオブジェクトを取得する"""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    # 1) トークンを読み込む（環境変数優先 → ファイル）
    creds = _load_credentials_from_env() or _load_credentials_from_file()

    # 2) 期限切れならリフレッシュ
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            logger.error(f"トークンリフレッシュエラー: {e}")
            creds = None

    # 3) 有効なトークンがなければ新規認証フロー
    if not creds or not creds.valid:
        credentials_json = Config.GMAIL_CREDENTIALS_JSON
        credentials_path = Config.GMAIL_CREDENTIALS_PATH

        if credentials_json:
            try:
                flow = InstalledAppFlow.from_client_config(
                    json.loads(credentials_json), SCOPES
                )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"環境変数からのOAuth認証エラー: {e}")
                return None
        elif credentials_path.exists():
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"OAuth認証エラー: {e}")
                return None
        else:
            logger.error("OAuth credentials が設定されていません")
            return None

    # 4) トークンをファイルに保存（ファイルベース認証の場合のみ）
    if not Config.GMAIL_TOKEN_JSON:
        token_path = Config.GMAIL_TOKEN_PATH
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(token_path), "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def build_query(
    labels: list[str] | None = None,
    keywords: list[str] | None = None,
    after_date: str | None = None,
) -> str:
    """Gmail検索クエリを構築する"""
    parts = []

    labels = labels or Config.GMAIL_LABELS
    keywords = keywords or Config.GMAIL_KEYWORDS

    for label in labels:
        if label:
            parts.append(f"label:{label}")

    if keywords:
        keyword_clause = " OR ".join(keywords)
        parts.append(f"({keyword_clause})")

    if after_date:
        parts.append(f"after:{after_date}")

    return " ".join(parts)


def fetch_message_ids(service, query: str, max_results: int = 500) -> list[str]:
    """Gmail APIからメッセージIDリストを取得する"""
    message_ids = []
    page_token = None

    while len(message_ids) < max_results:
        batch_size = min(100, max_results - len(message_ids))
        try:
            result = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=batch_size,
                    pageToken=page_token,
                )
                .execute()
            )
        except Exception as e:
            logger.error(f"メッセージリスト取得エラー: {e}")
            break

        messages = result.get("messages", [])
        message_ids.extend(m["id"] for m in messages)

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return message_ids


def fetch_message_detail(service, message_id: str) -> Optional[dict]:
    """1件のメッセージの詳細を取得する"""
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
    except Exception as e:
        logger.error(f"メッセージ詳細取得エラー (ID: {message_id}): {e}")
        return None

    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

    subject = headers.get("subject", "")
    sender = headers.get("from", "")
    date_str = headers.get("date", "")

    received_at = None
    if date_str:
        try:
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            pass

    body_text = _extract_body(msg.get("payload", {}))
    labels = ",".join(msg.get("labelIds", []))

    return {
        "gmail_message_id": message_id,
        "subject": subject,
        "sender": sender,
        "received_at": received_at.isoformat() if received_at else None,
        "body_text": body_text,
        "labels": labels,
    }


def _extract_body(payload: dict) -> str:
    """メールペイロードからテキスト本文を抽出する"""
    from utils.text_helpers import strip_html

    # 単一パート
    if "body" in payload and payload["body"].get("data"):
        data = payload["body"]["data"]
        text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        mime_type = payload.get("mimeType", "")
        if "html" in mime_type:
            return strip_html(text)
        return text

    # マルチパート
    parts = payload.get("parts", [])
    text_parts = []
    html_parts = []

    for part in parts:
        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data", "")

        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if "plain" in mime_type:
                text_parts.append(decoded)
            elif "html" in mime_type:
                html_parts.append(decoded)

        # ネストしたマルチパート
        if "parts" in part:
            nested = _extract_body(part)
            if nested:
                text_parts.append(nested)

    if text_parts:
        return "\n".join(text_parts)
    if html_parts:
        return strip_html("\n".join(html_parts))

    return ""


def fetch_and_store_emails(
    service, progress_callback=None
) -> int:
    """Gmailからメールを取得してDBに保存する。保存件数を返す。"""
    from core.database import insert_email, get_connection

    # 直近のデータ取得日以降のメールを取得
    after_date = None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(received_at) as latest FROM emails"
        ).fetchone()
        if row and row["latest"]:
            latest = row["latest"]
            if isinstance(latest, datetime):
                after_date = latest.strftime("%Y/%m/%d")
            else:
                after_date = str(latest)[:10].replace("-", "/")

    query = build_query(after_date=after_date)
    logger.info(f"Gmail検索クエリ: {query}")

    if progress_callback:
        progress_callback(
            {"phase": "fetch", "current": 0, "total": 0, "message": f"メール検索中: {query}"}
        )

    message_ids = fetch_message_ids(service, query, max_results=Config.MAX_EMAILS_PER_FETCH)
    total = len(message_ids)

    if progress_callback:
        progress_callback(
            {"phase": "fetch", "current": 0, "total": total, "message": f"{total}件のメールを取得中..."}
        )

    stored = 0
    for i, msg_id in enumerate(message_ids):
        detail = fetch_message_detail(service, msg_id)
        if detail:
            result = insert_email(
                gmail_message_id=detail["gmail_message_id"],
                subject=detail["subject"],
                sender=detail["sender"],
                received_at=detail["received_at"],
                body_text=detail["body_text"],
                labels=detail["labels"],
            )
            if result:
                stored += 1

        if progress_callback and (i + 1) % 10 == 0:
            progress_callback(
                {
                    "phase": "fetch",
                    "current": i + 1,
                    "total": total,
                    "message": f"メール取得中: {i + 1}/{total} (新規: {stored}件)",
                }
            )

    return stored
