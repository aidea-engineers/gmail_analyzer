"use client";

import { useEffect, useState } from "react";
import { getSettings, updateSettings, getFetchStatus } from "@/lib/api";
import type { Settings, FetchStatus } from "@/types";

const MODEL_OPTIONS = [
  "gemini-2.0-flash",
  "gemini-2.0-flash-lite",
  "gemini-2.5-flash",
  "gemini-2.5-pro",
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [fetchStatus, setFetchStatus] = useState<FetchStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // フォーム状態
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-2.0-flash");
  const [gmailLabels, setGmailLabels] = useState("");
  const [gmailKeywords, setGmailKeywords] = useState("");
  const [batchSize, setBatchSize] = useState(50);
  const [maxEmails, setMaxEmails] = useState(500);
  const [geminiDelay, setGeminiDelay] = useState(1.0);

  useEffect(() => {
    Promise.all([getSettings(), getFetchStatus()])
      .then(([s, f]) => {
        setSettings(s);
        setFetchStatus(f);
        setGeminiModel(s.gemini_model);
        setGmailLabels(s.gmail_labels.join(","));
        setGmailKeywords(s.gmail_keywords.join(","));
        setBatchSize(s.batch_size);
        setMaxEmails(s.max_emails_per_fetch);
        setGeminiDelay(s.gemini_delay_seconds);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const data: Record<string, unknown> = {
        gemini_model: geminiModel,
        gmail_labels: gmailLabels,
        gmail_keywords: gmailKeywords,
        batch_size: batchSize,
        max_emails_per_fetch: maxEmails,
        gemini_delay_seconds: geminiDelay,
      };
      if (geminiApiKey) {
        data.gemini_api_key = geminiApiKey;
      }
      const res = await updateSettings(data as import("@/types").SettingsUpdate);
      setMessage(res.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-slate-400">読み込み中...</div>;
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-bold mb-6">設定</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
        </div>
      )}
      {message && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
          {message}
        </div>
      )}

      {/* Gmail設定 */}
      <section
        className="rounded-xl p-5 shadow-sm border mb-6"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <h2 className="text-sm font-bold mb-4">Gmail設定</h2>

        <div className="mb-4">
          {fetchStatus?.gmail_connected ? (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
              <span className="w-2 h-2 bg-green-500 rounded-full" />
              Gmail: 接続済み
            </div>
          ) : (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-sm">
              <span className="w-2 h-2 bg-yellow-500 rounded-full" />
              Gmail: 未接続
            </div>
          )}
        </div>

        <label className="block text-sm text-slate-600 mb-1">対象ラベル（カンマ区切り）</label>
        <input
          type="text"
          value={gmailLabels}
          onChange={(e) => setGmailLabels(e.target.value)}
          className="w-full mb-3 px-3 py-2 border rounded-lg text-sm"
          style={{ borderColor: "var(--border)" }}
        />

        <label className="block text-sm text-slate-600 mb-1">検索キーワード（カンマ区切り）</label>
        <input
          type="text"
          value={gmailKeywords}
          onChange={(e) => setGmailKeywords(e.target.value)}
          className="w-full px-3 py-2 border rounded-lg text-sm"
          style={{ borderColor: "var(--border)" }}
        />
      </section>

      {/* Gemini API設定 */}
      <section
        className="rounded-xl p-5 shadow-sm border mb-6"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <h2 className="text-sm font-bold mb-4">Gemini API設定</h2>

        <label className="block text-sm text-slate-600 mb-1">
          APIキー {settings?.gemini_api_key_set && <span className="text-green-600">（設定済み）</span>}
        </label>
        <input
          type="password"
          value={geminiApiKey}
          onChange={(e) => setGeminiApiKey(e.target.value)}
          placeholder={settings?.gemini_api_key_set ? "変更する場合のみ入力" : "APIキーを入力"}
          className="w-full mb-3 px-3 py-2 border rounded-lg text-sm"
          style={{ borderColor: "var(--border)" }}
        />

        <label className="block text-sm text-slate-600 mb-1">モデル</label>
        <select
          value={geminiModel}
          onChange={(e) => setGeminiModel(e.target.value)}
          className="w-full px-3 py-2 border rounded-lg text-sm"
          style={{ borderColor: "var(--border)" }}
        >
          {MODEL_OPTIONS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </section>

      {/* 処理設定 */}
      <section
        className="rounded-xl p-5 shadow-sm border mb-6"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <h2 className="text-sm font-bold mb-4">処理設定</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">バッチサイズ</label>
            <input
              type="number"
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              min={10}
              max={500}
              step={10}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              style={{ borderColor: "var(--border)" }}
            />
            <p className="text-xs text-slate-400 mt-1">1回のAI解析で処理するメール数</p>
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">最大メール取得数</label>
            <input
              type="number"
              value={maxEmails}
              onChange={(e) => setMaxEmails(Number(e.target.value))}
              min={50}
              max={2000}
              step={50}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              style={{ borderColor: "var(--border)" }}
            />
            <p className="text-xs text-slate-400 mt-1">1回のGmail取得で取得するメール数</p>
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">API呼び出し間隔（秒）</label>
            <input
              type="number"
              value={geminiDelay}
              onChange={(e) => setGeminiDelay(Number(e.target.value))}
              min={0.5}
              max={10}
              step={0.5}
              className="w-full px-3 py-2 border rounded-lg text-sm"
              style={{ borderColor: "var(--border)" }}
            />
            <p className="text-xs text-slate-400 mt-1">レート制限対策のウェイト</p>
          </div>
        </div>
      </section>

      {/* 保存ボタン */}
      <button
        onClick={handleSave}
        disabled={saving}
        className="px-6 py-2.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
      >
        {saving ? "保存中..." : "設定を保存"}
      </button>
    </div>
  );
}
