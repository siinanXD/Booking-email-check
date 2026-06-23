import { NavLink } from "react-router-dom";
import { useAuthStore } from "@/features/auth/authStore";
import { useSidebarNav } from "@/shared/layout/useSidebarNav";

type SidebarNavProps = {
  onNavigate?: () => void;
  id?: string;
};

export function SidebarNav({ onNavigate, id = "primary-navigation" }: SidebarNavProps) {
  const { links, isPlatformAdmin, pending, pendingApprovals, navCountFor } =
    useSidebarNav();

  return (
    <nav id={id} aria-label="Hauptnavigation" className="flex-1 space-y-1 p-3">
      {links.map(({ to, label, icon: Icon, badge, navCountKey }) => {
        const navCount = navCountFor(navCountKey);
        return (
          <NavLink
            key={to}
            to={to}
            end={to === "/" || to === "/admin/overview"}
            onClick={() => onNavigate?.()}
            className={({ isActive }) =>
              `flex min-h-11 items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400 ${
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-slate-300 hover:bg-slate-800"
              }`
            }
          >
            <Icon size={18} aria-hidden="true" />
            <span className="flex-1">{label}</span>
            {navCountKey && navCount != null && navCount > 0 && (
              <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-200">
                {navCount}
              </span>
            )}
            {badge && !isPlatformAdmin && pending > 0 && (
              <span className="animate-pulse rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white">
                {pending}
              </span>
            )}
            {badge && isPlatformAdmin && pendingApprovals > 0 && (
              <span className="rounded-full bg-amber-500 px-2 py-0.5 text-xs font-bold text-white">
                {pendingApprovals}
              </span>
            )}
          </NavLink>
        );
      })}
    </nav>
  );
}

export function SidebarBrand() {
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  return (
    <div className="px-4 py-5">
      <p className="text-xs uppercase tracking-wide text-slate-400">AI Mail</p>
      <p className="font-semibold text-white">
        {isPlatformAdmin ? "Plattform" : "Platform"}
      </p>
    </div>
  );
}
