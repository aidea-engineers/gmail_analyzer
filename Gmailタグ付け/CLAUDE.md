# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

Gmailアカウントのラベル付け・フィルタ設定を管理する運用プロジェクト。コードベースではなく、ブラウザ操作によるGmail設定作業が中心。

## 対象Gmailアカウント

- `cloudlink.company@gmail.com` (CloudLink 株式会社)

## 作業メモのルール

- 行ったことはすべて `作業メモ.md` に記録する
- 日付ごとにセクションを分け、作業内容と結果を簡潔に記載する
- このフォルダ内に格納する

## Gmail操作時の注意

- Chromeブラウザで複数Googleアカウントがログイン済み。`cloudlink.company@gmail.com` は `/mail/u/2/` にある
- Gmailフィルタ作成時、カスタムドロップダウン（ラベル選択）はJavaScriptの `div.J-N` クラスをクリックして選択する必要がある
- フィルタ作成・編集時の注意:
  - ラベル選択ドロップダウンは `div.J-N` クラスの要素をJavaScriptでクリックする
  - 「一致するスレッドにもフィルタを適用する」チェックボックスをUIで直接クリックするとフォームが閉じてしまう。JavaScriptで `checkbox.checked = true` + `dispatchEvent(new Event('change'))` した後、「フィルタを作成/更新」ボタンをクリックすること
  - フィルタ新規作成時に既存メールへの適用を忘れた場合は、フィルタ設定画面から「編集」→「続行」→ 上記JS手法でチェック → 「フィルタを更新」で対応可能

## 現在のフィルタ設定

| 条件 | 処理 |
|------|------|
| `to:(cloudlink.company@gmail.com)` | ラベル「SES案件」を付ける |
| `to:(partner@cloudsoft.jp)` | ラベル「SES案件」を付ける |
| `deliveredto:cloudlink.company@gmail.com` | ラベル「SES案件」を付ける |
