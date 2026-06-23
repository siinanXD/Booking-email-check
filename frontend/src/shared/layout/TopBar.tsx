import { Link, useLocation } from "react-router-dom";
import { LogOut, Settings, Menu } from "lucide-react";
import { useAuthStore } from "@/features/auth/authStore";

function getInitials(email: string): string {
  const local = email.split("@")[0] ?? "";
  const parts = local.split(/[._-]/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return (local || email).slice(0, 2).toUpperCase() || "??";
}

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/bookings": "Buchungen",
  "/cancellations": "Stornos",
  "/changes": "Änderungen",
  "/messages": "Nachrichten",
  "/properties": "Unterkünfte",
  "/support": "Support",
  "/review": "Review-Warteschlange",
  "/ground-zero": "Ground Zero",
  "/completed": "Abgeschlossen",
  "/settings": "Einstellungen",
  "/costs": "API-Kosten",
  "/workflows": "Workflows",
};

type TopBarProps = {
  onMenuOpen?: () => void;
};

export function TopBar({ onMenuOpen }: TopBarProps) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const profileLink = isPlatformAdmin ? "/admin/overview" : "/settings";
  const initials = user?.email ? getInitials(user.email) : "??";
  const location = useLocation();

  const pageTitle =
    PAGE_TITLES[location.pathname] ??
    (location.pathname.startsWith("/admin") ? "Admin-Konsole" : "AI Mail Platform");

  return (
    <header className="flex h-14 flex-shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6">
      <div className="flex items-center gap-3">
        {/* Hamburger — only visible on mobile */}
        <button
          type="button"
          onClick={onMenuOpen}
          className="lg:hidden flex h-9 w-9 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
          aria-label="Menü öffnen"
        >
          <Menu size={20} />
        </button>
        <h1 className="text-base font-bold text-slate-900">{pageTitle}</h1>
      </div>

      <div className="flex items-center gap-1">
        {/* User */}
        <Link
          to={profileLink}
          className="group flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-slate-100"
          title="Profil & Einstellungen"
        >
          <div
            className="flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white flex-shrink-0"
            style={{ background: "linear-gradient(135deg, #6366f1, #818cf8)" }}
          >
            {initials}
          </div>
          {/* Email text — hidden on small screens */}
          <span className="hidden sm:block max-w-[160px] truncate text-sm font-medium text-slate-700 group-hover:text-slate-900">
            {user?.email ?? "—"}
          </span>
        </Link>

        <Link
          to={profileLink}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700"
          title="Einstellungen"
        >
          <Settings size={16} />
        </Link>

        <button
          type="button"
          onClick={logout}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
          title="Abmelden"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
