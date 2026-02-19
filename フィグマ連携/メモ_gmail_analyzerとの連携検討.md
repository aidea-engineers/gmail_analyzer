# gmail_analyzerとFigma連携の検討

## 調査日: 2026-02-19

---

## gmail_analyzerの概要
- SES案件メール解析Webダッシュボード
- 技術スタック: Streamlit (Python), SQLite, Gmail API, Gemini AI
- パス: ~/Desktop/gmail_analyzer
- 4ページ構成: ダッシュボード、案件検索、メール取得、設定

## Figma連携は可能か？
→ **可能だが、Streamlitの制約に注意が必要**

### Streamlitの制約
- HTML/CSSの自由なカスタマイズが難しい
- レイアウトの自由度が低い
- Figmaで凝ったデザインを作っても完全再現は困難

### 選択肢
1. **Streamlitのまま連携** - 大まかなデザイン参考として活用（変更少）
2. **フロントエンド変更して連携** - React/Next.js等に移行し、Figmaデザインを完全再現（変更大）

## 結論
- ユーザーの方針次第で次のステップが変わる
- 要確認: Streamlitのまま進めるか、フロントエンド変更するか
