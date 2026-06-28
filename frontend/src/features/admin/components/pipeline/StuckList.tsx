import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle } from "lucide-react";
import { fetchAdminStuckMails } from "@/lib/api/admin";
import { Card } from "@/shared/ui/Card";
import { Badge } from "@/shared/ui/Badge";
import { EmptyState } from "@/shared/components/EmptyState";
import { ErrorState } from "@/shared/components/ErrorState";
import { MailTraceModal } from "./MailTraceModal";
import type { AdminStuckItem } from "@/lib/types/api";

type Kind = "processing" | "discarded";

const HOURS_OPTIONS = [6, 24, 72] as const;

const KIND_TABS: { value: Kind; label: string }[] = [
  { value: "processing", label: "Verarbeitung" },
  { value: "discarded", label: "Verworfen" },
];

interface Selected {
  accountId: string;
  correlationId: string;
}

function StuckRow({
  item,
  kind,
  onOpen,
}: {
  item: AdminStuckItem;
  kind: Kind;
  onOpen: (s: Selected) => void;
}) {
  const clickable = !!item.account_id;
  return (
    <tr
      className={`border-b border-border align-top ${
        clickable ? "cursor-pointer hover:bg-app" : ""
      }`}
      onClick={() =>
        clickable &&
        onOpen({
          accountId: item.account_id!,
          correlationId: item.correlation_id,
        })
      }
    >
      <td className="py-2 pr-4 text-ink">{item.subject || "—"}</td>
      <td className="py-2 pr-4 text-ink2">{item.tenant ?? "—"}</td>
      <td className="py-2 pr-4">
        <Badge tone={item.processing_state} label={item.processing_state} />
      </td>
      <td className="py-2 pr-4 whitespace-nowrap font-numeric tabular-nums text-muted">
        {Math.round(item.age_hours)} h
      </td>
      {kind === "discarded" && (
        <td className="py-2 text-xs text-muted">{item.reason ?? "—"}</td>
      )}
    </tr>
  );
}

export function StuckList() {
  const [kind, setKind] = useState<Kind>("processing");
  const [hours, setHours] = useState<number>(24);
  const [selected, setSelected] = useState<Selected | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["admin-stuck", hours, kind],
    queryFn: () => fetchAdminStuckMails(hours, kind),
  });

  const items = data?.items ?? [];

  return (
    <Card className="space-y-4 overflow-x-auto">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertCircle size={18} className="text-warntext" />
          <h2 className="font-semibold text-ink">Hängengebliebene Mails</h2>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1">
            {KIND_TABS.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setKind(t.value)}
                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                  kind === t.value
                    ? "bg-brand text-brandink"
                    : "bg-app text-muted hover:text-ink2"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          {kind === "processing" && (
            <div className="flex gap-1">
              {HOURS_OPTIONS.map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setHours(h)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition-colors ${
                    hours === h
                      ? "bg-brandsoft text-brandink"
                      : "bg-app text-muted hover:text-ink2"
                  }`}
                >
                  {h} h
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {isError ? (
        <ErrorState
          message="Liste konnte nicht geladen werden."
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <p className="text-sm text-muted">Lade Liste…</p>
      ) : items.length === 0 ? (
        <EmptyState
          bare
          title="Nichts hängt fest"
          message={
            kind === "processing"
              ? "Keine Mails stecken aktuell in der Verarbeitung fest."
              : "Keine verworfenen Mails im Zeitraum."
          }
        />
      ) : (
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-muted">
              <th scope="col" className="pb-2 pr-4 font-medium">Betreff</th>
              <th scope="col" className="pb-2 pr-4 font-medium">Mandant</th>
              <th scope="col" className="pb-2 pr-4 font-medium">Status</th>
              <th scope="col" className="pb-2 pr-4 font-medium">Alter</th>
              {kind === "discarded" && (
                <th scope="col" className="pb-2 font-medium">Grund</th>
              )}
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <StuckRow
                key={item.correlation_id}
                item={item}
                kind={kind}
                onOpen={setSelected}
              />
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <MailTraceModal
          accountId={selected.accountId}
          correlationId={selected.correlationId}
          onClose={() => setSelected(null)}
        />
      )}
    </Card>
  );
}
