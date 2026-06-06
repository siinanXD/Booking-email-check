import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  CalendarCheck,
  XCircle,
  RefreshCw,
  MessageSquare,
  ClipboardCheck,
  AlertTriangle,
  CheckCircle2,
  Building2,
  Shield,
  Users,
  Stethoscope,
  LineChart,
  SlidersHorizontal,
  GitBranch,
  Tag,
  LifeBuoy,
  Ticket,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboardStats } from "@/lib/api/dashboard";
import { fetchPendingAccounts } from "@/lib/api/admin";
import { fetchWorkflowNav } from "@/lib/api/workflows";
import { useAuthStore } from "@/features/auth/authStore";

type NavCountKey =
  | "nav_bookings"
  | "nav_cancellations"
  | "nav_changes"
  | "nav_messages"
  | "nav_ground_zero"
  | "nav_completed";

type SidebarLink = {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: boolean;
  navCountKey?: NavCountKey;
};

const tenantLinks: SidebarLink[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  {
    to: "/bookings",
    label: "Buchungen",
    icon: CalendarCheck,
    navCountKey: "nav_bookings",
  },
  {
    to: "/cancellations",
    label: "Stornos",
    icon: XCircle,
    navCountKey: "nav_cancellations",
  },
  {
    to: "/changes",
    label: "Änderungen",
    icon: RefreshCw,
    navCountKey: "nav_changes",
  },
  {
    to: "/messages",
    label: "Nachrichten",
    icon: MessageSquare,
    navCountKey: "nav_messages",
  },
  { to: "/properties", label: "Unterkünfte", icon: Building2 },
  { to: "/support", label: "Support", icon: LifeBuoy },
  { to: "/review", label: "Review", icon: ClipboardCheck, badge: true },
  {
    to: "/ground-zero",
    label: "Ground Zero",
    icon: AlertTriangle,
    navCountKey: "nav_ground_zero",
  },
  {
    to: "/completed",
    label: "Abgeschlossen",
    icon: CheckCircle2,
    navCountKey: "nav_completed",
  },
];

const adminLinks: SidebarLink[] = [
  { to: "/admin/overview", label: "Übersicht", icon: Shield },
  { to: "/admin/accounts", label: "Mandanten", icon: Users, badge: true },
  { to: "/admin/diagnostics", label: "Diagnose", icon: Stethoscope },
  { to: "/admin/observability", label: "Observability", icon: LineChart },
  { to: "/admin/tickets", label: "Tickets", icon: Ticket },
  { to: "/admin/llm-config", label: "LLM-Konfiguration", icon: SlidersHorizontal },
  { to: "/admin/workflows", label: "Workflows", icon: GitBranch },
];

type SidebarNavProps = {
  onNavigate?: () => void;
  id?: string;
};

export function SidebarNav({ onNavigate, id = "primary-navigation" }: SidebarNavProps) {
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboardStats,
    refetchInterval: 30_000,
    enabled: !isPlatformAdmin,
  });
  const { data: pendingAccounts } = useQuery({
    queryKey: ["admin-accounts", "pending-count"],
    queryFn: fetchPendingAccounts,
    enabled: isPlatformAdmin,
    refetchInterval: 60_000,
  });
  const { data: workflowNav } = useQuery({
    queryKey: ["workflows", "nav"],
    queryFn: fetchWorkflowNav,
    enabled: !isPlatformAdmin,
    refetchInterval: 60_000,
  });
  const pending = stats?.pending_review ?? 0;
  const pendingApprovals = pendingAccounts?.total ?? 0;
  const workflowRubrics: SidebarLink[] = (workflowNav?.items ?? []).map((wf) => ({
    to: `/rubrics/${wf.slug}`,
    label: wf.label,
    icon: Tag,
  }));
  const links = isPlatformAdmin
    ? adminLinks
    : [
        ...tenantLinks.slice(0, 8),
        ...workflowRubrics,
        ...tenantLinks.slice(8),
      ];

  return (
    <nav id={id} aria-label="Hauptnavigation" className="flex-1 space-y-1 p-3">
      {links.map(({ to, label, icon: Icon, badge, navCountKey }) => {
        const navCount =
          navCountKey && stats
            ? (stats[navCountKey] as number | undefined)
            : undefined;
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
