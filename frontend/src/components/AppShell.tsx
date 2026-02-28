"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import Sidebar from "@/components/Sidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  // ログインページはSidebarなしで表示
  if (pathname === "/login") {
    return <>{children}</>;
  }

  // ローディング中
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p style={{ color: "var(--muted)" }}>読み込み中...</p>
      </div>
    );
  }

  // 未認証 → ログインにリダイレクト
  if (!user) {
    // クライアントサイドリダイレクト
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return null;
  }

  return (
    <>
      <Sidebar />
      <main className="lg:ml-56 min-h-screen p-4 pt-14 lg:p-6">
        {children}
      </main>
    </>
  );
}
