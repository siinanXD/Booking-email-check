import { useQuery } from "@tanstack/react-query";
import { fetchAdminAuditLog } from "@/lib/api/admin";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { EmptyState } from "@/shared/components/EmptyState";
import { ErrorState } from "@/shared/components/ErrorState";
import { Card } from "@/shared/ui/Card";
import { formatTs } from "@/lib/format";

const ACTION_LABELS: Record<string, string> = {
  "account.approve": "Mandant freigeschaltet",
  "account.reject": "Mandant abgelehnt",
  "account.suspend": "Mandant gesperrt",
  "account.unsuspend": "Mandant entsperrt",
  "account.expiry": "Ablaufdatum geändert",
  "account.delete": "Mandant gelöscht",
  "user.lock": "Benutzer gesperrt/entsperrt",
  "user.reset_password": "Passwort zurückgesetzt",
  "user.delete": "Benutzer gelöscht",
};

function actionLabel(action: string): string {
  return ACTION_LABELS[action] ?? action;
}

function formatDetails(details: Record<string, unknown>): string {
  const entries = Object.entries(details).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );
  if (entries.length === 0) return "—";
  return entries.map(([k, v]) => `${k}: ${String(v)}`).join(" · ");
}

export function AdminAuditPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-audit-log"],
    queryFn: () => fetchAdminAuditLog(200),
    refetchInterval: 60_000,
  });

  const items = data?.items ?? [];

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Audit-Log"
        description="Protokoll der Plattform-Admin-Aktionen: Freischaltungen, Sperren, Ablaufdaten, Löschungen sowie Benutzer- und LLM-Änderungen — mit Zeitpunkt und handelndem Admin."
        impact="Reine Lese-Ansicht zur Nachvollziehbarkeit. Es werden keine Aktionen ausgelöst."
      />

      <Card className="overflow-x-auto">
        {isLoading ? (
          <p className="text-sm text-muted">Lade Audit-Log…</p>
        ) : isError ? (
          <ErrorState
            message="Audit-Log konnte nicht geladen werden."
            onRetry={() => refetch()}
          />
        ) : items.length === 0 ? (
          <EmptyState
            bare
            title="Noch keine Einträge"
            message="Sobald Admin-Aktionen ausgeführt werden, erscheinen sie hier."
          />
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-muted">
                <th scope="col" className="pb-2 pr-4 font-medium">Zeitpunkt</th>
                <th scope="col" className="pb-2 pr-4 font-medium">Aktion</th>
                <th scope="col" className="pb-2 pr-4 font-medium">Admin</th>
                <th scope="col" className="pb-2 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {items.map((entry) => (
                <tr key={entry.id} className="border-b border-border align-top">
                  <td className="py-2 pr-4 text-muted whitespace-nowrap">
                    {formatTs(entry.created_at)}
                  </td>
                  <td className="py-2 pr-4 font-medium text-ink">
                    {actionLabel(entry.action)}
                  </td>
                  <td className="py-2 pr-4 text-xs text-muted">
                    {entry.user_id ?? "—"}
                  </td>
                  <td className="py-2 text-xs text-muted">
                    {formatDetails(entry.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
