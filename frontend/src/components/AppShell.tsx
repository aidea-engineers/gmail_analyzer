"use client";

import { usePathname } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import Sidebar from "@/components/Sidebar";

type Role = "admin" | "sales" | "engineer";

/** パスごとのアクセス許可ロール定義 */
const ROUTE_GUARDS: { prefix: string; allowedRoles: Role[] }[] = [
  { prefix: "/admin/users", allowedRoles: ["admin"] },
  { prefix: "/fetch", allowedRoles: ["admin"] },
  { prefix: "/settings", allowedRoles: ["admin"] },
  { prefix: "/my-profile", allowedRoles: ["engineer"] },
  { prefix: "/search", allowedRoles: ["admin", "sales"] },
  { prefix: "/engineers", allowedRoles: ["admin", "sales"] },
  { prefix: "/matching", allowedRoles: ["admin", "sales"] },
  { prefix: "/", allowedRoles: ["admin", "sales"] },
];

/** ロール別のデフォルトホームページ */
function getHomePage(role: Role): string {
  if (role === "engineer") return "/my-profile";
  return "/"; // admin, sales
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  // ログインページ・パスワード設定ページはSidebarなしで表示
  if (pathname === "/login" || pathname === "/set-password") {
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

  const userRole = (user.role || "engineer") as Role;

  // エンジニアロールでプロフィール未紐付け → マイプロフィールに強制リダイレクト
  if (
    userRole === "engineer" &&
    !user.engineer_id &&
    pathname !== "/my-profile"
  ) {
    if (typeof window !== "undefined") {
      window.location.href = "/my-profile";
    }
    return null;
  }

  // ルートガード: 許可されていないページへのアクセスをリダイレクト
  const guard = ROUTE_GUARDS.find((g) => pathname.startsWith(g.prefix));
  if (guard && !guard.allowedRoles.includes(userRole)) {
    const home = getHomePage(userRole);
    if (typeof window !== "undefined" && pathname !== home) {
      window.location.href = home;
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
