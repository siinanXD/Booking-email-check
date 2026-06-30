import { useQuery } from "@tanstack/react-query";
import { fetchAccountCleaning } from "@/lib/api/adminCleaning";
import { toneFor } from "@/features/cleaning/cleaningStatus";
import { Badge } from "@/shared/ui/Badge";
import { Card } from "@/shared/ui/Card";

function fmt(value?: string | null): string {
  if (!value) return "—";
  const [y, m, d] = value.slice(0, 10).split("-");
  return d ? `${d}.${m}.${y}` : value;
}

export function AdminCleaningDiagnosticsCard({
  accountId,
}: {
  accountId: string;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-cleaning", accountId],
    queryFn: () => fetchAccountCleaning(accountId),
    enabled: Boolean(accountId),
  });

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-medium text-slate-900">Putzplan</h2>
      {isLoading && <p className="text-sm text-slate-500">Lade Putzplan…</p>}
      {data && !data.enabled && (
        <p className="text-sm text-slate-500">
          Putzplan für diesen Mandanten nicht aktiviert.
        </p>
      )}
      {data && data.enabled && (
        <>
          <p className="text-sm text-slate-600">
            {data.partners.length} Putzpartner · {data.tasks.length} Aufträge
            {data.partners.length === 0 && (
              <span className="text-amber-700">
                {" "}
                · kein Partner hinterlegt
              </span>
            )}
          </p>
          {data.tasks.length === 0 ? (
            <p className="text-sm text-slate-500">Noch keine Putzaufträge.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.tasks.slice(0, 25).map((t) => (
                <li
                  key={t.task_id}
                  className="flex flex-wrap items-center justify-between gap-2 py-2"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-800">
                      {t.property_name ?? "—"}
                      {t.room_number ? ` · Zimmer ${t.room_number}` : ""}
                    </p>
                    <p className="text-xs text-slate-500">
                      Putztermin {fmt(t.cleaning_date)} · Gast{" "}
                      {t.guest_name ?? "—"}
                      {t.partner_name ? ` · ${t.partner_name}` : ""}
                      {t.last_notification_status
                        ? ` · WhatsApp: ${t.last_notification_status}`
                        : ""}
                    </p>
                  </div>
                  <Badge
                    label={t.status_label}
                    tone={toneFor(t.status)}
                    dot
                  />
                </li>
              ))}
            </ul>
          )}
          {data.tasks.length > 25 && (
            <p className="text-xs text-slate-400">
              … {data.tasks.length - 25} weitere
            </p>
          )}
        </>
      )}
    </Card>
  );
}
