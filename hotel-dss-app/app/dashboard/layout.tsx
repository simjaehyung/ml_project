"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ClipboardList,
  Settings2,
  Plus,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    label: "Overview",
    href: "/dashboard",
    icon: LayoutDashboard,
    exact: true,
  },
  {
    label: "New Booking",
    href: "/dashboard/reservations/new",
    icon: Plus,
    exact: false,
  },
  {
    label: "Reservations",
    href: "/dashboard/reservations",
    icon: ClipboardList,
    exact: false,
  },
  {
    label: "Flexi Policy",
    href: "/dashboard/flexi",
    icon: Settings2,
    exact: false,
  },
] as const;

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  function isActive(href: string, exact: boolean): boolean {
    if (exact) return pathname === href;
    return pathname.startsWith(href);
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--bg-dark)] text-white">
      {/* Sidebar */}
      <aside
        className="flex w-56 shrink-0 flex-col justify-between bg-[var(--bg-sidebar)] border-r border-white/10"
        style={{ minWidth: "14rem" }}
      >
        {/* Logo */}
        <div>
          <div className="px-5 py-5 border-b border-white/10">
            <span className="text-base font-semibold tracking-tight">
              🏨 Hotel DSS
            </span>
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
                      ? "bg-white/10 text-white font-medium"
                      : "text-white/60 hover:bg-white/5 hover:text-white"
                  )}
                >
                  <Icon size={16} />
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Footer badge */}
        <div className="px-5 py-4 border-t border-white/10">
          <Badge
            variant="outline"
            className="text-[10px] text-white/50 border-white/20 bg-transparent"
          >
            LightGBM PR-AUC 0.8189
          </Badge>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-[var(--bg-dark)]">
        {children}
      </main>
    </div>
  );
}
