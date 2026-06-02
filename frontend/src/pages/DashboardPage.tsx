import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarCheck,
  Mail,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { fetchCosts } from "@/api/costs";
import { fetchDashboardStats } from "@/api/dashboard";
import { CostChart } from "@/components/shared/CostChart";
import { StatCard } from "@/components/shared/StatCard";
import { Card } from "@/components/ui/Card";

export function DashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboardStats,
  });

  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 7);

  const { data: costs } = useQuery({
    queryKey: ["costs-week"],
    queryFn: () =>
      fetchCosts(weekAgo.toISOString().slice(0, 10), undefined, "day"),
  });

  if (isLoading || !stats) {
    return <p className="text-slate-500">Lade Dashboard…</p>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-800">Übersicht</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Buchungs-Mails erkannt"
          value={stats.booking_emails_week}
          hint={`${stats.booking_emails_total} gesamt · ${stats.total_emails_week} E-Mails (7 T.)`}
          icon={<Mail size={22} />}
        />
        <StatCard
          title="Eingegangen heute"
          value={stats.total_emails_today}
          hint="alle Posteingänge"
        />
        <StatCard
          title="Review ausstehend"
          value={stats.pending_review}
          highlight={stats.pending_review > 0}
          icon={<AlertTriangle size={22} />}
        />
        <StatCard
          title="Neue Buchungen"
          value={stats.new_bookings_today}
          icon={<CalendarCheck size={22} />}
        />
        <StatCard
          title="Stornos / Änderungen"
          value={`${stats.cancellations_today} / ${stats.changes_today}`}
          icon={<XCircle size={22} />}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Verarbeitet heute" value={stats.processed_today} />
        <StatCard title="Spam verworfen" value={stats.spam_discarded_today} />
        <StatCard
          title="Kosten heute"
          value={`$${stats.cost_today_usd.toFixed(4)}`}
          hint={`Ø $${stats.avg_cost_per_mail_usd.toFixed(4)}/Mail`}
        />
        <StatCard
          title="Grounding-Fehler"
          value={stats.grounding_failures_today}
          icon={<RefreshCw size={22} />}
        />
      </div>
      <Card>
        <h3 className="mb-4 font-medium text-slate-800">API-Kosten (7 Tage)</h3>
        <CostChart series={costs?.series ?? []} />
      </Card>
    </div>
  );
}
