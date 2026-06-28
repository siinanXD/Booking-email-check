import { useQuery } from "@tanstack/react-query";
import { MessageSquare, Mail } from "lucide-react";
import { fetchAdminActivity } from "@/lib/api/admin";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { EmptyState } from "@/shared/components/EmptyState";
import { ErrorState } from "@/shared/components/ErrorState";
import { Card } from "@/shared/ui/Card";
import { intentLabel } from "@/lib/intentDisplay";
import { formatTs } from "@/lib/format";
import type { ActivityMail, ActivityNotification } from "@/lib/types/api";

const NOTIF_TONE: Record<string, string> = {
  sent: "bg-okbg text-oktext ring-border",
  failed: "bg-dangerbg text-dangertext ring-border",
  skipped: "bg-surface2 text-muted ring-border",
  pending: "bg-warnbg text-warntext ring-border",
};

const NOTIF_LABEL: Record<string, string> = {
  sent: "Gesendet",
  failed: "Fehlgeschlagen",
  skipped: "Übersprungen",
  pending: "Ausstehend",
};

const KIND_LABEL: Record<string, string> = {
  booking_cleaning_task: "Reinigung",
  booking_status_notice: "Status",
  booking_guest_inquiry: "Gastnachricht",
};

const STATE_TONE: Record<string, string> = {
  approved: "bg-okbg text-oktext ring-border",
  pending_review: "bg-brandsoft text-brandink ring-border",
  discarded: "bg-surface2 text-muted ring-border",
  rejected: "bg-dangerbg text-dangertext ring-border",
};

function StatusPill({ tone, label }: { tone: string; label: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ${tone}`}>
      {label}
    </span>
  );
}

function CountBadge({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5">
      <span className={`h-2 w-2 rounded-full ${tone}`} />
      <span className="text-sm font-semibold tabular-nums text-ink">{value}</span>
      <span className="text-xs text-muted">{label}</span>
    </div>
  );
}

function NotificationRow({ n }: { n: ActivityNotification }) {
  return (
    <tr className="border-b border-border align-top">
      <td className="py-2 pr-4 whitespace-nowrap text-muted">{formatTs(n.created_at)}</td>
      <td className="py-2 pr-4 text-ink2">{n.tenant ?? "—"}</td>
      <td className="py-2 pr-4 text-ink2">{KIND_LABEL[n.kind] ?? n.kind}</td>
      <td className="py-2 pr-4 font-mono text-xs text-muted">{n.recipient_masked}</td>
      <td className="py-2 pr-4">
        <StatusPill tone={NOTIF_TONE[n.status] ?? NOTIF_TONE.skipped} label={NOTIF_LABEL[n.status] ?? n.status} />
      </td>
      <td className="py-2 text-xs text-dangertext">{n.error ?? ""}</td>
    </tr>
  );
}

function MailRow({ m }: { m: ActivityMail }) {
  return (
    <tr className="border-b border-border align-top">
      <td className="py-2 pr-4 whitespace-nowrap text-muted">{formatTs(m.at)}</td>
      <td className="py-2 pr-4 text-ink2">{m.tenant ?? "—"}</td>
      <td className="py-2 pr-4 text-ink">{m.subject}</td>
      <td className="py-2 pr-4 text-muted">{intentLabel(m.intent)}</td>
      <td className="py-2">
        <StatusPill
          tone={STATE_TONE[m.processing_state] ?? "bg-surface2 text-muted ring-border"}
          label={m.processing_state}
        />
      </td>
    </tr>
  );
}

export function AdminActivityPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-activity"],
    queryFn: () => fetchAdminActivity(50),
    refetchInterval: 30_000,
  });

  const n24 = data?.notification_counts_24h ?? {};
  const mail24 = data?.mail_counts_24h ?? {};

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Aktivität (Live)"
        description="Sieh in Echtzeit, dass es läuft: zuletzt verarbeitete Kunden-Mails und tatsächlich versendete WhatsApp-Nachrichten — mandantenübergreifend. Aktualisiert sich automatisch alle 30 Sekunden."
        impact="Reine Beobachtung. Grüne WhatsApp-Status bedeuten erfolgreich versendet; rote zeigen Fehler mit Grund."
      />

      {isError ? (
        <ErrorState message="Aktivität konnte nicht geladen werden." onRetry={() => refetch()} />
      ) : isLoading ? (
        <p className="text-sm text-muted">Lade Aktivität…</p>
      ) : (
        <>
          {/* WhatsApp */}
          <Card className="space-y-4 overflow-x-auto">
            <div className="flex items-center gap-2">
              <MessageSquare size={18} className="text-oktext" />
              <h2 className="font-semibold text-ink">WhatsApp-Versand</h2>
              <span className="text-xs text-faint">letzte 24 h</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <CountBadge label="gesendet" value={n24.sent ?? 0} tone="bg-[var(--oktext)]" />
              <CountBadge label="fehlgeschlagen" value={n24.failed ?? 0} tone="bg-[var(--dangertext)]" />
              <CountBadge label="übersprungen" value={n24.skipped ?? 0} tone="bg-[var(--faint)]" />
            </div>
            {(data?.recent_notifications.length ?? 0) === 0 ? (
              <EmptyState bare title="Noch keine WhatsApp-Sends" message="Sobald Benachrichtigungen rausgehen, erscheinen sie hier." />
            ) : (
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted">
                    <th scope="col" className="pb-2 pr-4 font-medium">Zeit</th>
                    <th scope="col" className="pb-2 pr-4 font-medium">Mandant</th>
                    <th scope="col" className="pb-2 pr-4 font-medium">Typ</th>
                    <th scope="col" className="pb-2 pr-4 font-medium">Empfänger</th>
                    <th scope="col" className="pb-2 pr-4 font-medium">Status</th>
                    <th scope="col" className="pb-2 font-medium">Fehler</th>
                  </tr>
                </thead>
                <tbody>
                  {data!.recent_notifications.map((n) => (
                    <NotificationRow key={n.id} n={n} />
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          {/* Mail processing */}
          <Card className="space-y-4 overflow-x-auto">
            <div className="flex items-center gap-2">
              <Mail size={18} className="text-brandink" />
              <h2 className="font-semibold text-ink">Mail-Verarbeitung</h2>
              <span className="text-xs text-faint">letzte 24 h</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <CountBadge label="verarbeitet" value={mail24.total ?? 0} tone="bg-[var(--brand)]" />
              <CountBadge label="im Review" value={mail24.pending_review ?? 0} tone="bg-[var(--warntext)]" />
              <CountBadge label="freigegeben" value={mail24.approved ?? 0} tone="bg-[var(--oktext)]" />
              <CountBadge label="verworfen" value={mail24.discarded ?? 0} tone="bg-[var(--faint)]" />
            </div>
            {(data?.recent_mails.length ?? 0) === 0 ? (
              <EmptyState bare title="Noch keine verarbeiteten Mails" message="Sobald Kunden-Mails durch die Pipeline laufen, erscheinen sie hier." />
            ) : (
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted">
                    <th scope="col" className="pb-2 pr-4 font-medium">Zeit</th>
                    <th scope="col" className="pb-2 pr-4 font-medium">Mandant</th>
                    <th scope="col" className="pb-2 pr-4 font-medium">Betreff</th>
                    <th scope="col" className="pb-2 pr-4 font-medium">Intent</th>
                    <th scope="col" className="pb-2 font-medium">Zustand</th>
                  </tr>
                </thead>
                <tbody>
                  {data!.recent_mails.map((m) => (
                    <MailRow key={m.correlation_id} m={m} />
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
