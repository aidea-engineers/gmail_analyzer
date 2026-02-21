"use client";

import { useEffect, useState } from "react";
import KPICard from "@/components/KPICard";
import SkillBarChart from "@/components/charts/SkillBarChart";
import PriceHistogram from "@/components/charts/PriceHistogram";
import AreaPieChart from "@/components/charts/AreaPieChart";
import TrendLineChart from "@/components/charts/TrendLineChart";
import { getKPIs, getCharts } from "@/lib/api";
import type { KPIs, ChartsResponse } from "@/types";

const PERIODS = ["7日", "30日", "90日", "全期間"] as const;
type Period = (typeof PERIODS)[number];

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>("30日");
  const [granularity, setGranularity] = useState<"daily" | "weekly">("daily");
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [charts, setCharts] = useState<ChartsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    Promise.all([getKPIs(period), getCharts(period, granularity)])
      .then(([k, c]) => {
        if (!cancelled) {
          setKpis(k);
          setCharts(c);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [period, granularity]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">SES案件ダッシュボード</h1>
        <div className="flex gap-1 rounded-lg p-1" style={{ background: "var(--border)" }}>
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                period === p
                  ? "bg-blue-600 text-white"
                  : "hover:bg-slate-200 text-slate-600"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          APIエラー: {error}
          <span className="block text-xs mt-1">バックエンド (localhost:8000) が起動しているか確認してください</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          読み込み中...
        </div>
      ) : (
        <>
          {/* KPI カード */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <KPICard label="総案件数" value={`${kpis?.total ?? 0}件`} icon="📋" />
            <KPICard label="平均単価" value={`${kpis?.avg_price ?? 0}万円`} icon="💰" />
            <KPICard label="本日の新着" value={`${kpis?.today_count ?? 0}件`} icon="🆕" />
            <KPICard label="エリア数" value={`${kpis?.area_count ?? 0}`} icon="📍" />
          </div>

          {/* チャート 2x2 */}
          <div className="grid grid-cols-2 gap-4">
            <SkillBarChart data={charts?.skills ?? []} />
            <PriceHistogram data={charts?.prices ?? []} />
            <AreaPieChart data={charts?.areas ?? []} />
            <div>
              <div className="flex gap-2 mb-2">
                <button
                  onClick={() => setGranularity("daily")}
                  className={`px-3 py-1 rounded text-xs ${
                    granularity === "daily"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-200 text-slate-600"
                  }`}
                >
                  日別
                </button>
                <button
                  onClick={() => setGranularity("weekly")}
                  className={`px-3 py-1 rounded text-xs ${
                    granularity === "weekly"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-200 text-slate-600"
                  }`}
                >
                  週別
                </button>
              </div>
              <TrendLineChart data={charts?.trend ?? []} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
