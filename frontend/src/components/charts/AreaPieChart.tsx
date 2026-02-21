"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { AreaCount } from "@/types";

const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
];

export default function AreaPieChart({ data }: { data: AreaCount[] }) {
  const top10 = data.slice(0, 10);

  return (
    <div
      className="rounded-xl p-4 shadow-sm border"
      style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
    >
      <h3 className="text-sm font-semibold mb-3">エリア別案件数</h3>
      {top10.length === 0 ? (
        <p className="text-sm text-slate-400 py-8 text-center">データなし</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={top10}
              dataKey="count"
              nameKey="work_area"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) =>
                `${name ?? ""} ${((percent ?? 0) * 100).toFixed(0)}%`
              }
              labelLine={false}
              fontSize={11}
            >
              {top10.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
