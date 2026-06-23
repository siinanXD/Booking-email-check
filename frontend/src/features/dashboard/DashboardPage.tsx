import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  AlertTriangle,
  CalendarCheck,
  Mail,
  RefreshCw,
  XCircle,
  Info,
  CheckCircle2,
  Inbox,
  TrendingDown,
} from "lucide-react";
import { fetchDashboardStats } from "@/lib/api/dashboard";
import { fetchMailConnection, syncMailConnection } from "@/lib/api/mail";
import { StatCard } from "@/shared/components/StatCard";
import { ErrorState } from "@/shared/components/ErrorState";
import { Button } from "@/shared/ui/Button";

function formatTimestamp(value: string | number | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function DashboardPage() {
  const queryClient = useQueryClient();
  const [showSyncErrors, setShowSyncErrors] = useState(false);

  const { data: stats, isLoading, isError, refetch, dataUpdatedAt } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboardStats,
    refetchInterval: 30_000,
  });

  const { data: mailConnection } = useQuery({
    queryKey: ["mail-connection"],
    queryFn: fetchMailConnection,
  });

  const syncMut = useMutation({
    mutationFn: () => syncMailConnection(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      void queryClient.invalidateQueries({ queryKey: ["emails"] });
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["mail-connection"] });
    },
  });

  const loading = isLoading || !stats;
  const dash = "—";

  const syncErrors = [
    ...(syncMut.data?.item_errors ?? []),
    ...(syncMut.data?.reprocess_errors ?? []),
  ];
  const visibleSyncErrors = syncErrors.slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-extrabold tracking-tight text-slate-900">Übersicht</h2>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-400">
            <span>Aktualisiert: <span className="text-slate-600 font-medium">{loading ? dash : formatTimestamp(dataUpdatedAt)}</span></span>
            <span>·</span>
            <span>Sync: <span className="text-slate-600 font-medium">{formatTimestamp(stats?.last_sync_at)}</span></span>
            <span>·</span>
            <span>Letzte Mail: <span className="text-slate-600 font-medium">{formatTimestamp(stats?.last_email_received_at)}</span></span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <Button
            variant="secondary"
            onClick={() => { setShowSyncErrors(false); syncMut.mutate(); }}
            disabled={syncMut.isPending}
          >
            <RefreshCw size={15} className={syncMut.isPending ? "animate-spin" : ""} />
            Postfach synchronisieren
          </Button>
          {syncMut.data && (
            <div className="max-w-xs text-right">
              <p className={`text-xs font-medium ${syncMut.data.success ? "text-emerald-700" : "text-amber-700"}`}>
                {syncMut.data.message}
              </p>
              {syncErrors.length > 0 && (
                <button
                  type="button"
                  className="mt-1 text-xs text-indigo-600 underline hover:text-indigo-500"
                  onClick={() => setShowSyncErrors((o) => !o)}
                >
                  {showSyncErrors ? "Ausblenden" : "Fehlerdetails"}
                </button>
              )}
              {showSyncErrors && (
                <ul className="mt-1 space-y-0.5 text-left text-xs text-red-600">
                  {visibleSyncErrors.map((e) => <li key={e}>· {e}</li>)}
                </ul>
              )}
            </div>
          )}
          {syncMut.isError && (
            <p className="text-xs text-red-600">Synchronisation fehlgeschlagen.</p>
          )}
        </div>
      </div>

      {/* Notices */}
      {mailConnection?.last_error && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle size={16} className="mt-0.5 flex-shrink-0 text-amber-600" />
          <p className="text-sm text-amber-800">
            <span className="font-semibold">Postfach-Hinweis:</span> {mailConnection.last_error}
          </p>
        </div>
      )}
      {stats?.mail_fetch_unread_only && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <Info size={16} className="mt-0.5 flex-shrink-0 text-amber-600" />
          <p className="text-sm text-amber-800">Nur ungelesene Mails werden abgerufen (OUTLOOK_FETCH_UNREAD_ONLY).</p>
        </div>
      )}

      {isError && (
        <ErrorState
          message="Kennzahlen konnten nicht geladen werden."
          onRetry={() => refetch()}
        />
      )}

      {/* Primary KPIs */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">Überblick</p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Buchungs-Mails (7 Tage)"
            value={loading ? dash : stats!.booking_emails_week}
            hint={loading ? "Laden…" : `${stats!.booking_emails_total} gesamt · ${stats!.total_emails_today} heute`}
            icon={<Mail size={20} />}
            tone="indigo"
          />
          <StatCard
            title="Neue Buchungen"
            value={loading ? dash : stats!.new_bookings_today}
            icon={<CalendarCheck size={20} />}
            tone="success"
          />
          <StatCard
            title="Review ausstehend"
            value={loading ? dash : stats!.pending_review}
            highlight={!loading && stats!.pending_review > 0}
            icon={<AlertTriangle size={20} />}
          />
          <StatCard
            title="Geprüft heute"
            value={loading ? dash : stats!.reviewed_today}
            hint="freigegeben oder abgelehnt"
            icon={<CheckCircle2 size={20} />}
            tone="success"
          />
        </div>
      </div>

      {/* Secondary KPIs */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">Weitere Metriken</p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Stornos heute"
            value={loading ? dash : stats!.cancellations_today}
            icon={<XCircle size={20} />}
            tone={!loading && stats!.cancellations_today > 0 ? "danger" : "default"}
          />
          <StatCard
            title="Änderungen heute"
            value={loading ? dash : stats!.changes_today}
            icon={<RefreshCw size={20} />}
            tone="info"
          />
          <StatCard
            title="Freigegeben heute"
            value={loading ? dash : stats!.processed_today}
            icon={<Inbox size={20} />}
          />
          <StatCard
            title="Spam verworfen"
            value={loading ? dash : stats!.spam_discarded_today}
            icon={<TrendingDown size={20} />}
          />
        </div>
      </div>

      {/* Grounding */}
      {!loading && ((stats!.pending_grounding_review ?? 0) > 0 || stats!.grounding_failures_today > 0) && (
        <StatCard
          title="Grounding offen"
          value={(stats!.pending_grounding_review ?? 0) > 0 ? stats!.pending_grounding_review! : stats!.grounding_failures_today}
          hint={(stats!.pending_grounding_review ?? 0) > 0 ? `${stats!.pending_grounding_review} zum Prüfen` : `${stats!.grounding_failures_today} heute erkannt`}
          icon={<AlertTriangle size={20} />}
          highlight
          to="/ground-zero"
        />
      )}

      {/* Info banner */}
      {!loading && stats!.total_emails_week > 0 && stats!.booking_emails_total === 0 && (
        <div className="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-4">
          <Info size={16} className="mt-0.5 flex-shrink-0 text-blue-600" />
          <p className="text-sm text-blue-900">
            E-Mails eingegangen, aber keine als Buchungs-Mail erkannt. Die KI wertet Betreff und
            Inhalt aus — nach dem Sync müssen neue Mails die Pipeline durchlaufen.
          </p>
        </div>
      )}
    </div>
  );
}
