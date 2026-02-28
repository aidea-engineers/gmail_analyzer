# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

SES案件メールを自動解析し、案件情報を可視化 + エンジニアとのマッチングを行うWebシステム。
`cloudlink.company@gmail.com` に届くメールをGmail API経由で取得 → Gemini AIで解析 → スキル別・単価別・エリア別に一覧化。
エンジニア登録・管理 + 案件×エンジニアのマッチング提案機能あり。

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

### バックエンド構成 (`backend/`)

**エントリポイント** (`main.py`):
- FastAPI app。起動時に `init_db()` + `cleanup_stale_fetch_logs()` + `clear_old_email_bodies(days=7)` を実行
- CORS: `Config.CORS_ORIGINS`（カンマ区切り環境変数）から動的設定

**ルーター** (6つのAPIグループ):
- `routers/dashboard.py` — `/api/dashboard/{kpis,charts}` 集計・チャート
- `routers/search.py` — `/api/search/{filters,listings,export}` 検索・CSV出力
- `routers/fetch.py` — `/api/fetch/{status,full-pipeline,ai-only,cron,progress,reanalyze-old}` パイプライン制御。重複実行防止ロック付き（409で拒否）
- `routers/settings.py` — `/api/settings` 設定
- `routers/engineers.py` — `/api/engineers/*` エンジニアCRUD、スキル管理、担当案件、CSV入出力、フィルター
- `routers/matching.py` — `/api/matching/*` マッチング提案（候補/提案済み/面談中/成約/見送り）、スコア計算

**コアモジュール**:
- `core/database.py` — デュアルDB対応。`DATABASE_URL`環境変数ありでPostgreSQL、なしでSQLite。`_DBWrapper`がプレースホルダ(`?`→`%s`)を自動変換。マイグレーションはバージョン管理方式（`MIGRATIONS`リスト + `schema_migrations`テーブル）で管理。カラム追加時は`MIGRATIONS`末尾に追加し、PG/SQLite両スキーマ定義も更新すること
- `core/gmail_client.py` — Gmail OAuth認証（環境変数トークン優先、ファイルフォールバック）、インクリメンタルフェッチ（`MAX(received_at)`以降のみ取得）
- `core/gemini_extractor.py` — Gemini APIで案件情報抽出。JSON mode + Pydantic `EmailExtractionResult` スキーマ。429エラー時は指数バックオフリトライ(3回)。60秒タイムアウト。後処理でスキル正規化・エリア正規化・会社名を品質ベース優先順位で設定
- `core/batch_processor.py` — `run_full_pipeline()`(Gmail取得+AI解析)と`run_extraction_only()`(AI解析のみ)。progress_callbackでSSE進捗通知。1メール→複数案件対応

**ユーティリティ** (`utils/`):
- `text_helpers.py` — メール本文クリーニング、スキル名正規化（60+マッピング）、エリア正規化、sender解析、会社名品質判定、署名抽出、`PROCESS_OPTIONS`定数
- `date_helpers.py` — 期間文字列→日付範囲変換、JST表示フォーマット

**スキーマ** (`models/schemas.py`):
- `JobListingExtraction` / `EmailExtractionResult` — Gemini抽出結果
- `EngineerCreate` / `EngineerUpdate` — エンジニアCRUD
- `ProposalCreate` / `ProposalUpdate` — マッチング提案
- `AssignmentCreate` — 担当案件割り当て

### フロントエンド構成 (`frontend/`)

- App Router、全ページ `"use client"` (CSR)
- `src/lib/api.ts` — `fetchAPI<T>()`ラッパー（`NEXT_PUBLIC_API_URL`でバックエンドURL指定）
- `src/types/index.ts` — 全APIレスポンスのTypeScript型定義（バックエンド `models/schemas.py` と同期必須）
- `src/components/charts/` — Recharts 4種（スキル棒、単価ヒストグラム、エリア円、トレンド折れ線）
- `src/components/CollapsibleSection.tsx` — 折りたたみパネル
- SSE進捗追跡: EventSourceで`/api/fetch/progress/{jobId}`をリアルタイム受信
- スタイル: Tailwindクラス + CSS変数（`var(--card-bg)`, `var(--border)`, `var(--primary)`等）をinline styleで使用

**ページ** (6ページ):

| ルート | 機能 |
|--------|------|
| `/` | ダッシュボード — KPIカード + 4チャート + 折りたたみセクション |
| `/search` | 案件検索 — サイドバーフィルター(AND/OR) + 展開テーブル + CSV出力 |
| `/fetch` | メール取得 — パイプライン制御、SSE進捗、409重複表示 |
| `/settings` | 設定 — Gmail/Gemini/処理パラメータ |
| `/engineers` | エンジニア管理 — CRUD、スキル・単価・エリア・工程管理、CSV入出力 |
| `/matching` | マッチング — 案件↔エンジニア提案、スコア表示、ステータス管理 |

### DBスキーマ（主要テーブル）

- `emails` — gmail_message_id(UNIQUE), subject, sender, body_text, received_at, is_processed
- `job_listings` — email_id(FK), company_name, work_area, unit_price, unit_price_min/max, required_skills(JSON), project_details, requirements, job_type, confidence, start_month
- `skills` — listing_id(FK), skill_name（正規化済み）
- `fetch_log` — started_at, status, emails_fetched, emails_processed, errors(JSON)
- `engineers` — name, experience_years, current_price, desired_price_min/max, status, preferred_areas, available_from, processes, notes
- `engineer_skills` — engineer_id(FK), skill_name
- `engineer_assignments` — engineer_id, listing_id, company_name, project_name, start/end_date, unit_price, status
- `matching_proposals` — engineer_id, listing_id, score, status, UNIQUE(engineer_id, listing_id)

新カラム追加手順: `database.py` の `MIGRATIONS` リスト末尾に `(N, "table.column", "ALTER TABLE ...")` を追加 → PG/SQLite両スキーマ定義にもカラムを追加 → insert/update関数のfield_mapに追加。

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
- Gemini解析はBATCH_SIZE(200)件ずつ。手動UIは1バッチのみ、cron実行時は自動ループで全件処理
- 処理済みメール本文は7日後に自動削除（Supabase容量対策）
- 旧Streamlit UI用の `app.py` と `utils/chart_helpers.py` は未使用だが残存
- 会社名抽出は品質ベース優先順位: sender(法人格) > 署名(法人格) > Gemini > sender(普通) > ドメイン

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
