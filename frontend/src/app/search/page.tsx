"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getFilters, getListings, getExportURL } from "@/lib/api";
import type { SearchFilters, JobListing } from "@/types";

export default function SearchPage() {
  const router = useRouter();
  const [filters, setFilters] = useState<SearchFilters | null>(null);
  const [listings, setListings] = useState<JobListing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [perPage] = useState(50);

  // フィルター状態
  const [keyword, setKeyword] = useState("");
  const [keywordMode, setKeywordMode] = useState<"and" | "or">("and");
  const [companySearch, setCompanySearch] = useState("");
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
    if (keyword) {
      params.keyword = keyword;
      params.keyword_mode = keywordMode;
    }
    if (companySearch.trim()) params.companies = companySearch.trim();
    if (selectedSkills.length) params.skills = selectedSkills.join(",");
    if (selectedAreas.length) params.areas = selectedAreas.join(",");
    if (selectedJobTypes.length) params.job_types = selectedJobTypes.join(",");
    if (priceMin) params.price_min = priceMin;
    if (priceMax) params.price_max = priceMax;
    if (dateFrom) params.date_from = dateFrom;
    if (dateTo) params.date_to = dateTo;
    return params;
  }, [keyword, keywordMode, companySearch, selectedSkills, selectedAreas, selectedJobTypes, priceMin, priceMax, dateFrom, dateTo]);

  const doSearch = useCallback(() => {
    setLoading(true);
    setError("");
    const params = buildParams();
    params.page = String(page);
    params.per_page = String(perPage);
    getListings(params)
      .then((res) => {
        setListings(res.listings);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [buildParams, page, perPage]);

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
    setKeywordMode("and");
    setCompanySearch("");
    setSelectedSkills([]);
    setSelectedAreas([]);
    setSelectedJobTypes([]);
    setPriceMin("");
    setPriceMax("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="flex gap-6 h-[calc(100vh-3.5rem)]">
      {/* サイドバーフィルター */}
      <div
        className="w-64 shrink-0 rounded-xl p-4 shadow-sm border overflow-y-auto"
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
          placeholder="AWS Java（スペース区切り）"
          className="w-full mb-2 px-2 py-1.5 border rounded text-sm"
          style={{ borderColor: "var(--border)" }}
        />
        <div className="flex items-center gap-1 mb-3">
          <span className="text-xs text-slate-400 mr-1">検索条件:</span>
          <button
            onClick={() => setKeywordMode("and")}
            className={`px-2 py-0.5 text-xs rounded-l border transition-colors ${
              keywordMode === "and"
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50"
            }`}
          >
            AND
          </button>
          <button
            onClick={() => setKeywordMode("or")}
            className={`px-2 py-0.5 text-xs rounded-r border border-l-0 transition-colors ${
              keywordMode === "or"
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50"
            }`}
          >
            OR
          </button>
        </div>

        {/* 会社名 */}
        <label className="block text-xs text-slate-500 mb-1">会社名</label>
        <input
          type="text"
          value={companySearch}
          onChange={(e) => setCompanySearch(e.target.value)}
          placeholder="例: クラウドワークス"
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
      <div className="flex-1 min-w-0 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-xl font-bold">案件検索</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500">
              検索結果: {total}件{totalPages > 1 && ` (${page}/${totalPages}ページ)`}
            </span>
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
              className="grid grid-cols-[100px_1fr_120px_120px_100px_80px_60px] gap-2 px-4 py-2 text-xs font-semibold text-slate-500 border-b"
              style={{ borderColor: "var(--border)" }}
            >
              <span>日付</span>
              <span>会社名</span>
              <span>職種</span>
              <span>エリア</span>
              <span>単価</span>
              <span>参画月</span>
              <span>確信度</span>
            </div>

            {/* テーブル行 */}
            {listings.map((item) => (
              <div key={item.id}>
                <div
                  className="grid grid-cols-[100px_1fr_120px_120px_100px_80px_60px] gap-2 px-4 py-3 rounded-lg border cursor-pointer hover:bg-slate-50 transition-colors"
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
                  <span className="text-xs text-slate-600 truncate">
                    {item.start_month || "-"}
                  </span>
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
                        <p><span className="font-semibold">参画月:</span> {item.start_month || "未記載"}</p>
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
                    {item.requirements && (
                      <div className="mt-3 p-3 rounded-lg" style={{ background: "#eef2ff", border: "1px solid #c7d2fe" }}>
                        <p className="text-sm">
                          <span className="font-semibold text-indigo-700">必須要件・求める人物像:</span>
                        </p>
                        <p className="text-sm mt-1 whitespace-pre-wrap">{item.requirements}</p>
                      </div>
                    )}
                    <div className="mt-3">
                      <button
                        onClick={() =>
                          router.push(`/matching?tab=listing&id=${item.id}`)
                        }
                        className="px-3 py-1.5 bg-purple-600 text-white text-xs rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        マッチするエンジニアを探す
                      </button>
                    </div>
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

        {/* ページネーション */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4 pb-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-30"
              style={{ background: "var(--card-bg)", border: "1px solid var(--border)", color: "var(--foreground)" }}
            >
              前へ
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              let p: number;
              if (totalPages <= 7) {
                p = i + 1;
              } else if (page <= 4) {
                p = i + 1;
              } else if (page >= totalPages - 3) {
                p = totalPages - 6 + i;
              } else {
                p = page - 3 + i;
              }
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-3 py-1.5 rounded-lg text-sm ${
                    page === p ? "text-white" : ""
                  }`}
                  style={{
                    background: page === p ? "var(--primary)" : "var(--card-bg)",
                    border: "1px solid var(--border)",
                    color: page === p ? "white" : "var(--foreground)",
                  }}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg text-sm disabled:opacity-30"
              style={{ background: "var(--card-bg)", border: "1px solid var(--border)", color: "var(--foreground)" }}
            >
              次へ
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
