"use client";

interface KPICardProps {
  label: string;
  value: string;
  icon: string;
}

export default function KPICard({ label, value, icon }: KPICardProps) {
  return (
    <div
      className="rounded-xl p-5 shadow-sm border"
      style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
}
