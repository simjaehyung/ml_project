"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ClipboardList, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard",    href: "/pms",              icon: LayoutDashboard, exact: true },
  { label: "Reservations", href: "/pms/reservations", icon: ClipboardList,   exact: false },
] as const;

export default function PMSLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  function isActive(href: string, exact: boolean): boolean {
    return exact ? pathname === href : pathname.startsWith(href);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950 text-white">
      {/* Sidebar */}
      <aside className="flex w-56 shrink-0 flex-col justify-between bg-slate-900 border-r border-slate-700/50">
        <div>
          {/* Logo */}
          <div className="px-5 py-5 border-b border-slate-700/50">
            <div className="flex items-center gap-2">
              <span className="text-lg">🏨</span>
              <div>
                <p className="text-sm font-bold tracking-tight text-white">Grand Hotel</p>
                <p className="text-[10px] text-slate-400 font-medium">PMS — Property Mgmt</p>
              </div>
            </div>
          </div>

          {/* Nav */}
          <nav className="mt-3 flex flex-col gap-0.5 px-2">
            {NAV_ITEMS.map(({ label, href, icon: Icon, exact }) => {
              const active = isActive(href, exact);
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-blue-600/20 text-blue-300 font-medium border border-blue-500/20"
                      : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  )}
                >
                  <Icon size={15} />
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* DSS 링크 */}
          <div className="mt-4 px-4">
            <div className="text-[10px] text-slate-600 uppercase tracking-wider mb-2 px-1">연동 시스템</div>
            <Link
              href="/dashboard"
              className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
            >
              <Bot size={14} className="text-amber-500/60" />
              <span>DSS Manager View</span>
              <span className="ml-auto text-[10px] text-slate-600">→</span>
            </Link>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-slate-700/50">
          <div className="text-[10px] text-slate-600">
            <p>PMS v2.0 · Port 3001</p>
            <p className="mt-0.5 text-slate-700">Connected to DSS :8001</p>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto bg-slate-950">
        {children}
      </main>
    </div>
  );
}
