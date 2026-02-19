# CLAUDE.md - Gmail Analyzer プロジェクト

## プロジェクト概要

SES（システムエンジニアリングサービス）案件メールを自動解析し、案件情報を可視化するWebダッシュボードシステム。
`cloudlink.company@gmail.com` に届くSES案件メールをGmail API経由で取得し、Gemini AIで解析して、スキル別・単価別・エリア別などで一覧化する。

## 技術スタック

- **フロントエンド/UI**: Streamlit
- **バックエンド**: Python
- **データベース**: SQLite (`data/gmail_analyzer.db`)
- **メール取得**: Gmail API
- **AI解析**: Google Gemini API (`gemini-2.0-flash`)
- **デプロイ**: Streamlit Community Cloud

## リポジトリ

- **GitHub**: `https://github.com/pauhei-saunner/gmail_analyzer` (Private)
- **Streamlit Cloud**: デプロイ済み（デモ用、Gmail接続なし）

## ディレクトリ構成

```
gmail_analyzer/
├── .claude/              # Claude設定
├── .streamlit/           # Streamlit設定
├── core/                 # コアロジック
├── credentials/          # 認証ファイル（.gitignore対象）
│   ├── credentials.json  # Google Cloud OAuthクライアント
│   └── token.json        # Gmail認証トークン（自動生成）
├── data/                 # データベース（.gitignore対象）
├── models/               # データモデル
├── pages/                # Streamlitページ
├── utils/                # ユーティリティ
├── .env                  # 環境変数（.gitignore対象）
├── .env.example          # 環境変数テンプレート
├── .gitignore
├── app.py                # メインエントリポイント
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

- **プロジェクトパス**: `C:\Users\shimi\Documents\gmail_analyzer`
- **用途**: 実データでのメール取得・解析
- **起動コマンド**:
  ```cmd
  cd %USERPROFILE%\Documents\gmail_analyzer
  venv\Scripts\activate
  streamlit run app.py
  ```
- **ブラウザ**: `http://localhost:8501`

### .env ファイル（Mac側の設定内容）

```
# Gemini API
GEMINI_API_KEY=（設定済み）
GEMINI_MODEL=gemini-2.0-flash

# Gmail
GMAIL_CREDENTIALS_PATH=credentials/credentials.json
GMAIL_TOKEN_PATH=credentials/token.json

# Filters
GMAIL_LABELS=SES案件
GMAIL_KEYWORDS=案件,募集,エンジニア,SE,PG

# Processing
BATCH_SIZE=50
MAX_EMAILS_PER_FETCH=500
GEMINI_DELAY_SECONDS=1.0

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
- [x] Gmailフィルタで「SES案件」ラベル自動付与設定

### 未完了（次のステップ）
- [ ] **Windows側の.envにGemini APIキーを設定**（最優先）
  - `notepad C:\Users\shimi\Documents\gmail_analyzer\.env` でメモ帳を開く
  - Mac側の.envと同じ内容に書き換える（特にGEMINI_API_KEY）
- [ ] メール取得→AI解析の動作確認
- [ ] 実データでのダッシュボード表示確認
- [ ] 契約形態の分類改善（派遣 vs 準委任）
- [ ] 給与フォーマット標準化（時給 vs 月給）
- [ ] AI信頼度スコアの実装
- [ ] 本格運用時のStreamlit Cloud Secrets設定（クラウドでもGmail接続可能にする）
- [ ] GitHubユーザー名変更（本格運用時）

## 開発ワークフロー

1. **Mac**でコード修正 → `git push`
2. **Windows**で `git pull` → 最新コード取得
3. **Windows**で実データテスト
4. 変更をStreamlit Cloudに自動反映（GitHubプッシュ時）

## 注意事項

- **情報管理**: 実データの取得・閲覧は社用PC（Windows）のみで行う。Macはコード開発専用。
- **認証ファイル**: `credentials/`フォルダは.gitignoreで除外。GitHubにアップしない。
- **トークン再認証**: 別のGmailアカウントに切り替える場合は`token.json`を削除して再接続。
  - Mac: `rm ~/Desktop/gmail_analyzer/credentials/token.json`
  - Windows: `del C:\Users\shimi\Documents\gmail_analyzer\credentials\token.json`
