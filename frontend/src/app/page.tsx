"use client";

import { useEffect, useState } from "react";
import KPICard from "@/components/KPICard";
import CollapsibleSection from "@/components/CollapsibleSection";
import SkillBarChart from "@/components/charts/SkillBarChart";
import PriceHistogram from "@/components/charts/PriceHistogram";
import AreaPieChart from "@/components/charts/AreaPieChart";
import TrendLineChart from "@/components/charts/TrendLineChart";
import { getKPIs, getCharts, getMonthlySummary } from "@/lib/api";
import type { KPIs, ChartsResponse, MonthlySummary } from "@/types";

const PERIODS = ["7日", "30日", "90日", "全期間"] as const;
type Period = (typeof PERIODS)[number];

export default function DashboardPage() {
  const [period, setPeriod] = useState<Period>("30日");
  const [granularity, setGranularity] = useState<"daily" | "weekly">("daily");
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [charts, setCharts] = useState<ChartsResponse | null>(null);
  const [monthly, setMonthly] = useState<MonthlySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    Promise.all([getKPIs(period), getCharts(period, granularity), getMonthlySummary()])
      .then(([k, c, m]) => {
        if (!cancelled) {
          setKpis(k);
          setCharts(c);
          setMonthly(m);
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
        <div className="flex flex-col gap-4">
          {/* KPI サマリー（総案件数・本日の新着・エリア数） */}
          <CollapsibleSection title="サマリー" defaultOpen={true}>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              <KPICard label="総案件数" value={`${kpis?.total ?? 0}件`} icon="📋" />
              <KPICard label="本日の新着" value={`${kpis?.today_count ?? 0}件`} icon="🆕" />
              <KPICard label="エリア数" value={`${kpis?.area_count ?? 0}`} icon="📍" />
            </div>
          </CollapsibleSection>

          {/* 単価情報（平均単価 + 単価分布）— デフォルト閉じ */}
          <CollapsibleSection title="単価情報" defaultOpen={false}>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <KPICard label="平均単価" value={`${kpis?.avg_price ?? 0}万円`} icon="💰" />
              <PriceHistogram data={charts?.prices ?? []} />
            </div>
          </CollapsibleSection>

          {/* スキル分布 */}
          <CollapsibleSection title="スキル分布" defaultOpen={true}>
            <SkillBarChart data={charts?.skills ?? []} />
          </CollapsibleSection>

          {/* エリア分布 */}
          <CollapsibleSection title="エリア分布" defaultOpen={true}>
            <AreaPieChart data={charts?.areas ?? []} />
          </CollapsibleSection>

          {/* トレンド */}
          <CollapsibleSection title="案件トレンド" defaultOpen={true}>
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
          </CollapsibleSection>

          {/* 月別サマリー */}
          <CollapsibleSection title="月別サマリー" defaultOpen={true}>
            {monthly.length === 0 ? (
              <p className="text-sm text-slate-400">データなし</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)" }}>
                      <th className="text-left py-2 px-3 font-medium">月</th>
                      <th className="text-right py-2 px-3 font-medium">案件数</th>
                      <th className="text-right py-2 px-3 font-medium">平均単価</th>
                      <th className="text-right py-2 px-3 font-medium">会社数</th>
                      <th className="text-left py-2 px-3 font-medium">最多エリア</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthly.map((row) => (
                      <tr key={row.month} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td className="py-2 px-3">{row.month}</td>
                        <td className="py-2 px-3 text-right">{row.listing_count}件</td>
                        <td className="py-2 px-3 text-right">
                          {row.avg_price != null ? `${row.avg_price}万円` : "-"}
                        </td>
                        <td className="py-2 px-3 text-right">{row.unique_companies}</td>
                        <td className="py-2 px-3">{row.top_area || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CollapsibleSection>
        </div>
      )}
    </div>
  );
}
