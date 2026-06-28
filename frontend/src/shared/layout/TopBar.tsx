import { useLocation } from "react-router-dom";
import { LogOut } from "lucide-react";
import { useAuthStore } from "@/features/auth/authStore";
import { ThemeToggle } from "@/shared/theme/ThemeToggle";
import { GlobalSearch } from "@/shared/layout/GlobalSearch";
import { NotificationBell } from "@/shared/layout/NotificationBell";
import { Logo } from "@/shared/layout/Logo";

function getInitials(email: string): string {
  const local = email.split("@")[0] ?? "";
  const parts = local.split(/[._-]/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (local || email).slice(0, 2).toUpperCase() || "??";
}

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/inbox": "Posteingang",
  "/bookings": "Buchungen",
  "/cancellations": "Stornos",
  "/changes": "Änderungen",
  "/messages": "Nachrichten",
  "/properties": "Unterkünfte",
  "/support": "Support",
  "/review": "Review-Warteschlange",
  "/settings": "Einstellungen",
  "/admin/overview": "Plattform-Übersicht",
  "/admin/accounts": "Konten & Freigaben",
  "/admin/activity": "Aktivität",
  "/admin/observability": "Observability",
  "/admin/diagnostics": "System-Diagnose",
  "/admin/llm-config": "LLM-Konfiguration",
  "/admin/workflows": "Workflows",
  "/admin/tickets": "Support-Tickets",
  "/admin/audit": "Audit-Log",
};

export function TopBar() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const initials = user?.email ? getInitials(user.email) : "??";
  const location = useLocation();

  const pageTitle =
    PAGE_TITLES[location.pathname] ??
    (location.pathname.startsWith("/admin") ? "Admin-Konsole" : "Mail Assistant");

  return (
    <header className="flex h-[58px] flex-none items-center justify-between border-b border-border bg-surface px-4 md:px-[18px]">
      <div className="flex min-w-0 items-center gap-2.5">
        <div className="lg:hidden">
          <Logo size={34} showAdminDot={isPlatformAdmin} />
        </div>
        <h1 className="truncate text-base font-extrabold tracking-tight text-ink">
          {pageTitle}
        </h1>
      </div>

      <div className="flex items-center gap-2.5">
        <GlobalSearch />
        <ThemeToggle />
        <NotificationBell />
        <div
          className="flex h-[34px] w-[34px] items-center justify-center rounded-lg bg-brand-gradient-140 text-[12px] font-bold text-white"
          title={user?.email ?? undefined}
        >
          {initials}
        </div>
        <button
          type="button"
          onClick={logout}
          title="Abmelden"
          aria-label="Abmelden"
          className="flex h-[34px] w-[34px] items-center justify-center rounded-lg border border-border bg-app text-muted transition-colors hover:text-dangertext"
        >
          <LogOut size={15} />
        </button>
      </div>
    </header>
  );
}
