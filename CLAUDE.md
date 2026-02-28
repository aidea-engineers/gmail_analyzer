# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

**AIdea Platform** — SES案件メールを自動解析し、案件情報を可視化 + エンジニアとのマッチングを行うWebシステム。
`cloudlink.company@gmail.com` に届くメールをGmail API経由で取得 → Gemini AIで解析 → スキル別・単価別・エリア別に一覧化。
エンジニア登録・管理 + 案件×エンジニアのマッチング提案 + Supabase Auth認証・権限管理。

## 技術スタック

- **フロントエンド**: Next.js 16 + React 19 + TypeScript + Tailwind CSS 4 + Recharts 3 + @supabase/supabase-js
- **バックエンド**: FastAPI (Python) + Pydantic 2 + PyJWT[crypto]
- **データベース**: PostgreSQL (Supabase本番) / SQLite (ローカル開発フォールバック)
- **認証**: Supabase Auth (メール+パスワード) → ES256 JWT → バックエンドで検証
- **外部API**: Gmail API, Google Gemini API (`gemini-2.5-flash`)
- **デプロイ**: Vercel (フロントエンド) + Render (バックエンド) + Supabase (DB + Auth)
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
- 構文チェック: `python3 -c "import py_compile; py_compile.compile('main.py', doraise=True)"`

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
                                                                    ↑
                                            エンジニア登録/マッチング提案
```

### 認証フロー

```
ログイン画面 → Supabase Auth (email+password) → JWT (ES256) 取得
    ↓
全APIリクエストに Authorization: Bearer <JWT> 付与
    ↓
バックエンド get_current_user() → JWKS公開鍵でES256検証 → user_profilesからロール取得
    ↓
require_admin() / require_auth() で権限チェック
```

- **ロール**: `admin`（全データ閲覧・編集）/ `engineer`（自分の情報のみ）
- `AUTH_ENABLED=false` で認証バイパス（ローカル開発用、ダミー管理者を返す）
- Supabase未設定時はフロントエンドもダミー管理者モードで動作

### バックエンド構成 (`backend/`)

**エントリポイント** (`main.py`):
- FastAPI app（title: "AIdea Platform API", version: 1.0.0）。起動時に `init_db()` + `cleanup_stale_fetch_logs()` + `clear_old_email_bodies(days=7)` を実行
- CORS: `Config.CORS_ORIGINS`（カンマ区切り環境変数）から動的設定

**ルーター** (8つのAPIグループ):
- `routers/auth.py` — `/api/auth/{me,users}` 認証ユーザー情報・ユーザー管理（管理者用CRUD）
- `routers/dashboard.py` — `/api/dashboard/{kpis,charts,monthly-summary}` 集計・チャート・月次サマリー（admin）
- `routers/search.py` — `/api/search/{filters,listings,export}` 検索・CSV出力（admin）
- `routers/fetch.py` — `/api/fetch/{status,full-pipeline,ai-only,cron,progress,reanalyze-old}` パイプライン制御（admin、cronは既存CRON_SECRET維持）
- `routers/settings.py` — `/api/settings` 設定（admin）
- `routers/engineers.py` — `/api/engineers/*` エンジニアCRUD、スキル管理、担当案件、CSV入出力（admin / 自分のみauth）
- `routers/matching.py` — `/api/matching/*` マッチング提案・スコア計算（admin）
- `routers/import_data.py` — `/api/import/{employees,assignments,companies}` Fairgrit CSVインポート（admin）

**コアモジュール**:
- `core/database.py` — デュアルDB対応。`DATABASE_URL`環境変数ありでPostgreSQL、なしでSQLite。`_DBWrapper`がプレースホルダ(`?`→`%s`)を自動変換。マイグレーションはバージョン管理方式（`MIGRATIONS`リスト v1-35 + `schema_migrations`テーブル）で管理。カラム追加時は`MIGRATIONS`末尾に追加し、PG/SQLite両スキーマ定義も更新すること
- `core/auth.py` — JWT認証モジュール。Supabase Auth JWTをES256(JWKS)で検証し、user_profilesからロールを取得。`AUTH_ENABLED`環境変数でON/OFF切替。`CurrentUser`データクラス、`require_auth()`/`require_admin()`依存関数
- `core/gmail_client.py` — Gmail OAuth認証（環境変数トークン優先、ファイルフォールバック）、インクリメンタルフェッチ（`MAX(received_at)`以降のみ取得）
- `core/gemini_extractor.py` — Gemini APIで案件情報抽出。JSON mode + Pydantic `EmailExtractionResult` スキーマ。429エラー時は指数バックオフリトライ(3回)。60秒タイムアウト。後処理でスキル正規化・エリア正規化・会社名を品質ベース優先順位で設定
- `core/batch_processor.py` — `run_full_pipeline()`(Gmail取得+AI解析)と`run_extraction_only()`(AI解析のみ)。progress_callbackでSSE進捗通知。1メール→複数案件対応

**ユーティリティ** (`utils/`):
- `text_helpers.py` — メール本文クリーニング、スキル名正規化（60+マッピング）、エリア正規化、sender解析、会社名品質判定、署名抽出、`PROCESS_OPTIONS`定数、`COMPANY_NAME_OVERRIDES`（略称→正式名称の手動マッピング）
- `date_helpers.py` — 期間文字列→日付範囲変換、JST表示フォーマット

**スキーマ** (`models/schemas.py`):
- `JobListingExtraction` / `EmailExtractionResult` — Gemini抽出結果
- `EngineerCreate` / `EngineerUpdate` — エンジニアCRUD（20+フィールド）
- `ProposalCreate` / `ProposalUpdate` — マッチング提案
- `AssignmentCreate` — 担当案件割り当て

### フロントエンド構成 (`frontend/`)

- App Router、全ページ `"use client"` (CSR)
- `src/lib/api.ts` — `fetchAPI<T>()`ラッパー。Supabase AuthトークンをBearer headerとして自動付与
- `src/lib/supabase.ts` — Supabaseクライアント初期化（未設定時はnull→認証無効モード）
- `src/types/index.ts` — 全APIレスポンスのTypeScript型定義（バックエンド `models/schemas.py` と同期必須）
- `src/components/AuthProvider.tsx` — 認証コンテキスト（session, role, isAdmin, signOut）+ `useAuth()`フック
- `src/components/AppShell.tsx` — 認証ガード（未認証→/loginリダイレクト）+ Sidebar表示制御
- `src/components/Sidebar.tsx` — ロール別ナビ表示（admin: 全メニュー / engineer: マイプロフィールのみ）+ ログアウトボタン
- `src/components/charts/` — Recharts 4種（スキル棒、単価ヒストグラム、エリア円、トレンド折れ線）
- `src/components/CollapsibleSection.tsx` — 折りたたみパネル
- SSE進捗追跡: EventSourceで`/api/fetch/progress/{jobId}`をリアルタイム受信
- スタイル: Tailwindクラス + CSS変数（`var(--card-bg)`, `var(--border)`, `var(--primary)`等）をinline styleで使用

**ページ** (8ページ):

| ルート | 機能 | 認証 |
|--------|------|------|
| `/login` | ログイン — メール+パスワード (Supabase Auth) | 公開 |
| `/` | ダッシュボード — KPIカード + 4チャート + 月別サマリーテーブル + 折りたたみセクション | admin |
| `/search` | 案件検索 — サイドバーフィルター(AND/OR) + 展開テーブル + CSV出力 | admin |
| `/fetch` | メール取得 — パイプライン制御、SSE進捗、409重複表示 | admin |
| `/settings` | 設定 — Gmail/Gemini/処理パラメータ | admin |
| `/engineers` | エンジニア管理 — CRUD、スキル・単価・エリア・工程管理、CSV入出力 | admin |
| `/matching` | マッチング — 案件↔エンジニア提案、スコア表示、ステータス管理 | admin |
| `/my-profile` | マイプロフィール — エンジニア自身の情報・スキル・担当案件表示 | engineer |

### DBスキーマ（主要テーブル）

- `emails` — gmail_message_id(UNIQUE), subject, sender, body_text, received_at, is_processed
- `job_listings` — email_id(FK), company_name, work_area, unit_price, unit_price_min/max, required_skills(JSON), project_details, requirements, job_type, confidence, start_month
- `skills` — listing_id(FK), skill_name（正規化済み）
- `fetch_log` — started_at, status, emails_fetched, emails_processed, errors(JSON)
- `engineers` — name, email, phone, name_kana, gender, birth_date, education, hire_date, experience_years, current_price, desired_price_min/max, status, preferred_areas, available_from, processes, notes, industry_experience, skill_proficiency(JSON), certifications, job_type_experience, position_experience, remote_preference, career fields, office_branch, department, fairgrit_user_id, address, nearest_station
- `engineer_skills` — engineer_id(FK), skill_name
- `engineer_assignments` — engineer_id, listing_id, company_name, project_name, start/end_date, unit_price, status, contract_type, sales_person, client_company_name, monthly_rate, work_hours_lower/upper
- `matching_proposals` — engineer_id, listing_id, score, status, UNIQUE(engineer_id, listing_id)
- `user_profiles` — id(PK, Supabase Auth UUID), email, role("admin"/"engineer"), engineer_id(FK), display_name, created_at, updated_at
- `companies` — name, name_kana, phone, url, prefecture, tags, contact_name, contact_email等

新カラム追加手順: `database.py` の `MIGRATIONS` リスト末尾に `(N, "table.column", "ALTER TABLE ...")` を追加 → PG/SQLite両スキーマ定義にもカラムを追加 → insert/update関数のfield_mapに追加。現在v35まで。

### 自動実行 (GitHub Actions)

- `.github/workflows/scheduled-fetch.yml` — 1日5回（JST 9,12,15,18,21時）
- Renderサーバー起床(60秒待機) → `POST /api/fetch/cron`(Bearer認証) → バックグラウンドで処理
- Keep-aliveループ: 30秒間隔でstatus確認、未処理0またはスタック検出で終了（最大20分）
- cron実行時は未処理が0になるまでBATCH_SIZE(200件)ずつループ解析（手動UIは1バッチのみ）

## 本番環境

| サービス | URL | プラン |
|---------|-----|--------|
| Vercel | `https://gmail-analyzer-nu.vercel.app` | Hobby (¥0) |
| Render | `https://gmail-analyzer-api.onrender.com` | Starter ($7/月) |
| Supabase | (内部接続) | Free (¥0) |
| GitHub | `aidea-engineers/gmail_analyzer` | Free Org (¥0) |

- GitHubプッシュで Vercel/Render 自動デプロイ
- リポジトリはPublic（Vercel Hobby制約）

## 開発時の注意事項

- `credentials/`フォルダは.gitignore対象。GitHubにアップしない
- ローカル開発はSQLite（DATABASE_URL未設定時）、本番はSupabase PostgreSQL
- ローカル開発は`AUTH_ENABLED=false`（デフォルト）で認証バイパス、本番は`AUTH_ENABLED=true`
- Gemini解析はBATCH_SIZE(200)件ずつ。手動UIは1バッチのみ、cron実行時は自動ループで全件処理
- 処理済みメール本文は7日後に自動削除（Supabase容量対策）
- 旧Streamlit UI用の `app.py` と `utils/chart_helpers.py` は未使用だが残存
- 会社名抽出は品質ベース優先順位: sender(法人格) > 署名(法人格) > Gemini > sender(普通) > ドメイン → 最後に`COMPANY_NAME_OVERRIDES`で手動マッピング適用

## 環境変数 (.env)

```
# Gemini AI
GEMINI_API_KEY=<key>
GEMINI_MODEL=gemini-2.5-flash
GEMINI_DELAY_SECONDS=1
BATCH_SIZE=200
MAX_EMAILS_PER_FETCH=500

# Gmail
GMAIL_LABELS=SES案件
GMAIL_KEYWORDS=案件,募集,エンジニア,SE,PG
GMAIL_CREDENTIALS_PATH=credentials/credentials.json
GMAIL_TOKEN_PATH=credentials/token.json
GMAIL_TOKEN_JSON=      # 本番用: token.jsonの内容を文字列で設定
GMAIL_CREDENTIALS_JSON= # 本番用: credentials.jsonの内容を文字列で設定

# Database & Auth
DATABASE_URL=            # 空ならSQLite、設定するとPostgreSQL
AUTH_ENABLED=false       # 本番: true
SUPABASE_URL=            # https://xxx.supabase.co（ES256 JWKS検証用）
SUPABASE_JWT_SECRET=     # フォールバック用HS256シークレット
CORS_ORIGINS=http://localhost:3000
CRON_SECRET=             # GitHub Actions認証用

# フロントエンド（Vercel環境変数）
NEXT_PUBLIC_API_URL=     # バックエンドURL（デフォルト: http://localhost:8000）
NEXT_PUBLIC_SUPABASE_URL=      # https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY= # Supabase anon key
```
