"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SetPasswordPage() {
  const router = useRouter();

  useEffect(() => {
    // パスワード設定はmy-profileページ内で行うため、リダイレクト
    router.replace("/my-profile");
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--background)" }}>
      <p style={{ color: "var(--muted)" }}>リダイレクト中...</p>
    </div>
  );
}
