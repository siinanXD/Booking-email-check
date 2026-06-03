import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CalendarCheck,
  Mail,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { fetchCosts } from "@/lib/api/costs";
import { fetchDashboardStats } from "@/lib/api/dashboard";
import { fetchMailConnection, syncMailConnection } from "@/lib/api/mail";
import { CostChart } from "@/shared/components/CostChart";
import { StatCard } from "@/shared/components/StatCard";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildCostHint(stats: {
  cost_today_usd: number;
  cost_week_usd: number;
  avg_cost_per_mail_usd: number;
}): string {
  const parts: string[] = [`Ø 7-Tage: $${stats.avg_cost_per_mail_usd.toFixed(4)}/Mail`];
  if (stats.cost_today_usd === 0 && stats.cost_week_usd > 0) {
    parts.unshift(`Heute $0 · diese Woche $${stats.cost_week_usd.toFixed(4)}`);
  }
  return parts.join(" · ");
}

export function DashboardPage() {
  const queryClient = useQueryClient();
  const [showSyncErrors, setShowSyncErrors] = useState(false);

  const {
    data: stats,
    isLoading,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboardStats,
    refetchInterval: 30_000,
  });

  const { data: mailConnection } = useQuery({
    queryKey: ["mail-connection"],
    queryFn: fetchMailConnection,
  });

  const syncMut = useMutation({
    mutationFn: syncMailConnection,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      void queryClient.invalidateQueries({ queryKey: ["emails"] });
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["mail-connection"] });
    },
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

  const syncErrors = [
    ...(syncMut.data?.item_errors ?? []),
    ...(syncMut.data?.reprocess_errors ?? []),
  ];
  const visibleSyncErrors = syncErrors.slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Übersicht</h2>
          <p className="mt-1 text-xs text-slate-500">
            Letzte Dashboard-Aktualisierung: {formatTimestamp(new Date(dataUpdatedAt).toISOString())}
            {" · "}
            Postfach-Sync: {formatTimestamp(stats.last_sync_at)}
            {" · "}
            Letzte Mail: {formatTimestamp(stats.last_email_received_at)}
            {" · "}
            Letzte Buchungs-Mail: {formatTimestamp(stats.last_booking_detected_at)}
          </p>
          {mailConnection?.last_error && (
            <p className="mt-1 text-xs text-amber-700">
              Postfach-Hinweis: {mailConnection.last_error}
            </p>
          )}
          {stats.mail_fetch_unread_only && (
            <p className="mt-1 text-xs text-amber-700">
              Nur ungelesene Mails werden abgerufen (OUTLOOK_FETCH_UNREAD_ONLY) —
              gelesene Mails erscheinen nicht im Sync.
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button
            variant="secondary"
            className="inline-flex items-center gap-2"
            onClick={() => {
              setShowSyncErrors(false);
              syncMut.mutate();
            }}
            disabled={syncMut.isPending}
          >
            <RefreshCw
              size={16}
              className={syncMut.isPending ? "animate-spin" : ""}
            />
            Postfach synchronisieren
          </Button>
          {syncMut.data && (
            <div className="max-w-md text-right text-xs">
              <p
                className={
                  syncMut.data.success ? "text-green-700" : "text-amber-700"
                }
              >
                {syncMut.data.message}
              </p>
              {syncMut.data.duplicates > 0 && syncMut.data.processed === 0 && (
                <p className="text-slate-500">
                  Mails bereits bekannt — nur neue Mails werden verarbeitet.
                </p>
              )}
              {syncMut.data.error_count > 0 && (
                <p className="text-slate-500">
                  Keine Kosten gebucht für fehlgeschlagene Verarbeitungen.
                </p>
              )}
              {syncErrors.length > 0 && (
                <button
                  type="button"
                  className="mt-1 text-indigo-600 underline"
                  onClick={() => setShowSyncErrors((open) => !open)}
                >
                  {showSyncErrors ? "Fehler ausblenden" : "Fehlerdetails anzeigen"}
                </button>
              )}
              {showSyncErrors && visibleSyncErrors.length > 0 && (
                <ul className="mt-1 list-inside list-disc text-left text-red-700">
                  {visibleSyncErrors.map((err) => (
                    <li key={err}>{err}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {syncMut.isError && (
            <p className="text-xs text-red-600">Synchronisation fehlgeschlagen.</p>
          )}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Buchungs-Mails erkannt"
          value={stats.booking_emails_week}
          hint={`${stats.booking_emails_total} gesamt · ${stats.total_emails_week} E-Mails (7 T.) · ${stats.total_emails_today} eingegangen heute`}
          icon={<Mail size={22} />}
        />
        <StatCard
          title="Geprüft heute"
          value={stats.reviewed_today}
          hint="freigegeben oder abgelehnt"
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
        <StatCard title="Freigegeben heute" value={stats.processed_today} />
        <StatCard title="Spam verworfen" value={stats.spam_discarded_today} />
        <StatCard
          title="Kosten heute"
          value={`$${stats.cost_today_usd.toFixed(4)}`}
          hint={buildCostHint(stats)}
        />
        <StatCard
          title="Grounding-Fehler"
          value={stats.grounding_failures_today}
          icon={<AlertTriangle size={22} />}
        />
      </div>
      <Card>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-medium text-slate-800">
            API-Kosten (7 Tage)
            {costs && costs.total_usd > 0
              ? ` · Summe $${costs.total_usd.toFixed(4)}`
              : ""}
          </h3>
          <Link to="/costs" className="text-sm text-indigo-600 hover:underline">
            Details →
          </Link>
        </div>
        <CostChart series={costs?.series ?? []} />
      </Card>
    </div>
  );
}
