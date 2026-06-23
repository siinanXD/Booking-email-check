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

export type NavCountKey =
  | "nav_bookings"
  | "nav_cancellations"
  | "nav_changes"
  | "nav_messages"
  | "nav_ground_zero"
  | "nav_completed";

export type SidebarLink = {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: boolean;
  navCountKey?: NavCountKey;
};

const tenantLinks: SidebarLink[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/bookings", label: "Buchungen", icon: CalendarCheck, navCountKey: "nav_bookings" },
  { to: "/cancellations", label: "Stornos", icon: XCircle, navCountKey: "nav_cancellations" },
  { to: "/changes", label: "Änderungen", icon: RefreshCw, navCountKey: "nav_changes" },
  { to: "/messages", label: "Nachrichten", icon: MessageSquare, navCountKey: "nav_messages" },
  { to: "/properties", label: "Unterkünfte", icon: Building2 },
  { to: "/support", label: "Support", icon: LifeBuoy },
  { to: "/review", label: "Review", icon: ClipboardCheck, badge: true },
  { to: "/ground-zero", label: "Ground Zero", icon: AlertTriangle, navCountKey: "nav_ground_zero" },
  { to: "/completed", label: "Abgeschlossen", icon: CheckCircle2, navCountKey: "nav_completed" },
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

export interface SidebarNavData {
  links: SidebarLink[];
  isPlatformAdmin: boolean;
  pending: number;
  pendingApprovals: number;
  navCountFor: (key: NavCountKey | undefined) => number | undefined;
}

/** Shared data source for the desktop sidebar and the mobile drawer. */
export function useSidebarNav(): SidebarNavData {
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

  const workflowRubrics: SidebarLink[] = (workflowNav?.items ?? []).map((wf) => ({
    to: `/rubrics/${wf.slug}`,
    label: wf.label,
    icon: Tag,
  }));
  const links = isPlatformAdmin
    ? adminLinks
    : [...tenantLinks.slice(0, 8), ...workflowRubrics, ...tenantLinks.slice(8)];

  return {
    links,
    isPlatformAdmin,
    pending: stats?.pending_review ?? 0,
    pendingApprovals: pendingAccounts?.total ?? 0,
    navCountFor: (key) =>
      key && stats ? (stats[key] as number | undefined) : undefined,
  };
}
