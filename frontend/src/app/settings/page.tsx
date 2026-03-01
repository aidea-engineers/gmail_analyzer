"use client";

import { useEffect, useState, useRef } from "react";
import { getSettings, updateSettings, getFetchStatus, importDataCsv } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
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

      {/* データインポート（管理者のみ） */}
      <DataImportSection />
    </div>
  );
}


function DataImportSection() {
  const { user } = useAuth();
  if (!user?.is_admin) return null;

  return (
    <section
      className="rounded-xl p-5 shadow-sm border mt-8"
      style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
    >
      <h2 className="text-sm font-bold mb-4">データインポート（Fairgrit CSV）</h2>
      <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
        Fairgritからエクスポートした CSV をインポートできます（Shift-JIS / UTF-8 両対応）
      </p>
      <div className="space-y-4">
        <ImportUploader label="社員情報" type="employees" />
        <ImportUploader label="案件情報" type="assignments" />
        <ImportUploader label="取引先情報" type="companies" />
      </div>
    </section>
  );
}


function ImportUploader({ label, type }: { label: string; type: "employees" | "assignments" | "companies" }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ imported: number; updated?: number; skipped?: number; errors: string[] } | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setResult(null);
    try {
      const res = await importDataCsv(type, file);
      setResult(res as { imported: number; updated?: number; skipped?: number; errors: string[] });
    } catch (err) {
      setResult({ imported: 0, errors: [err instanceof Error ? err.message : "インポートに失敗しました"] });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="p-3 rounded-lg" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium flex-shrink-0" style={{ color: "var(--foreground)" }}>{label}</span>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={handleUpload}
          disabled={uploading}
          className="text-sm flex-1"
        />
        {uploading && <span className="text-xs" style={{ color: "var(--muted)" }}>インポート中...</span>}
      </div>
      {result && (
        <div className="mt-2 text-xs">
          <p style={{ color: result.errors.length === 0 ? "green" : "var(--foreground)" }}>
            インポート: {result.imported}件
            {result.updated !== undefined && ` / 更新: ${result.updated}件`}
            {result.skipped !== undefined && result.skipped > 0 && ` / スキップ(重複): ${result.skipped}件`}
          </p>
          {result.errors.length > 0 && (
            <div className="mt-1 text-red-500 max-h-24 overflow-y-auto">
              {result.errors.map((err, i) => (
                <p key={i}>{err}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
