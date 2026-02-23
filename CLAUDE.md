# CLAUDE.md - Gmail Analyzer プロジェクト

## プロジェクト概要

SES（システムエンジニアリングサービス）案件メールを自動解析し、案件情報を可視化するWebダッシュボードシステム。
`cloudlink.company@gmail.com` に届くSES案件メールをGmail API経由で取得し、Gemini AIで解析して、スキル別・単価別・エリア別などで一覧化する。

## 技術スタック

- **フロントエンド/UI**: Next.js 16 + TypeScript + Tailwind CSS（Phase 2-3,5-6 完了）/ Streamlit（旧UI・デモ用）
- **バックエンド**: FastAPI (Python)（Phase 1,4 完了）
- **データベース**: PostgreSQL (Supabase) / SQLite（ローカル開発用フォールバック）
- **メール取得**: Gmail API
- **AI解析**: Google Gemini API (`gemini-2.5-flash`)
- **チャート**: Recharts（スキル棒グラフ、単価ヒストグラム、エリア円グラフ、トレンド折れ線）
- **デプロイ**: Vercel（フロントエンド）+ Render（バックエンド）+ Supabase（DB）

## リポジトリ・本番URL

- **GitHub**: `https://github.com/aidea-engineers/gmail_analyzer` (Public)
- **本番フロントエンド**: `https://gmail-analyzer-nu.vercel.app`
- **本番バックエンドAPI**: `https://gmail-analyzer-api.onrender.com`
- **API Docs (Swagger)**: `https://gmail-analyzer-api.onrender.com/docs`
- **Streamlit Cloud**: デプロイ済み（デモ用、Gmail接続なし）

## ディレクトリ構成

```
gmail_analyzer/
├── .claude/              # Claude設定
├── .streamlit/           # Streamlit設定
├── core/                 # コアロジック（Streamlit用）
├── credentials/          # 認証ファイル（.gitignore対象）
│   ├── credentials.json  # Google Cloud OAuthクライアント
│   └── token.json        # Gmail認証トークン（自動生成）
├── data/                 # データベース（.gitignore対象）
├── models/               # データモデル（Streamlit用）
├── pages/                # Streamlitページ
├── utils/                # ユーティリティ（Streamlit用）
├── frontend/             # Next.js フロントエンド（Phase 2-3,5-6 完了）
│   ├── src/
│   │   ├── app/          # App Router ページ（/, /search, /fetch, /settings）
│   │   ├── components/   # UIコンポーネント（Sidebar, KPICard, ProgressBar, charts/）
│   │   ├── lib/          # APIクライアント（api.ts）
│   │   └── types/        # TypeScript型定義（index.ts）
│   ├── package.json
│   └── tsconfig.json
├── backend/              # FastAPI バックエンド（Phase 1,4 完了）
│   ├── core/             # コアロジック
│   ├── models/           # データモデル
│   ├── utils/            # ユーティリティ
│   ├── routers/          # APIルーター（dashboard, search, fetch, settings）
│   ├── main.py           # FastAPIエントリポイント（CORS設定済み）
│   ├── config.py         # 設定
│   ├── Dockerfile        # デプロイ用Docker設定
│   └── requirements.txt  # 依存パッケージ
├── .env                  # 環境変数（.gitignore対象）
├── .env.example          # 環境変数テンプレート
├── .gitignore
├── app.py                # Streamlitメインエントリポイント（旧UI）
├── config.py             # 設定
└── requirements.txt      # 依存パッケージ
```

## アプリの機能（4ページ構成）

1. **ダッシュボード** - スキル別案件数、単価分布、エリア別案件数、トレンドなどのグラフ
2. **案件検索** - フィルタリング・検索可能な案件一覧
3. **メール取得** - Gmail取得・AI解析実行、モックデータ投入
4. **設定** - Gmail接続、ラベル設定、Gemini APIキー設定

## 環境設定

### Mac（私用PC - 開発用）

- **プロジェクトパス**: `~/Desktop/gmail_analyzer`
- **用途**: コード開発・修正
- **起動コマンド**:
  ```bash
  cd ~/Desktop/gmail_analyzer
  source venv/bin/activate
  streamlit run app.py
  ```

### Windows（社用PC - 運用用）

- **プロジェクトパス**: `C:\Users\shimi\OneDrive\Desktop\VScode\AIdea Engineers事業全管理システム\gmail_analyzer`
- **WSLパス**: `/mnt/c/Users/shimi/OneDrive/Desktop/VScode/AIdea Engineers事業全管理システム/gmail_analyzer`
- **用途**: 実データでのメール取得・解析、Claude Codeでの開発

#### Next.js + FastAPI（新UI）
```bash
# バックエンド起動（Windows CMD）
cd "C:\Users\shimi\OneDrive\Desktop\VScode\AIdea Engineers事業全管理システム\gmail_analyzer\backend"
venv\Scripts\activate
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# フロントエンド起動（WSL）
cd "/mnt/c/Users/shimi/OneDrive/Desktop/VScode/AIdea Engineers事業全管理システム/gmail_analyzer/frontend"
npm run dev
```
- **フロントエンド**: `http://localhost:3000`
- **バックエンドAPI**: `http://localhost:8000/docs`（Swagger UI）

#### Streamlit（旧UI）
```cmd
cd "C:\Users\shimi\OneDrive\Desktop\VScode\AIdea Engineers事業全管理システム\gmail_analyzer"
venv\Scripts\activate
streamlit run app.py
```
- **ブラウザ**: `http://localhost:8501`

#### Git操作（WSLから）
WSLではGitHub認証が未設定のため、Windows側のGitを使う：
```bash
/mnt/c/Program\ Files/Git/bin/git.exe -C "C:/Users/shimi/OneDrive/Desktop/VScode/AIdea Engineers事業全管理システム/gmail_analyzer" push origin main
```

### .env ファイル（Mac側の設定内容）

```
# Gemini API
GEMINI_API_KEY=（設定済み）
GEMINI_MODEL=gemini-2.5-flash

# Gmail
GMAIL_CREDENTIALS_PATH=credentials/credentials.json
GMAIL_TOKEN_PATH=credentials/token.json

# Filters
GMAIL_LABELS=SES案件
GMAIL_KEYWORDS=案件,募集,エンジニア,SE,PG

# Processing
BATCH_SIZE=15
MAX_EMAILS_PER_FETCH=500
GEMINI_DELAY_SECONDS=4.0

# Database
DB_PATH=data/gmail_analyzer.db
```

### .gitignore で除外されているファイル

```
.env
credentials/
data/*.db
data/*.log
__pycache__/
*.pyc
.streamlit/secrets.toml
.venv/
venv/
```

## Google Cloud Console 設定

- **プロジェクト名**: Gmail Analyzer
- **プロジェクトID**: gmail-analyzer-487017
- **有効API**: Gmail API
- **OAuth同意画面**: テストモード（テストユーザー追加が必要）
- **管理アカウント**: ganalyzer71@gmail.com

### テストユーザー

Gmail APIのアプリ審査が未完了のため、OAuth同意画面でテストユーザーを追加する必要がある。
- Google Cloud Console → APIとサービス → OAuth同意画面 → 対象 → テストユーザー追加
- `cloudlink.company@gmail.com` をテストユーザーとして追加済み

## Gmail設定

- **対象アカウント**: `cloudlink.company@gmail.com`
- **対象ラベル**: `SES案件`
- **フィルタ設定済み**: 受信メール全てに「SES案件」ラベルを自動付与するGmailフィルタを設定

## 現在の状況と未完了タスク

### 完了済み
- [x] Mac側でのシステム開発・動作確認
- [x] GitHubリポジトリ作成・コードプッシュ
- [x] Windows社用PCへの移行（git clone、パッケージインストール）
- [x] credentials.jsonの配置（credentials/フォルダ内）
- [x] Streamlit Community Cloudへのデプロイ（デモ用）
- [x] Streamlit Cloudのアプリをパブリックに設定
- [x] Google Cloud Consoleでcloudlink.company@gmail.comをテストユーザーに追加
- [x] Windows側でcloudlink.company@gmail.comとのGmail接続成功
- [x] Gmailフィルタで「SES案件」ラベル自動付与設定（deliveredto: 条件で包括的にカバー）
- [x] Figma連携の調査→不採用（$16/月のコスト）
- [x] Next.js + FastAPI 移行計画の策定
- [x] Windows側のGitHub同期
- [x] Windows側の.envにGemini APIキーを設定
- [x] メール取得テスト（500件取得成功、DB保存OK）
- [x] Gemini API失敗時のエラーハンドリング改善（失敗メールを再試行可能に）
- [x] Phase 0: モノレポ構造セットアップ（frontend/ + backend/）
- [x] Phase 1: バックエンドAPI 8本作成（dashboard, search, fetch, settings）
- [x] Phase 2: フロントエンド ダッシュボード（KPIカード、Rechartsチャート4種）
- [x] Phase 3: フロントエンド 案件検索（フィルタ、テーブル、CSV出力）
- [x] Phase 4: バックエンド書き込みAPI（パイプライン実行、モック、SSE進捗）
- [x] Phase 5: フロントエンド メール取得・設定ページ
- [x] Phase 6: レスポンシブ対応・Dockerfile
- [x] モックデータ（150件）での全4ページ動作確認済み
- [x] GitHub Organization作成（aidea-engineers）& リポジトリ移管
- [x] PostgreSQL対応（database.pyデュアルDB、psycopg2-binary追加）
- [x] CORS動的設定、Gmail OAuth環境変数対応、Dockerfile改善
- [x] Supabaseプロジェクト作成（PostgreSQL）
- [x] Renderバックエンドデプロイ（環境変数6個設定済み）
- [x] Vercelフロントエンドデプロイ（NEXT_PUBLIC_API_URL設定済み）
- [x] 本番環境でモックデータ150件投入・ダッシュボード表示確認済み

### 次にやること（優先度順）

#### 最優先: 実データ接続
1. [ ] GMAIL_TOKEN_JSON / GMAIL_CREDENTIALS_JSON をRender環境変数に設定（本番Gmail接続）
2. [ ] 本番環境でメール取得テスト
3. [ ] Geminiクォータ回復後に「未処理メールをAI解析」を実行（513件未処理）
4. [ ] 実データでの案件抽出結果を確認・調整

#### 中期: 機能改善
5. [ ] 契約形態の分類改善（派遣 vs 準委任）
6. [ ] 給与フォーマット標準化（時給 vs 月給）
7. [ ] AI信頼度スコアの実装
8. [ ] カスタムドメイン設定（Vercel）

#### 長期: 機能拡張
9. [ ] エンジニア情報管理機能の設計・開発
10. [ ] 案件×エンジニアのAIマッチング
11. [ ] Slack/Teams連携による通知機能
12. [ ] 複数ユーザー対応（認証・権限管理）

#### その他
- [ ] 各サービスの法人契約への移行
- [ ] CI/CDパイプラインの構築
- [ ] Vercel Pro移行時にリポジトリをPrivateに戻す

## 本番環境（デプロイ済み 2026-02-21）

| サービス | URL | プラン | 用途 |
|---------|-----|--------|------|
| Vercel | `https://gmail-analyzer-nu.vercel.app` | Hobby (¥0) | フロントエンド |
| Render | `https://gmail-analyzer-api.onrender.com` | Free (¥0) | バックエンドAPI |
| Supabase | (内部接続) | Free (¥0) | PostgreSQL DB |
| GitHub | `aidea-engineers/gmail_analyzer` | Free Org (¥0) | ソースコード |

**注意**: Render無料プランは15分無操作でスリープ。初回アクセス時30秒程度かかる。

## 開発ワークフロー

1. **Mac/Windows**でコード修正 → `git push origin main`
2. **Vercel**: GitHubプッシュで自動デプロイ（フロントエンド）
3. **Render**: GitHubプッシュで自動デプロイ（バックエンド）
4. ローカル開発時は従来通り `localhost:3000` + `localhost:8000`

## 注意事項

- **情報管理**: 実データの取得・閲覧は社用PC（Windows）のみで行う。Macはコード開発専用。
- **認証ファイル**: `credentials/`フォルダは.gitignoreで除外。GitHubにアップしない。
- **トークン再認証**: 別のGmailアカウントに切り替える場合は`token.json`を削除して再接続。
  - Mac: `rm ~/Desktop/gmail_analyzer/credentials/token.json`
  - Windows: `del "C:\Users\shimi\OneDrive\Desktop\VScode\AIdea Engineers事業全管理システム\gmail_analyzer\credentials\token.json"`

## メモの管理方針

### GitHubで共有されるメモ（Mac・Windows両方で見える）
- `CLAUDE.md` - プロジェクト全体の設定・状況
- `フィグマ連携/` - Figma調査メモ、Next.js移行計画
- `Gmailタグ付け/` - Gmailフィルタ設定の作業記録
- → git push/pull で Mac・Windows間を同期

### Claude Code専用メモ（各PCのローカルのみ）
- Claude Codeが前回の作業を思い出すための記憶ファイル
- 各PCごとに別々に保存される（GitHubには上がらない）
