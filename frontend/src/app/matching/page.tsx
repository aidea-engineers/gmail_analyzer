"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  getMatchingStats,
  getEngineersBrief,
  getListingsForEngineer,
  getEngineersForListing,
  getListings,
  createProposal,
  updateProposal,
  deleteProposal,
  getProposals,
} from "@/lib/api";
import type {
  MatchingStats,
  EngineerBrief,
  ListingMatchResult,
  EngineerMatchResult,
  MatchProposal,
  JobListing,
  CategorizedSkills,
} from "@/types";

const STATUS_COLORS: Record<string, string> = {
  "候補": "bg-gray-100 text-gray-700",
  "提案済み": "bg-blue-100 text-blue-700",
  "面談中": "bg-yellow-100 text-yellow-800",
  "成約": "bg-green-100 text-green-700",
  "見送り": "bg-red-100 text-red-700",
};

const STATUSES = ["候補", "提案済み", "面談中", "成約", "見送り"];

const SKILL_CAT_COLORS: Record<string, string> = {
  "言語": "bg-blue-100 text-blue-700",
  "FW": "bg-purple-100 text-purple-700",
  "インフラ": "bg-orange-100 text-orange-700",
  "DB": "bg-green-100 text-green-700",
  "その他": "bg-gray-100 text-gray-600",
};

function getSkillBadgeClass(skill: string, categorized?: CategorizedSkills): string {
  if (!categorized) return "bg-slate-100 text-slate-600";
  for (const [cat, skills] of Object.entries(categorized)) {
    if (skills.includes(skill)) return SKILL_CAT_COLORS[cat] || SKILL_CAT_COLORS["その他"];
  }
  return SKILL_CAT_COLORS["その他"];
}

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 80 ? "#22c55e" : score >= 50 ? "#eab308" : "#ef4444";
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-3 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, background: color }}
        />
      </div>
      <span className="text-xs font-bold" style={{ color }}>
        {score}
      </span>
    </div>
  );
}

function ScoreDetail({ detail }: { detail: { skill: number; area: number; price: number } }) {
  return (
    <div className="flex gap-3 text-xs text-slate-500">
      <span>スキル: {detail.skill}/50</span>
      <span>エリア: {detail.area}/25</span>
      <span>単価: {detail.price}/25</span>
    </div>
  );
}

export default function MatchingPage() {
  return (
    <Suspense fallback={<div className="text-center py-20 text-slate-400">読み込み中...</div>}>
      <MatchingContent />
    </Suspense>
  );
}

function MatchingContent() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const idParam = searchParams.get("id");

  const [activeTab, setActiveTab] = useState<"engineer" | "listing" | "proposals">(
    tabParam === "listing" ? "listing" : tabParam === "proposals" ? "proposals" : "engineer"
  );

  // --- タブ1: エンジニアから探す ---
  const [engineers, setEngineers] = useState<EngineerBrief[]>([]);
  const [selectedEngineerId, setSelectedEngineerId] = useState<number | null>(
    tabParam === "engineer" && idParam ? parseInt(idParam) : null
  );
  const [listingMatches, setListingMatches] = useState<ListingMatchResult[]>([]);
  const [loadingListings, setLoadingListings] = useState(false);

  // --- タブ2: 案件から探す ---
  const [recentListings, setRecentListings] = useState<JobListing[]>([]);
  const [selectedListingId, setSelectedListingId] = useState<number | null>(
    tabParam === "listing" && idParam ? parseInt(idParam) : null
  );
  const [engineerMatches, setEngineerMatches] = useState<EngineerMatchResult[]>([]);
  const [loadingEngineers, setLoadingEngineers] = useState(false);

  // --- タブ3: 提案管理 ---
  const [stats, setStats] = useState<MatchingStats | null>(null);
  const [proposals, setProposals] = useState<MatchProposal[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [expandedProposalId, setExpandedProposalId] = useState<number | null>(null);
  const [editNotes, setEditNotes] = useState("");

  const [error, setError] = useState("");

  // 初期データ読み込み
  useEffect(() => {
    getEngineersBrief().then(setEngineers).catch(() => {});
    getListings({}).then((res) => setRecentListings(res.listings.slice(0, 100))).catch(() => {});
    getMatchingStats().then(setStats).catch(() => {});
  }, []);

  // URLパラメータからの自動検索
  useEffect(() => {
    if (tabParam === "engineer" && idParam) {
      const id = parseInt(idParam);
      if (!isNaN(id)) {
        setActiveTab("engineer");
        setSelectedEngineerId(id);
      }
    } else if (tabParam === "listing" && idParam) {
      const id = parseInt(idParam);
      if (!isNaN(id)) {
        setActiveTab("listing");
        setSelectedListingId(id);
      }
    }
  }, [tabParam, idParam]);

  // エンジニア選択時 → 案件マッチング
  useEffect(() => {
    if (selectedEngineerId && activeTab === "engineer") {
      setLoadingListings(true);
      setError("");
      getListingsForEngineer(selectedEngineerId)
        .then((res) => setListingMatches(res.matches))
        .catch((e) => setError(e.message))
        .finally(() => setLoadingListings(false));
    }
  }, [selectedEngineerId, activeTab]);

  // 案件選択時 → エンジニアマッチング
  useEffect(() => {
    if (selectedListingId && activeTab === "listing") {
      setLoadingEngineers(true);
      setError("");
      getEngineersForListing(selectedListingId)
        .then((res) => setEngineerMatches(res.matches))
        .catch((e) => setError(e.message))
        .finally(() => setLoadingEngineers(false));
    }
  }, [selectedListingId, activeTab]);

  // 提案一覧
  const loadProposals = useCallback(() => {
    setLoadingProposals(true);
    const params: Record<string, string> = {};
    if (statusFilter) params.status = statusFilter;
    getProposals(params)
      .then((res) => setProposals(res.proposals))
      .catch((e) => setError(e.message))
      .finally(() => setLoadingProposals(false));
  }, [statusFilter]);

  useEffect(() => {
    if (activeTab === "proposals") {
      loadProposals();
      getMatchingStats().then(setStats).catch(() => {});
    }
  }, [activeTab, loadProposals]);

  // 提案作成
  const handlePropose = async (engineerId: number, listingId: number, score: number) => {
    try {
      await createProposal({ engineer_id: engineerId, listing_id: listingId, score });
      // マッチ結果を再取得
      if (activeTab === "engineer" && selectedEngineerId) {
        const res = await getListingsForEngineer(selectedEngineerId);
        setListingMatches(res.matches);
      } else if (activeTab === "listing" && selectedListingId) {
        const res = await getEngineersForListing(selectedListingId);
        setEngineerMatches(res.matches);
      }
      getMatchingStats().then(setStats).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // 提案ステータス更新
  const handleUpdateStatus = async (proposalId: number, status: string) => {
    try {
      await updateProposal(proposalId, { status, notes: editNotes || undefined });
      loadProposals();
      getMatchingStats().then(setStats).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    }
  };

  // 提案削除
  const handleDeleteProposal = async (proposalId: number) => {
    if (!confirm("この提案を削除しますか？")) return;
    try {
      await deleteProposal(proposalId);
      loadProposals();
      getMatchingStats().then(setStats).catch(() => {});
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const tabs = [
    { key: "engineer" as const, label: "エンジニアから探す" },
    { key: "listing" as const, label: "案件から探す" },
    { key: "proposals" as const, label: "提案管理" },
  ];

  return (
    <div>
      <h1 className="text-xl font-bold mb-4">マッチング</h1>

      {/* KPIバー */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
          {[
            { label: "候補", value: stats.candidate, color: "#6b7280" },
            { label: "提案済み", value: stats.proposed, color: "#3b82f6" },
            { label: "面談中", value: stats.interviewing, color: "#eab308" },
            { label: "成約", value: stats.closed, color: "#22c55e" },
            { label: "見送り", value: stats.rejected, color: "#ef4444" },
          ].map((kpi) => (
            <div
              key={kpi.label}
              className="rounded-xl p-3 shadow-sm border"
              style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
            >
              <p className="text-xs text-slate-500">{kpi.label}</p>
              <p className="text-2xl font-bold" style={{ color: kpi.color }}>
                {kpi.value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* タブ切替 */}
      <div className="flex gap-1 mb-4 border-b" style={{ borderColor: "var(--border)" }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              activeTab === tab.key
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline text-xs">
            閉じる
          </button>
        </div>
      )}

      {/* タブ1: エンジニアから探す */}
      {activeTab === "engineer" && (
        <div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">エンジニアを選択</label>
            <select
              value={selectedEngineerId ?? ""}
              onChange={(e) => {
                const v = e.target.value ? parseInt(e.target.value) : null;
                setSelectedEngineerId(v);
                if (!v) setListingMatches([]);
              }}
              className="w-full max-w-md px-3 py-2 border rounded-lg text-sm"
              style={{ borderColor: "var(--border)" }}
            >
              <option value="">選択してください</option>
              {engineers.map((eng) => (
                <option key={eng.id} value={eng.id}>
                  {eng.name}（{eng.status}）
                </option>
              ))}
            </select>
          </div>

          {loadingListings ? (
            <div className="text-center py-10 text-slate-400">検索中...</div>
          ) : selectedEngineerId && listingMatches.length === 0 ? (
            <div className="text-center py-10 text-slate-400">
              マッチする案件がありません（直近30日）
            </div>
          ) : (
            <div className="space-y-2">
              {listingMatches.map((m) => (
                <div
                  key={m.listing.id}
                  className="p-4 rounded-lg border"
                  style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-medium text-sm">
                          {m.listing.company_name || "不明"}
                        </span>
                        <ScoreBar score={m.score} />
                        {m.proposal && (
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full ${
                              STATUS_COLORS[m.proposal.status] ?? ""
                            }`}
                          >
                            {m.proposal.status}
                          </span>
                        )}
                      </div>
                      <ScoreDetail detail={m.score_detail} />
                      <div className="flex gap-4 mt-1 text-xs text-slate-500">
                        <span>エリア: {m.listing.work_area || "-"}</span>
                        <span>単価: {m.listing.unit_price || "-"}</span>
                        <span>職種: {m.listing.job_type || "-"}</span>
                      </div>
                      {m.listing.required_skills && m.listing.required_skills.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {m.listing.required_skills.map((sk) => (
                            <span
                              key={sk}
                              className={`px-1.5 py-0.5 text-xs rounded ${getSkillBadgeClass(sk, m.listing.categorized_skills)}`}
                            >
                              {sk}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="ml-3 shrink-0">
                      {!m.proposal ? (
                        <button
                          onClick={() =>
                            handlePropose(selectedEngineerId!, m.listing.id, m.score)
                          }
                          className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          提案する
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">提案済み</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* タブ2: 案件から探す */}
      {activeTab === "listing" && (
        <div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">案件を選択</label>
            <select
              value={selectedListingId ?? ""}
              onChange={(e) => {
                const v = e.target.value ? parseInt(e.target.value) : null;
                setSelectedListingId(v);
                if (!v) setEngineerMatches([]);
              }}
              className="w-full max-w-md px-3 py-2 border rounded-lg text-sm"
              style={{ borderColor: "var(--border)" }}
            >
              <option value="">選択してください</option>
              {recentListings.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.company_name || "不明"} - {l.work_area || "?"} ({l.unit_price || "?"})
                </option>
              ))}
            </select>
          </div>

          {loadingEngineers ? (
            <div className="text-center py-10 text-slate-400">検索中...</div>
          ) : selectedListingId && engineerMatches.length === 0 ? (
            <div className="text-center py-10 text-slate-400">
              マッチするエンジニアがいません（待機中/面談中）
            </div>
          ) : (
            <div className="space-y-2">
              {engineerMatches.map((m) => (
                <div
                  key={m.engineer.id}
                  className="p-4 rounded-lg border"
                  style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-medium text-sm">{m.engineer.name}</span>
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full ${
                            m.engineer.status === "待機中"
                              ? "bg-green-100 text-green-800"
                              : "bg-yellow-100 text-yellow-800"
                          }`}
                        >
                          {m.engineer.status}
                        </span>
                        <ScoreBar score={m.score} />
                        {m.proposal && (
                          <span
                            className={`px-2 py-0.5 text-xs rounded-full ${
                              STATUS_COLORS[m.proposal.status] ?? ""
                            }`}
                          >
                            {m.proposal.status}
                          </span>
                        )}
                      </div>
                      <ScoreDetail detail={m.score_detail} />
                      <div className="flex gap-4 mt-1 text-xs text-slate-500">
                        <span>エリア: {m.engineer.preferred_areas || "指定なし"}</span>
                        <span>
                          単価:{" "}
                          {m.engineer.current_price
                            ? `${m.engineer.current_price}万`
                            : "-"}
                          {(m.engineer.desired_price_min || m.engineer.desired_price_max) && (
                            <> (希望{m.engineer.desired_price_min ?? "?"}〜{m.engineer.desired_price_max ?? "?"})</>
                          )}
                        </span>
                        <span>
                          経験: {m.engineer.experience_years != null ? `${m.engineer.experience_years}年` : "-"}
                        </span>
                      </div>
                      {m.engineer.skills && m.engineer.skills.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {m.engineer.skills.map((sk) => (
                            <span
                              key={sk}
                              className={`px-1.5 py-0.5 text-xs rounded ${getSkillBadgeClass(sk, m.engineer.categorized_skills)}`}
                            >
                              {sk}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="ml-3 shrink-0">
                      {!m.proposal ? (
                        <button
                          onClick={() =>
                            handlePropose(m.engineer.id, selectedListingId!, m.score)
                          }
                          className="px-3 py-1.5 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors"
                        >
                          提案する
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">提案済み</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* タブ3: 提案管理 */}
      {activeTab === "proposals" && (
        <div>
          {/* フィルター */}
          <div className="flex items-center gap-3 mb-4">
            <label className="text-sm text-slate-500">ステータス:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 border rounded-lg text-sm"
              style={{ borderColor: "var(--border)" }}
            >
              <option value="">すべて</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <span className="text-sm text-slate-400">{proposals.length}件</span>
          </div>

          {loadingProposals ? (
            <div className="text-center py-10 text-slate-400">読み込み中...</div>
          ) : proposals.length === 0 ? (
            <div className="text-center py-10 text-slate-400">
              提案がありません
            </div>
          ) : (
            <div className="space-y-2">
              {/* ヘッダー */}
              <div
                className="grid grid-cols-[1fr_1fr_80px_80px_100px] gap-2 px-4 py-2 text-xs font-semibold text-slate-500 border-b"
                style={{ borderColor: "var(--border)" }}
              >
                <span>エンジニア</span>
                <span>案件（会社名）</span>
                <span>スコア</span>
                <span>ステータス</span>
                <span>更新日</span>
              </div>

              {proposals.map((p) => (
                <div key={p.id}>
                  <div
                    className="grid grid-cols-[1fr_1fr_80px_80px_100px] gap-2 px-4 py-3 rounded-lg border cursor-pointer hover:bg-slate-50 transition-colors"
                    style={{
                      background: "var(--card-bg)",
                      borderColor:
                        expandedProposalId === p.id ? "var(--primary)" : "var(--border)",
                    }}
                    onClick={() => {
                      if (expandedProposalId === p.id) {
                        setExpandedProposalId(null);
                      } else {
                        setExpandedProposalId(p.id);
                        setEditNotes(p.notes || "");
                      }
                    }}
                  >
                    <span className="text-sm font-medium truncate">
                      {p.engineer_name || `ID:${p.engineer_id}`}
                    </span>
                    <span className="text-sm truncate">
                      {p.listing_company || `ID:${p.listing_id}`}
                    </span>
                    <span>
                      <ScoreBar score={p.score} />
                    </span>
                    <span>
                      <span
                        className={`inline-block px-2 py-0.5 text-xs rounded-full ${
                          STATUS_COLORS[p.status] ?? "bg-gray-100 text-gray-500"
                        }`}
                      >
                        {p.status}
                      </span>
                    </span>
                    <span className="text-xs text-slate-500">
                      {p.updated_at?.slice(0, 10) ?? ""}
                    </span>
                  </div>

                  {/* 展開詳細 */}
                  {expandedProposalId === p.id && (
                    <div
                      className="mx-2 mb-2 p-4 rounded-b-lg border border-t-0"
                      style={{ background: "#f8fafc", borderColor: "var(--primary)" }}
                    >
                      <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                        <div>
                          <p>
                            <span className="font-semibold">エンジニア:</span>{" "}
                            {p.engineer_name || `ID:${p.engineer_id}`}
                          </p>
                          <p>
                            <span className="font-semibold">案件:</span>{" "}
                            {p.listing_company || `ID:${p.listing_id}`}
                          </p>
                          <p>
                            <span className="font-semibold">スコア:</span> {p.score}点
                          </p>
                        </div>
                        <div>
                          <p>
                            <span className="font-semibold">登録日:</span>{" "}
                            {p.created_at?.slice(0, 10) ?? ""}
                          </p>
                          <p>
                            <span className="font-semibold">更新日:</span>{" "}
                            {p.updated_at?.slice(0, 10) ?? ""}
                          </p>
                        </div>
                      </div>

                      {/* ステータス変更 */}
                      <div className="flex items-center gap-2 mb-3">
                        <label className="text-sm font-semibold">ステータス変更:</label>
                        {STATUSES.map((s) => (
                          <button
                            key={s}
                            onClick={() => handleUpdateStatus(p.id, s)}
                            className={`px-2 py-1 text-xs rounded transition-colors ${
                              p.status === s
                                ? "bg-blue-600 text-white"
                                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                            }`}
                          >
                            {s}
                          </button>
                        ))}
                      </div>

                      {/* メモ */}
                      <div className="mb-3">
                        <label className="block text-sm font-semibold mb-1">メモ</label>
                        <textarea
                          value={editNotes}
                          onChange={(e) => setEditNotes(e.target.value)}
                          rows={2}
                          className="w-full px-2 py-1.5 border rounded text-sm"
                          style={{ borderColor: "var(--border)" }}
                        />
                        <button
                          onClick={() =>
                            handleUpdateStatus(p.id, p.status)
                          }
                          className="mt-1 px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
                        >
                          メモ保存
                        </button>
                      </div>

                      <button
                        onClick={() => handleDeleteProposal(p.id)}
                        className="px-3 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600 transition-colors"
                      >
                        削除
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
