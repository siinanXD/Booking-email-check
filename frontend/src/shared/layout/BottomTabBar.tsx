import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Inbox,
  ClipboardCheck,
  Building2,
  Shield,
  Activity,
  Users,
  Ticket,
  MoreHorizontal,
} from "lucide-react";
import { useAuthStore } from "@/features/auth/authStore";

type Tab = { to: string; label: string; icon: typeof Inbox; end?: boolean };

const tenantTabs: Tab[] = [
  { to: "/", label: "Start", icon: LayoutDashboard, end: true },
  { to: "/inbox", label: "Posteingang", icon: Inbox },
  { to: "/review", label: "Review", icon: ClipboardCheck },
  { to: "/properties", label: "Unterk.", icon: Building2 },
];

const adminTabs: Tab[] = [
  { to: "/admin/overview", label: "Übersicht", icon: Shield, end: true },
  { to: "/admin/activity", label: "Aktivität", icon: Activity },
  { to: "/admin/accounts", label: "Konten", icon: Users },
  { to: "/admin/tickets", label: "Tickets", icon: Ticket },
];

type Props = { onMore: () => void };

/** Untere Tab-Bar für Mobil (4 Haupt-Tabs + „Mehr"-Sheet). */
export function BottomTabBar({ onMore }: Props) {
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const tabs = isPlatformAdmin ? adminTabs : tenantTabs;

  return (
    <nav
      aria-label="Hauptnavigation"
      className="flex flex-none items-stretch border-t border-border bg-surface lg:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {tabs.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            `flex min-h-[52px] flex-1 flex-col items-center justify-center gap-1 py-1.5 text-[10px] font-semibold ${
              isActive ? "text-brandink" : "text-faint"
            }`
          }
        >
          <Icon size={20} />
          <span className="truncate">{label}</span>
        </NavLink>
      ))}
      <button
        type="button"
        onClick={onMore}
        className="flex min-h-[52px] flex-1 flex-col items-center justify-center gap-1 py-1.5 text-[10px] font-semibold text-faint"
      >
        <MoreHorizontal size={20} />
        <span>Mehr</span>
      </button>
    </nav>
  );
}
