import { NavLink } from "react-router-dom";
import { Zap } from "lucide-react";
import { useSidebarNav } from "@/shared/layout/useSidebarNav";

export function Sidebar() {
  const { links, isPlatformAdmin, pending, pendingApprovals, navCountFor } =
    useSidebarNav();

  return (
    <aside className="hidden lg:flex w-56 flex-col" style={{ background: "#0c1222" }}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5">
        <div
          className="flex h-8 w-8 items-center justify-center rounded-lg"
          style={{ background: "linear-gradient(135deg, #6366f1, #818cf8)" }}
        >
          <Zap size={16} className="text-white" />
        </div>
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
            AI Mail
          </p>
          <p className="text-sm font-bold text-white leading-tight">
            {isPlatformAdmin ? "Plattform" : "Platform"}
          </p>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-3 mb-2 h-px bg-white/[0.06]" />

      {/* Nav */}
      <nav aria-label="Hauptnavigation" className="flex-1 overflow-y-auto px-2 py-2">
        <div className="space-y-0.5">
          {links.map(({ to, label, icon: Icon, badge, navCountKey }) => {
            const navCount = navCountFor(navCountKey);
            return (
              <NavLink
                key={to}
                to={to}
                end={to === "/" || to === "/admin/overview"}
                className={({ isActive }) =>
                  `group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 ${
                    isActive
                      ? "bg-indigo-600 text-white"
                      : "text-slate-400 hover:bg-white/[0.07] hover:text-white"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {/* Active left bar */}
                    {isActive && (
                      <span className="absolute -left-2 top-1.5 bottom-1.5 w-1 rounded-r-full bg-indigo-300" />
                    )}
                    <Icon
                      size={16}
                      aria-hidden="true"
                      className={`flex-shrink-0 ${isActive ? "text-indigo-200" : "text-slate-500 group-hover:text-slate-300"}`}
                    />
                    <span className="flex-1 truncate">{label}</span>
                    {navCountKey && navCount != null && navCount > 0 && (
                      <span
                        className={`min-w-[20px] rounded-full px-1.5 py-0.5 text-center text-[10px] font-bold tabular-nums ${
                          isActive ? "bg-indigo-500 text-indigo-100" : "bg-slate-700/80 text-slate-300"
                        }`}
                      >
                        {navCount}
                      </span>
                    )}
                    {badge && !isPlatformAdmin && pending > 0 && (
                      <span className="min-w-[20px] animate-pulse rounded-full bg-red-500 px-1.5 py-0.5 text-center text-[10px] font-bold text-white">
                        {pending}
                      </span>
                    )}
                    {badge && isPlatformAdmin && pendingApprovals > 0 && (
                      <span className="min-w-[20px] rounded-full bg-amber-500 px-1.5 py-0.5 text-center text-[10px] font-bold text-white">
                        {pendingApprovals}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Bottom */}
      <div className="mx-3 my-2 h-px bg-white/[0.06]" />
      <div className="px-3 pb-3 pt-1">
        <div className="flex items-center gap-2 rounded-lg px-2 py-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          <span className="text-[11px] text-slate-500">System aktiv</span>
        </div>
      </div>
    </aside>
  );
}
