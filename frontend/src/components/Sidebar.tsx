"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";

const ADMIN_NAV_ITEMS = [
  { href: "/", label: "ダッシュボード", icon: "📊" },
  { href: "/search", label: "案件検索", icon: "🔍" },
  { href: "/engineers", label: "エンジニア管理", icon: "👤" },
  { href: "/matching", label: "マッチング", icon: "🤝" },
  { href: "/admin/users", label: "アカウント管理", icon: "🔑" },
  { href: "/fetch", label: "メール取得", icon: "📧" },
  { href: "/settings", label: "設定", icon: "⚙️" },
];

const ENGINEER_NAV_ITEMS = [
  { href: "/my-profile", label: "マイプロフィール", icon: "👤" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { user, signOut } = useAuth();

  const navItems = user?.is_admin ? ADMIN_NAV_ITEMS : ENGINEER_NAV_ITEMS;

  return (
    <>
      {/* モバイルハンバーガー */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed top-3 left-3 z-50 lg:hidden p-2 rounded-lg"
        style={{ background: "var(--sidebar-bg)", color: "var(--sidebar-text)" }}
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
          {open ? (
            <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" />
          ) : (
            <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none" />
          )}
        </svg>
      </button>

      {/* オーバーレイ（モバイル） */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* サイドバー */}
      <aside
        className={`fixed left-0 top-0 h-full w-56 flex flex-col z-40 transition-transform lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ background: "var(--sidebar-bg)", color: "var(--sidebar-text)" }}
      >
        <div className="p-4 border-b border-slate-600">
          <h1 className="text-lg font-bold">AIdea Platform</h1>
          <p className="text-xs text-slate-400 mt-1">SES事業管理システム</p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-blue-600 text-white"
                    : "hover:bg-slate-700 text-slate-300"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-slate-600">
          {user && (
            <div className="mb-3">
              <p className="text-xs text-slate-400 truncate">{user.email}</p>
              <p className="text-xs text-slate-500">
                {user.is_admin ? "管理者" : "エンジニア"}
              </p>
            </div>
          )}
          <button
            onClick={signOut}
            className="w-full text-left text-xs text-slate-400 hover:text-white transition-colors"
          >
            ログアウト
          </button>
          <p className="text-xs text-slate-600 mt-2">v1.0.0</p>
        </div>
      </aside>
    </>
  );
}
