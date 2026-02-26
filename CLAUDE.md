# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

SES案件メールを自動解析し、案件情報を可視化するWebダッシュボードシステム。
`cloudlink.company@gmail.com` に届くメールをGmail API経由で取得 → Gemini AIで解析 → スキル別・単価別・エリア別に一覧化。

## 技術スタック

- **フロントエンド**: Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 + Recharts 3
- **バックエンド**: FastAPI (Python) + Pydantic 2
- **データベース**: PostgreSQL (Supabase本番) / SQLite (ローカル開発フォールバック)
- **外部API**: Gmail API, Google Gemini API (`gemini-2.5-flash`)
- **デプロイ**: Vercel (フロントエンド) + Render (バックエンド) + Supabase (DB)
- **自動実行**: GitHub Actions (cron 1日5回)

## 開発コマンド

### バックエンド

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger UI: http://localhost:8000/docs
- Health check: `GET /api/health`
- テストフレームワーク: 未導入（pytest等なし）
- Linter: 未設定（flake8/black等なし）

### フロントエンド

```bash
cd frontend
npm install
npm run dev      # 開発サーバー (localhost:3000)
npm run build    # 本番ビルド + TypeScriptチェック
npm run lint     # ESLint (flat config v9, next/core-web-vitals + typescript)
```

バックエンドが `localhost:8000` で起動している必要あり（または `NEXT_PUBLIC_API_URL` で変更）。

### Git操作（WSLからの場合）

WSLではGitHub認証が未設定のため、Windows側のGitを使う：
```bash
/mnt/c/Program\ Files/Git/bin/git.exe -C "C:/Users/shimi/OneDrive/Desktop/VScode/AIdea Engineers事業全管理システム/gmail_analyzer" push origin main
```

## アーキテクチャ

### データフロー

```
Gmail API → メール取得 → DB保存 → Gemini AI解析 → 案件情報抽出 → DB保存
                                                                    ↓
フロントエンド ← REST API ← FastAPIルーター ← SQLクエリ ← PostgreSQL/SQLite
```

### バックエンド構成 (`backend/`)

**エントリポイント** (`main.py`):
- FastAPI app。起動時に `init_db()` + `cleanup_stale_fetch_logs()` を実行
- CORS: `Config.CORS_ORIGINS`（カンマ区切り環境変数）から動的設定

**ルーター** (4つのAPIグループ):
- `routers/dashboard.py` — `/api/dashboard/{kpis,charts}` 集計・チャート
- `routers/search.py` — `/api/search/{filters,listings,export}` 検索・CSV出力
- `routers/fetch.py` — `/api/fetch/{status,full-pipeline,ai-only,cron,progress,reanalyze-old}` パイプライン制御。重複実行防止ロック付き（409で拒否）
- `routers/settings.py` — `/api/settings` 設定

**コアモジュール**:
- `core/database.py` — デュアルDB対応。`DATABASE_URL`環境変数ありでPostgreSQL、なしでSQLite。`_DBWrapper`がプレースホルダ(`?`→`%s`)を自動変換。マイグレーションは `init_db()` 内の `ALTER TABLE` で実施（カラム追加時はここにtry/exceptブロックを追加）
- `core/gmail_client.py` — Gmail OAuth認証（環境変数トークン優先、ファイルフォールバック）、インクリメンタルフェッチ（`MAX(received_at)`以降のみ取得）
- `core/gemini_extractor.py` — Gemini APIで案件情報抽出。JSON mode + Pydantic `EmailExtractionResult` スキーマ。429エラー時は指数バックオフリトライ(3回)。60秒タイムアウト。後処理でスキル正規化・エリア正規化・会社名をsenderから強制設定
- `core/batch_processor.py` — `run_full_pipeline()`(Gmail取得+AI解析)と`run_extraction_only()`(AI解析のみ)。progress_callbackでSSE進捗通知。1メール→複数案件対応

**ユーティリティ** (`utils/`):
- `text_helpers.py` — メール本文クリーニング（HTML除去, 引用削除, 30,000字truncate）、スキル名正規化（60+マッピング）、エリア正規化（東京23区/埼玉/千葉等の大分類マッピング）、sender解析（`extract_company_from_sender()`）
- `date_helpers.py` — 期間文字列→日付範囲変換、JST表示フォーマット
- `chart_helpers.py` — 旧Streamlit UI用（現在未使用、Rechartsに移行済み）

**スキーマ** (`models/schemas.py`):
- `JobListingExtraction` — Gemini抽出結果（company_name, work_area, unit_price, required_skills, project_details, requirements, job_type, confidence, start_month, is_job_listing）
- `EmailExtractionResult` — 1メール→複数案件のラッパー（`listings: list[JobListingExtraction]`）
- `BatchResult` — パイプライン処理結果

**設定** (`config.py`):
- 全設定を環境変数から読み込み。`.env`ファイル対応（python-dotenv）

### フロントエンド構成 (`frontend/`)

- App Router、全ページ `"use client"` (CSR)
- `src/lib/api.ts` — `fetchAPI<T>()`ラッパー（`NEXT_PUBLIC_API_URL`でバックエンドURL指定）
- `src/types/index.ts` — 全APIレスポンスのTypeScript型定義
- `src/components/charts/` — Recharts 4種（スキル棒、単価ヒストグラム、エリア円、トレンド折れ線）
- SSE進捗追跡: EventSourceで`/api/fetch/progress/{jobId}`をリアルタイム受信
- スタイル: Tailwindクラス + CSS変数（`var(--card-bg)`, `var(--border)`, `var(--primary)`等）をinline styleで使用

### DBスキーマ（主要テーブル）

- `emails` — gmail_message_id(UNIQUE), subject, sender, body_text, received_at, is_processed
- `job_listings` — email_id(FK), company_name, work_area, unit_price, unit_price_min/max, required_skills(JSON), project_details, requirements, job_type, raw_extraction, confidence, start_month
- `skills` — listing_id(FK), skill_name（正規化済み）
- `fetch_log` — started_at, status, emails_fetched, emails_processed, errors(JSON)。サーバー起動時にスタックした"running"ログを自動クリーンアップ（10分超→"failed (stale)"）

新カラム追加時: `database.py` の `init_db()` 内に `ALTER TABLE ... ADD COLUMN` のtry/exceptブロックを追加する。PG/SQLiteの両スキーマ定義も更新すること。

### 自動実行 (GitHub Actions)

- `.github/workflows/scheduled-fetch.yml` — 1日5回（JST 9,12,15,18,21時）
- Renderサーバー起床(60秒待機) → `POST /api/fetch/cron`(Bearer認証) → バックグラウンドで処理
- Keep-aliveループ: 30秒間隔でstatus確認、未処理0またはスタック検出で終了（最大20分）
- cron実行時は未処理が0になるまでBATCH_SIZE(200件)ずつループ解析（手動UIは1バッチのみ）
- 手動実行も可能（workflow_dispatch）

## 本番環境

| サービス | URL | プラン |
|---------|-----|--------|
| Vercel | `https://gmail-analyzer-nu.vercel.app` | Hobby (¥0) |
| Render | `https://gmail-analyzer-api.onrender.com` | Starter ($7/月) |
| Supabase | (内部接続) | Free (¥0) |
| GitHub | `aidea-engineers/gmail_analyzer` | Free Org (¥0) |

- GitHubプッシュで Vercel/Render 自動デプロイ
- Render Starterプラン（$7/月）: スリープなし、常時稼働。スタックしたfetch_logは起動時に自動クリーンアップ
- リポジトリはPublic（Vercel Hobby制約）

## 開発時の注意事項

- `credentials/`フォルダは.gitignore対象。GitHubにアップしない
- ローカル開発はSQLite（DATABASE_URL未設定時）、本番はSupabase PostgreSQL
- Gemini解析はBATCH_SIZE(200)件ずつ。手動UIは1バッチのみ、cron実行時は自動ループで全件処理
- 実際のメール量: 1日約1,000件（Supabase無料500MBは約4ヶ月で上限到達見込み）
- 情報管理: 実データの取得・閲覧は社用PC（Windows）のみ。Macはコード開発専用
- `app.py`（ルート）と`utils/chart_helpers.py`は旧Streamlit UI用。現在未使用だが残存

## 環境変数 (.env)

```
GEMINI_API_KEY=<key>
GEMINI_MODEL=gemini-2.5-flash
GEMINI_DELAY_SECONDS=1
BATCH_SIZE=200
MAX_EMAILS_PER_FETCH=500
GMAIL_LABELS=SES案件
GMAIL_KEYWORDS=案件,募集,エンジニア,SE,PG
GMAIL_CREDENTIALS_PATH=credentials/credentials.json
GMAIL_TOKEN_PATH=credentials/token.json
GMAIL_TOKEN_JSON=      # 本番用: token.jsonの内容を文字列で設定
GMAIL_CREDENTIALS_JSON= # 本番用: credentials.jsonの内容を文字列で設定
CORS_ORIGINS=http://localhost:3000
DATABASE_URL=  # 空ならSQLite、設定するとPostgreSQL
CRON_SECRET=   # GitHub Actions認証用
```

## タスク状況

### 完了済み（主要）
- Next.js + FastAPI フルスタック（4ページ: ダッシュボード、案件検索、メール取得、設定）
- Vercel + Render + Supabase デプロイ
- Gmail OAuth本番接続、Gemini AI解析
- フリーワード検索 AND/OR対応、参画月フィールド、CSV出力
- メール自動取得の定期実行（GitHub Actions、1日5回、keep-aliveループ付き）
- パイプライン安定性改善（Gemini 60秒タイムアウト、重複実行防止ロック、スタックしたログの自動クリーンアップ）
- 取得ログの日時をJST（日本時間）で表示
- エリア正規化（東京23区/埼玉/千葉等の大分類）、スキル名正規化（60+マッピング）
- 1メール→複数案件抽出対応、重複案件検出
- 会社名をsender企業名に限定（案件先名の混入防止）
- 必須要件・求める人物像フィールド（requirements）追加
- 検索UIのサイドバー/メインコンテンツ独立スクロール

### 次にやること（優先度順）
1. メール本文の自動削除機能（処理済み30日後に本文クリア）
2. 月次サマリーテーブルの自動集計
3. エンジニア情報管理機能（テーブル設計 + 登録UI）
4. 案件×エンジニア マッチング機能

### 関連ドキュメント
- `計画書_2026年2月.md` - 計画書（Markdown版）
- `create_word_plan.py` - Word版計画書生成スクリプト
