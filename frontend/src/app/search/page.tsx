"use client";

import { useEffect, useState, useCallback } from "react";
import { getFilters, getListings, getExportURL } from "@/lib/api";
import type { SearchFilters, JobListing } from "@/types";

export default function SearchPage() {
  const [filters, setFilters] = useState<SearchFilters | null>(null);
  const [listings, setListings] = useState<JobListing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // フィルター状態
  const [keyword, setKeyword] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedAreas, setSelectedAreas] = useState<string[]>([]);
  const [selectedJobTypes, setSelectedJobTypes] = useState<string[]>([]);
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // 展開中の案件ID
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    getFilters()
      .then(setFilters)
      .catch(() => {});
  }, []);

  const buildParams = useCallback(() => {
    const params: Record<string, string> = {};
    if (keyword) params.keyword = keyword;
    if (selectedSkills.length) params.skills = selectedSkills.join(",");
    if (selectedAreas.length) params.areas = selectedAreas.join(",");
    if (selectedJobTypes.length) params.job_types = selectedJobTypes.join(",");
    if (priceMin) params.price_min = priceMin;
    if (priceMax) params.price_max = priceMax;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [keyword, selectedSkills, selectedAreas, selectedJobTypes, priceMin, priceMax, dateFrom, dateTo]);

  const doSearch = useCallback(() => {
    setLoading(true);
    setError("");
    getListings(buildParams())
      .then((res) => {
        setListings(res.listings);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [buildParams]);

  useEffect(() => {
    doSearch();
  }, [doSearch]);

  const toggleMulti = (
    arr: string[],
    setter: React.Dispatch<React.SetStateAction<string[]>>,
    val: string
  ) => {
    setter(arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val]);
  };

  const clearFilters = () => {
    setKeyword("");
    setSelectedSkills([]);
    setSelectedAreas([]);
    setSelectedJobTypes([]);
    setPriceMin("");
    setPriceMax("");
    setDateFrom("");
    setDateTo("");
  };

  return (
    <div className="flex gap-6">
      {/* サイドバーフィルター */}
      <div
        className="w-64 shrink-0 rounded-xl p-4 shadow-sm border self-start sticky top-6"
        style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold">検索フィルタ</h2>
          <button onClick={clearFilters} className="text-xs text-blue-600 hover:underline">
            クリア
          </button>
        </div>

        {/* キーワード */}
        <label className="block text-xs text-slate-500 mb-1">フリーワード</label>
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="会社名・スキル等"
          className="w-full mb-3 px-2 py-1.5 border rounded text-sm"
          style={{ borderColor: "var(--border)" }}
        />

        {/* スキル */}
        <label className="block text-xs text-slate-500 mb-1">スキル</label>
        <div className="max-h-32 overflow-y-auto mb-3 space-y-1">
          {(filters?.skills ?? []).map((s) => (
            <label key={s} className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={selectedSkills.includes(s)}
                onChange={() => toggleMulti(selectedSkills, setSelectedSkills, s)}
              />
              {s}
            </label>
          ))}
        </div>

        {/* エリア */}
        <label className="block text-xs text-slate-500 mb-1">エリア</label>
        <div className="max-h-32 overflow-y-auto mb-3 space-y-1">
          {(filters?.areas ?? []).map((a) => (
            <label key={a} className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={selectedAreas.includes(a)}
                onChange={() => toggleMulti(selectedAreas, setSelectedAreas, a)}
              />
              {a}
            </label>
          ))}
        </div>

        {/* 職種 */}
        <label className="block text-xs text-slate-500 mb-1">職種</label>
        <div className="max-h-32 overflow-y-auto mb-3 space-y-1">
          {(filters?.job_types ?? []).map((j) => (
            <label key={j} className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={selectedJobTypes.includes(j)}
                onChange={() => toggleMulti(selectedJobTypes, setSelectedJobTypes, j)}
              />
              {j}
            </label>
          ))}
        </div>

        {/* 単価範囲 */}
        <label className="block text-xs text-slate-500 mb-1">単価範囲（万円）</label>
        <div className="flex gap-2 mb-3">
          <input
            type="number"
            value={priceMin}
            onChange={(e) => setPriceMin(e.target.value)}
            placeholder="下限"
            className="w-1/2 px-2 py-1.5 border rounded text-sm"
            style={{ borderColor: "var(--border)" }}
          />
          <input
            type="number"
            value={priceMax}
            onChange={(e) => setPriceMax(e.target.value)}
            placeholder="上限"
            className="w-1/2 px-2 py-1.5 border rounded text-sm"
            style={{ borderColor: "var(--border)" }}
          />
        </div>

        {/* 日付範囲 */}
        <label className="block text-xs text-slate-500 mb-1">期間</label>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="w-full mb-1 px-2 py-1.5 border rounded text-sm"
          style={{ borderColor: "var(--border)" }}
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="w-full mb-3 px-2 py-1.5 border rounded text-sm"
          style={{ borderColor: "var(--border)" }}
        />
      </div>

      {/* メインコンテンツ */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold">案件検索</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500">検索結果: {total}件</span>
            <a
              href={getExportURL(buildParams())}
              className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors"
            >
              CSV出力
            </a>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            APIエラー: {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            読み込み中...
          </div>
        ) : listings.length === 0 ? (
          <div className="text-center py-20 text-slate-400">
            条件に一致する案件がありません
          </div>
        ) : (
          <div className="space-y-2">
            {/* テーブルヘッダー */}
            <div
              className="grid grid-cols-[100px_1fr_120px_120px_100px_60px] gap-2 px-4 py-2 text-xs font-semibold text-slate-500 border-b"
              style={{ borderColor: "var(--border)" }}
            >
              <span>日付</span>
              <span>会社名</span>
              <span>職種</span>
              <span>エリア</span>
              <span>単価</span>
              <span>確信度</span>
            </div>

            {/* テーブル行 */}
            {listings.map((item) => (
              <div key={item.id}>
                <div
                  className="grid grid-cols-[100px_1fr_120px_120px_100px_60px] gap-2 px-4 py-3 rounded-lg border cursor-pointer hover:bg-slate-50 transition-colors"
                  style={{
                    background: "var(--card-bg)",
                    borderColor: expandedId === item.id ? "var(--primary)" : "var(--border)",
                  }}
                  onClick={() =>
                    setExpandedId(expandedId === item.id ? null : item.id)
                  }
                >
                  <span className="text-xs text-slate-500">
                    {item.created_at?.slice(0, 10) ?? ""}
                  </span>
                  <span className="text-sm font-medium truncate">
                    {item.company_name || "不明"}
                  </span>
                  <span className="text-xs text-slate-600 truncate">
                    {item.job_type}
                  </span>
                  <span className="text-xs text-slate-600 truncate">
                    {item.work_area}
                  </span>
                  <span className="text-xs font-medium">{item.unit_price}</span>
                  <span className="text-xs text-slate-500">
                    {(item.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                {/* 展開詳細 */}
                {expandedId === item.id && (
                  <div
                    className="mx-2 mb-2 p-4 rounded-b-lg border border-t-0"
                    style={{
                      background: "#f8fafc",
                      borderColor: "var(--primary)",
                    }}
                  >
                    <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                      <div>
                        <p><span className="font-semibold">会社名:</span> {item.company_name}</p>
                        <p><span className="font-semibold">職種:</span> {item.job_type}</p>
                        <p><span className="font-semibold">エリア:</span> {item.work_area}</p>
                        <p><span className="font-semibold">単価:</span> {item.unit_price}</p>
                      </div>
                      <div>
                        <p>
                          <span className="font-semibold">スキル:</span>{" "}
                          {item.required_skills.join(", ")}
                        </p>
                        <p>
                          <span className="font-semibold">確信度:</span>{" "}
                          {(item.confidence * 100).toFixed(0)}%
                        </p>
                        <p>
                          <span className="font-semibold">受信日:</span>{" "}
                          {item.received_at?.slice(0, 16)?.replace("T", " ") ?? ""}
                        </p>
                      </div>
                    </div>
                    <p className="text-sm">
                      <span className="font-semibold">案件内容:</span>{" "}
                      {item.project_details}
                    </p>
                    {item.subject && (
                      <p className="text-xs text-slate-400 mt-2">
                        メール件名: {item.subject}
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
