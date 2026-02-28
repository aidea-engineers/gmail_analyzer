"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { getEngineerDetail } from "@/lib/api";
import type { EngineerDetail } from "@/types";

export default function MyProfilePage() {
  const { user } = useAuth();
  const [engineer, setEngineer] = useState<EngineerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user?.engineer_id) {
      setLoading(false);
      return;
    }
    getEngineerDetail(user.engineer_id)
      .then(setEngineer)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [user?.engineer_id]);

  if (loading) {
    return <p style={{ color: "var(--muted)" }}>読み込み中...</p>;
  }

  if (!user?.engineer_id) {
    return (
      <div>
        <h1 className="text-2xl font-bold mb-4" style={{ color: "var(--foreground)" }}>
          マイプロフィール
        </h1>
        <p style={{ color: "var(--muted)" }}>
          エンジニア情報がまだ登録されていません。管理者にお問い合わせください。
        </p>
      </div>
    );
  }

  if (error) {
    return <p className="text-red-500">{error}</p>;
  }

  if (!engineer) {
    return <p style={{ color: "var(--muted)" }}>データが見つかりません</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6" style={{ color: "var(--foreground)" }}>
        マイプロフィール
      </h1>

      <div
        className="rounded-xl p-6 space-y-4"
        style={{ background: "var(--card-bg)", border: "1px solid var(--border)" }}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InfoField label="名前" value={engineer.name} />
          <InfoField label="ステータス" value={engineer.status} />
          <InfoField label="経験年数" value={engineer.experience_years ? `${engineer.experience_years}年` : ""} />
          <InfoField label="現在単価" value={engineer.current_price ? `${engineer.current_price}万円` : ""} />
          <InfoField label="希望エリア" value={engineer.preferred_areas} />
          <InfoField label="稼働可能日" value={engineer.available_from} />
        </div>

        {engineer.skills.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2" style={{ color: "var(--foreground)" }}>スキル</p>
            <div className="flex flex-wrap gap-1.5">
              {engineer.skills.map((s) => (
                <span
                  key={s}
                  className="px-2 py-0.5 rounded text-xs"
                  style={{ background: "var(--primary)", color: "white" }}
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {engineer.assignments.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2" style={{ color: "var(--foreground)" }}>担当案件</p>
            <div className="space-y-2">
              {engineer.assignments.map((a) => (
                <div
                  key={a.id}
                  className="p-3 rounded-lg text-sm"
                  style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                >
                  <p style={{ color: "var(--foreground)" }}>
                    {a.company_name} - {a.project_name}
                  </p>
                  <p className="text-xs" style={{ color: "var(--muted)" }}>
                    {a.start_date} ~ {a.end_date || "現在"} | {a.status}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div>
      <p className="text-xs" style={{ color: "var(--muted)" }}>{label}</p>
      <p className="text-sm" style={{ color: "var(--foreground)" }}>{value || "-"}</p>
    </div>
  );
}
