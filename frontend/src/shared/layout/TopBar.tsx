import { Link } from "react-router-dom";
import { LogOut, Menu, User } from "lucide-react";
import { useAuthStore } from "@/features/auth/authStore";
import { Button } from "@/shared/ui/Button";

type Props = {
  onOpenMenu: () => void;
  menuOpen: boolean;
};

export function TopBar({ onOpenMenu, menuOpen }: Props) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const profileLink = isPlatformAdmin ? "/admin/overview" : "/settings";
  const title = isPlatformAdmin ? "Plattform-Admin" : "AI Mail";

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between gap-2 border-b border-slate-200 bg-white/95 px-3 backdrop-blur supports-[backdrop-filter]:bg-white/80 sm:px-6 pt-[env(safe-area-inset-top)]">
      <div className="flex min-w-0 flex-1 items-center gap-2">
        <button
          type="button"
          className="inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-lg text-slate-700 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 lg:hidden"
          aria-label="Menü öffnen"
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={onOpenMenu}
        >
          <Menu size={22} aria-hidden="true" />
        </button>
        <h1 className="truncate text-base font-semibold text-slate-800 sm:text-lg">
          {title}
        </h1>
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:gap-3">
        <Link
          to={profileLink}
          className="flex max-w-[9rem] items-center gap-2 rounded-lg px-2 py-2 text-sm text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 sm:max-w-xs"
          title="Einstellungen"
          aria-label={`Einstellungen${user?.email ? ` (${user.email})` : ""}`}
        >
          <User size={18} aria-hidden="true" />
          <span className="hidden truncate sm:inline">{user?.email ?? "—"}</span>
        </Link>
        <Button
          variant="ghost"
          onClick={logout}
          aria-label="Abmelden"
          className="min-h-11 min-w-11 px-2"
        >
          <LogOut size={18} aria-hidden="true" />
        </Button>
      </div>
    </header>
  );
}
