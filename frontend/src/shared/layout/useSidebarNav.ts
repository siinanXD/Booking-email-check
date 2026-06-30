import {
  LayoutDashboard,
  Inbox,
  ClipboardCheck,
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
  ScrollText,
  Activity,
  Workflow,
  Sparkles,
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
  | "nav_completed"
  | "nav_cleaning_tasks";

export type SidebarLink = {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: boolean;
  navCountKey?: NavCountKey;
};

const tenantLinks: SidebarLink[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/inbox", label: "Posteingang", icon: Inbox },
  { to: "/properties", label: "Unterkünfte", icon: Building2 },
  { to: "/support", label: "Support", icon: LifeBuoy },
  { to: "/review", label: "Review", icon: ClipboardCheck, badge: true },
];

const adminLinks: SidebarLink[] = [
  { to: "/admin/overview", label: "Übersicht", icon: Shield },
  { to: "/admin/activity", label: "Aktivität", icon: Activity },
  { to: "/admin/pipeline", label: "Datenfluss", icon: Workflow },
  { to: "/admin/accounts", label: "Mandanten", icon: Users, badge: true },
  { to: "/admin/audit", label: "Audit-Log", icon: ScrollText },
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
  const cleaningEnabled = useAuthStore(
    (s) => Boolean(s.user?.features?.cleaning_schedule)
  );
  const cleaningLinks: SidebarLink[] = cleaningEnabled
    ? [
        {
          to: "/cleaning",
          label: "Putzplan",
          icon: Sparkles,
          navCountKey: "nav_cleaning_tasks",
        },
      ]
    : [];
  const links = isPlatformAdmin
    ? adminLinks
    : [...tenantLinks, ...cleaningLinks, ...workflowRubrics];

  return {
    links,
    isPlatformAdmin,
    pending: stats?.pending_review ?? 0,
    pendingApprovals: pendingAccounts?.total ?? 0,
    navCountFor: (key) =>
      key && stats ? (stats[key] as number | undefined) : undefined,
  };
}
