# Gmail Analyzer: Streamlit → Next.js + FastAPI 移行計画

## Context
gmail_analyzer（SES案件メール解析ダッシュボード）のフロントエンドをStreamlitからNext.jsに移行する。
- 目的: UIの自由度向上、12時間休止問題の解消、ソースコード非公開化
- コスト: 追加費用0円（すべて無料ツール・サービスで構成）
- Figma連携: コスト（$16/月）のため不採用

## 構成
- **フロントエンド**: Next.js (App Router) + TypeScript + Tailwind CSS
- **バックエンド**: FastAPI (Python) ← 既存ロジック流用
- **DB**: SQLite（変更なし）
- **ホスティング**: Cloudflare Pages (frontend) + Render無料枠 (backend)
- **チャート**: Recharts（Plotlyの代替、軽量）
- **状態管理**: TanStack Query + URLパラメータ
- **リアルタイム進捗**: SSE (Server-Sent Events)

## 新・ディレクトリ構成（モノレポ）
```
gmail_analyzer/
├── frontend/              # Next.js アプリ
│   ├── src/
│   │   ├── app/           # App Router ページ
│   │   ├── components/    # UIコンポーネント
│   │   ├── lib/           # API呼び出し・ユーティリティ
│   │   └── types/         # TypeScript型定義
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── backend/               # FastAPI アプリ
│   ├── core/              # 既存コアロジック（流用）
│   ├── models/            # Pydanticモデル（API用に拡張）
│   ├── utils/             # ユーティリティ（流用）
│   ├── routers/           # APIルーター
│   ├── credentials/       # 認証ファイル
│   ├── data/              # SQLiteデータベース
│   ├── main.py            # FastAPIエントリポイント
│   ├── config.py          # 設定
│   ├── .env               # 環境変数
│   ├── requirements.txt
│   └── Dockerfile
├── .gitignore
└── CLAUDE.md
```

## フェーズ概要

### Phase 0: プロジェクトセットアップ
- モノレポ構造作成（frontend/ + backend/）
- Next.jsアプリ初期化（App Router, TypeScript, Tailwind CSS）
- FastAPIアプリ初期化 + 既存Pythonコードコピー
- CORS設定

### Phase 1: バックエンド読み取りAPI
- `GET /api/dashboard/kpis` - KPI集計データ
- `GET /api/dashboard/charts` - チャートデータ
- `GET /api/search/filters` - フィルター選択肢
- `GET /api/search/listings` - 案件一覧
- `GET /api/search/export` - CSVエクスポート
- `GET /api/fetch/status` - 取得状態
- `GET /api/fetch/logs` - ログ
- `GET /api/settings` - 設定情報

### Phase 2: フロントエンド - レイアウト＋ダッシュボード
- サイドバーナビゲーション
- KPIカード4つ + Rechartsチャート4つ（スキル棒、単価ヒストグラム、エリア円、トレンド線）
- 期間フィルター（7日/30日/90日/全期間）

### Phase 3: フロントエンド - 検索ページ
- フィルターサイドバー（キーワード、スキル、エリア、職種、単価範囲、日付範囲）
- 結果テーブル + 展開詳細ビュー
- CSVエクスポートボタン

### Phase 4: バックエンド書き込み + Gmail OAuth
- Gmail OAuth再設計（バックエンド管理方式、リダイレクトURI対応）
- `POST /api/fetch/full-pipeline` - フルパイプライン実行
- `POST /api/fetch/ai-only` - AI解析のみ
- `POST /api/fetch/mock` - モックデータ投入
- `GET /api/fetch/progress/{job_id}` - SSE進捗
- `PUT /api/settings` - 設定更新
- バックグラウンドタスク管理

### Phase 5: フロントエンド - メール取得 + 設定ページ
- Gmail接続状態表示 + アクションボタン3つ
- SSEベースのリアルタイム進捗バー
- 設定フォーム（ラベル、キーワード、APIキー、モデル選択、処理パラメータ）

### Phase 6: 仕上げ + デプロイ
- エラーハンドリング、レスポンシブ対応
- Dockerfileの作成（バックエンド用）
- Render（バックエンド）+ Cloudflare Pages（フロントエンド）にデプロイ
- 基本テスト作成

## 既存ファイル流用方針
| ファイル | 方針 |
|---------|------|
| `core/database.py` | そのまま流用（DB操作すべて） |
| `core/gmail_client.py` | OAuth部分のみ修正 |
| `core/gemini_extractor.py` | 変更なし |
| `core/batch_processor.py` | 進捗コールバックをSSE用に修正 |
| `core/mock_data.py` | 変更なし |
| `models/schemas.py` | API用レスポンスモデル追加 |
| `utils/text_helpers.py` | 変更なし |
| `utils/date_helpers.py` | 変更なし |
| `utils/chart_helpers.py` | ★削除（チャートはフロントエンドで描画） |

## リスクと対策
1. **SQLite永続化（Render）**: Render Disk（無料1GB）を使用
2. **Gmail OAuthリダイレクトURI**: 開発用・本番用の両方をGoogle Cloud Consoleに登録
3. **CORS**: フロントとバックが別ドメインのためCORS設定必須
4. **Renderコールドスタート**: 15分アイドルでスリープ（30秒起動）→ cron pingで回避可能
5. **Cloudflare + Next.js互換性**: `"use client"`で全ページCSRに統一

## 作業メモ
- gmail_analyzerフォルダでClaude Codeを開いて作業を再開する
- まず社用PCのStreamlit起動問題を解決してから移行作業に入る
