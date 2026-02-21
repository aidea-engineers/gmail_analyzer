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
import type { SkillCount } from "@/types";

export default function SkillBarChart({ data }: { data: SkillCount[] }) {
  const top15 = data.slice(0, 15);

  return (
    <div
      className="rounded-xl p-4 shadow-sm border"
      style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
    >
      <h3 className="text-sm font-semibold mb-3">スキル別案件数</h3>
      {top15.length === 0 ? (
        <p className="text-sm text-slate-400 py-8 text-center">データなし</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={top15} layout="vertical" margin={{ left: 60 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="skill_name" type="category" width={80} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
