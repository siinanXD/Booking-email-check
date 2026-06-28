import { NavLink } from "react-router-dom";
import { useAuthStore } from "@/features/auth/authStore";
import { useSidebarNav } from "@/shared/layout/useSidebarNav";
import { Logo } from "@/shared/layout/Logo";

type SidebarNavProps = {
  onNavigate?: () => void;
  id?: string;
};

export function SidebarNav({ onNavigate, id = "primary-navigation" }: SidebarNavProps) {
  const { links, isPlatformAdmin, pending, pendingApprovals, navCountFor } =
    useSidebarNav();

  return (
    <nav id={id} aria-label="Hauptnavigation" className="flex flex-1 flex-col gap-0.5 px-2.5 py-2">
      {links.map(({ to, label, icon: Icon, badge, navCountKey }) => {
        const navCount = navCountFor(navCountKey);
        return (
          <NavLink
            key={to}
            to={to}
            end={to === "/" || to === "/admin/overview"}
            onClick={() => onNavigate?.()}
            className={({ isActive }) =>
              `group relative flex min-h-11 items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-semibold transition-colors ${
                isActive
                  ? "bg-white/[0.08] text-white"
                  : "text-railtext hover:bg-white/[0.05] hover:text-white"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute -left-2.5 top-2 bottom-2 w-1 rounded-r-full bg-brand" />
                )}
                <Icon
                  size={17}
                  aria-hidden="true"
                  className={isActive ? "text-brand" : "text-railfaint group-hover:text-railtext"}
                />
                <span className="flex-1 truncate">{label}</span>
                {navCountKey && navCount != null && navCount > 0 && (
                  <span className="min-w-[20px] rounded-full bg-white/10 px-1.5 py-0.5 text-center text-[10px] font-bold tabular-nums text-railtext">
                    {navCount}
                  </span>
                )}
                {badge && !isPlatformAdmin && pending > 0 && (
                  <span className="min-w-[20px] rounded-full bg-red-500 px-1.5 py-0.5 text-center text-[10px] font-bold text-white">
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
    </nav>
  );
}

export function SidebarBrand() {
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  return (
    <div className="flex items-center gap-2.5 px-3 py-4">
      <Logo size={36} showAdminDot={isPlatformAdmin} />
      <div className="min-w-0">
        <p className="truncate text-[13.5px] font-extrabold leading-none text-white">
          Mail Assistant
        </p>
        <p
          className={`mt-1.5 text-[9px] font-bold uppercase leading-none tracking-[0.16em] ${
            isPlatformAdmin ? "text-amber-300" : "text-brand"
          }`}
        >
          {isPlatformAdmin ? "Admin" : "Mandant"}
        </p>
      </div>
    </div>
  );
}
