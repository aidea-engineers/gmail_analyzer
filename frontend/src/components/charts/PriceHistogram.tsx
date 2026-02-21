"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PriceData } from "@/types";

function buildBins(data: PriceData[]) {
  const ranges = [
    { label: "~30万", min: 0, max: 30 },
    { label: "30-40万", min: 30, max: 40 },
    { label: "40-50万", min: 40, max: 50 },
    { label: "50-60万", min: 50, max: 60 },
    { label: "60-70万", min: 60, max: 70 },
    { label: "70-80万", min: 70, max: 80 },
    { label: "80-90万", min: 80, max: 90 },
    { label: "90万~", min: 90, max: 999 },
  ];

  return ranges.map((range) => {
    const count = data.filter((d) => {
      const avg =
        ((d.unit_price_min ?? 0) + (d.unit_price_max ?? 0)) / 2;
      return avg >= range.min && avg < range.max;
    }).length;
    return { label: range.label, count };
  });
}

export default function PriceHistogram({ data }: { data: PriceData[] }) {
  const bins = buildBins(data);

  return (
    <div
      className="rounded-xl p-4 shadow-sm border"
      style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
    >
      <h3 className="text-sm font-semibold mb-3">単価分布</h3>
      {data.length === 0 ? (
        <p className="text-sm text-slate-400 py-8 text-center">データなし</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={bins}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
