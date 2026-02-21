"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "ダッシュボード", icon: "📊" },
  { href: "/search", label: "案件検索", icon: "🔍" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-56 flex flex-col"
      style={{ background: "var(--sidebar-bg)", color: "var(--sidebar-text)" }}>
      <div className="p-4 border-b border-slate-600">
        <h1 className="text-lg font-bold">Gmail Analyzer</h1>
        <p className="text-xs text-slate-400 mt-1">SES案件メール解析</p>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
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
      <div className="p-4 border-t border-slate-600 text-xs text-slate-500">
        v0.1.0
      </div>
    </aside>
  );
}
