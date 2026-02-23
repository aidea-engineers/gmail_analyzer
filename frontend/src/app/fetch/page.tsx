"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getFetchStatus,
  getFetchLogs,
  startFullPipeline,
  startAIOnly,
  insertMockData,
  deleteAllData,
} from "@/lib/api";
import ProgressBar from "@/components/ProgressBar";
import type { FetchStatus, FetchLog, JobProgress } from "@/types";

export default function FetchPage() {
  const [status, setStatus] = useState<FetchStatus | null>(null);
  const [logs, setLogs] = useState<FetchLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [resultMessage, setResultMessage] = useState("");
  const [mockCount, setMockCount] = useState(150);

  const refresh = useCallback(() => {
    setLoading(true);
    Promise.all([getFetchStatus(), getFetchLogs()])
      .then(([s, l]) => {
        setStatus(s);
        setLogs(l.logs);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleComplete = useCallback((data: JobProgress) => {
    setActiveJobId(null);
    if (data.phase === "error") {
      setResultMessage(data.message);
    } else {
      setResultMessage(data.message);
    }
    refresh();
  }, [refresh]);

  const handleFullPipeline = async () => {
    setResultMessage("");
    const { job_id } = await startFullPipeline();
    setActiveJobId(job_id);
  };

  const handleAIOnly = async () => {
    setResultMessage("");
    const { job_id } = await startAIOnly();
    setActiveJobId(job_id);
  };

  const handleMock = async () => {
    setResultMessage("");
    const { inserted } = await insertMockData(mockCount);
    setResultMessage(`モックデータ ${inserted}件を投入しました`);
    refresh();
  };

  const handleClear = async () => {
    setResultMessage("");
    await deleteAllData();
    setResultMessage("全データを削除しました");
    refresh();
  };

  if (loading && !status) {
    return <div className="flex items-center justify-center py-20 text-slate-400">読み込み中...</div>;
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-6">メール取得・処理</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          APIエラー: {error}
        </div>
      )}

      {/* Gmail接続状態 */}
      <div className="mb-6">
        {status?.gmail_connected ? (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
            <span className="w-2 h-2 bg-green-500 rounded-full" />
            Gmail: 接続済み
          </div>
        ) : (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700 text-sm">
            <span className="w-2 h-2 bg-yellow-500 rounded-full" />
            Gmail: 未接続（バックエンド側で設定してください）
          </div>
        )}
      </div>

      {/* アクションボタン */}
      <div
        className="rounded-xl p-5 shadow-sm border mb-6"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <h2 className="text-sm font-bold mb-4">メール取得・AI解析</h2>
        <div className="flex gap-3">
          <button
            onClick={handleFullPipeline}
            disabled={!!activeJobId || !status?.gmail_connected}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            メール取得 + AI解析
          </button>
          <button
            onClick={handleAIOnly}
            disabled={!!activeJobId || !status?.gemini_api_key_set}
            className="px-4 py-2 bg-purple-600 text-white text-sm rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            未処理メールをAI解析
          </button>
        </div>

        {activeJobId && <ProgressBar jobId={activeJobId} onComplete={handleComplete} />}

        {resultMessage && !activeJobId && (
          <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-700 text-sm">
            {resultMessage}
          </div>
        )}
      </div>

      {/* モックデータ */}
      <div
        className="rounded-xl p-5 shadow-sm border mb-6"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <h2 className="text-sm font-bold mb-1">モックデータ（プロトタイプ用）</h2>
        <p className="text-xs text-slate-500 mb-4">Gmail接続前にUIの動作確認ができます</p>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600">
            件数:
            <input
              type="number"
              value={mockCount}
              onChange={(e) => setMockCount(Number(e.target.value))}
              min={10}
              max={500}
              step={10}
              className="ml-2 w-20 px-2 py-1 border rounded text-sm"
              style={{ borderColor: "var(--border)" }}
            />
          </label>
          <button
            onClick={handleMock}
            disabled={!!activeJobId}
            className="px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            モックデータ投入
          </button>
          <button
            onClick={handleClear}
            disabled={!!activeJobId}
            className="px-4 py-2 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 disabled:opacity-50 transition-colors"
          >
            全データ削除
          </button>
        </div>
      </div>

      {/* データ統計 */}
      <div
        className="rounded-xl p-5 shadow-sm border mb-6"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <h2 className="text-sm font-bold mb-4">データ統計</h2>
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold">{status?.total_emails ?? 0}</p>
            <p className="text-xs text-slate-500">総メール数</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold">{status?.processed_emails ?? 0}</p>
            <p className="text-xs text-slate-500">処理済み</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold">{status?.unprocessed_emails ?? 0}</p>
            <p className="text-xs text-slate-500">未処理</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold">{status?.total_listings ?? 0}</p>
            <p className="text-xs text-slate-500">抽出済み案件</p>
          </div>
        </div>
      </div>

      {/* 取得ログ */}
      <div
        className="rounded-xl p-5 shadow-sm border"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <h2 className="text-sm font-bold mb-4">取得ログ</h2>
        {logs.length === 0 ? (
          <p className="text-sm text-slate-400">取得ログはまだありません</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs text-slate-500" style={{ borderColor: "var(--border)" }}>
                  <th className="py-2 pr-4">開始日時</th>
                  <th className="py-2 pr-4">完了日時</th>
                  <th className="py-2 pr-4">取得数</th>
                  <th className="py-2 pr-4">処理数</th>
                  <th className="py-2">ステータス</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b" style={{ borderColor: "var(--border)" }}>
                    <td className="py-2 pr-4 text-xs">{log.started_at?.slice(0, 19)?.replace("T", " ")}</td>
                    <td className="py-2 pr-4 text-xs">{log.finished_at?.slice(0, 19)?.replace("T", " ") ?? "-"}</td>
                    <td className="py-2 pr-4">{log.emails_fetched}</td>
                    <td className="py-2 pr-4">{log.emails_processed}</td>
                    <td className="py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          log.status === "completed"
                            ? "bg-green-100 text-green-700"
                            : log.status === "running"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
