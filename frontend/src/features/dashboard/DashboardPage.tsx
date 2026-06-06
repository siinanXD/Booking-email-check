import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  AlertTriangle,
  CalendarCheck,
  Mail,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { fetchDashboardStats } from "@/lib/api/dashboard";
import { fetchMailConnection, syncMailConnection } from "@/lib/api/mail";
import { StatCard } from "@/shared/components/StatCard";
import { Button } from "@/shared/ui/Button";

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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Übersicht</h2>
          <p className="mt-1 space-y-1 text-xs text-slate-500 sm:space-y-0">
            <span className="block sm:inline">
              Letzte Dashboard-Aktualisierung:{" "}
              {loading
                ? dash
                : formatTimestamp(new Date(dataUpdatedAt).toISOString())}
            </span>
            <span className="hidden sm:inline"> · </span>
            <span className="block sm:inline">
              Postfach-Sync: {formatTimestamp(stats?.last_sync_at)}
            </span>
            <span className="hidden sm:inline"> · </span>
            <span className="block sm:inline">
              Letzte Mail: {formatTimestamp(stats?.last_email_received_at)}
            </span>
            <span className="hidden sm:inline"> · </span>
            <span className="block sm:inline">
              Letzte Buchungs-Mail:{" "}
              {formatTimestamp(stats?.last_booking_detected_at)}
            </span>
          </p>
          {mailConnection?.last_error && (
            <p className="mt-1 text-xs text-amber-700">
              Postfach-Hinweis: {mailConnection.last_error}
            </p>
          )}
          {stats?.mail_fetch_unread_only && (
            <p className="mt-1 text-xs text-amber-700">
              Nur ungelesene Mails werden abgerufen (OUTLOOK_FETCH_UNREAD_ONLY) —
              gelesene Mails erscheinen nicht im Sync.
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Button
            variant="secondary"
            className="inline-flex w-full items-center justify-center gap-2 sm:w-auto"
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
                  Einige Mails konnten nicht vollständig verarbeitet werden.
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
          value={loading ? dash : stats!.booking_emails_week}
          hint={
            loading
              ? "Statistiken werden geladen…"
              : `${stats!.booking_emails_total} gesamt · ${stats!.total_emails_week} E-Mails (7 T.) · ${stats!.total_emails_today} eingegangen heute`
          }
          icon={<Mail size={22} />}
        />
        <StatCard
          title="Geprüft heute"
          value={loading ? dash : stats!.reviewed_today}
          hint="freigegeben oder abgelehnt"
        />
        <StatCard
          title="Review ausstehend"
          value={loading ? dash : stats!.pending_review}
          highlight={!loading && stats!.pending_review > 0}
          icon={<AlertTriangle size={22} />}
        />
        <StatCard
          title="Neue Buchungen"
          value={loading ? dash : stats!.new_bookings_today}
          icon={<CalendarCheck size={22} />}
        />
        <StatCard
          title="Stornos / Änderungen"
          value={
            loading
              ? dash
              : `${stats!.cancellations_today} / ${stats!.changes_today}`
          }
          icon={<XCircle size={22} />}
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Freigegeben heute"
          value={loading ? dash : stats!.processed_today}
        />
        <StatCard
          title="Spam verworfen"
          value={loading ? dash : stats!.spam_discarded_today}
        />
        <StatCard
          title="Grounding offen"
          value={
            loading
              ? dash
              : (stats!.pending_grounding_review ?? 0) > 0
                ? stats!.pending_grounding_review!
                : stats!.grounding_failures_today
          }
          hint={
            loading
              ? undefined
              : (stats!.pending_grounding_review ?? 0) > 0
                ? `${stats!.pending_grounding_review} zum Prüfen · Klicken`
                : stats!.grounding_failures_today > 0
                  ? `${stats!.grounding_failures_today} heute erkannt`
                  : "Keine offenen Prüfhinweise"
          }
          icon={<AlertTriangle size={22} />}
          highlight={
            !loading &&
            ((stats!.pending_grounding_review ?? 0) > 0 ||
              stats!.grounding_failures_today > 0)
          }
          to={
            !loading &&
            ((stats!.pending_grounding_review ?? 0) > 0 ||
              stats!.grounding_failures_today > 0)
              ? "/ground-zero"
              : undefined
          }
        />
      </div>
      {!loading &&
        stats!.total_emails_week > 0 &&
        stats!.booking_emails_total === 0 && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Es sind E-Mails eingegangen, aber keine als Buchungs-Mail erkannt. Die KI
          wertet Betreff und Inhalt aus (auch informelle Anfragen wie „ich möchte
          buchen“). Nach dem Sync müssen neue Mails die Pipeline durchlaufen — bei nur
          Duplikaten erneut mit „Postfach synchronisieren“ und ggf. ?reprocess=1.
        </p>
      )}
    </div>
  );
}
