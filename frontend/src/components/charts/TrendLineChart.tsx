"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { TrendData } from "@/types";

export default function TrendLineChart({ data }: { data: TrendData[] }) {
  return (
    <div
      className="rounded-xl p-4 shadow-sm border"
      style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
    >
      <h3 className="text-sm font-semibold mb-3">案件数トレンド</h3>
      {data.length === 0 ? (
        <p className="text-sm text-slate-400 py-8 text-center">データなし</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="period" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
