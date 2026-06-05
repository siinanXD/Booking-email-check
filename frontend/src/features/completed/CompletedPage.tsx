import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchEmailActivity, fetchEmailDetail } from "@/lib/api/emails";
import { fetchReviewQueue } from "@/lib/api/review";
import { EmailDetailPanel } from "@/shared/components/EmailDetailPanel";
import { IntentBadge } from "@/shared/components/IntentBadge";
import { Card } from "@/shared/ui/Card";
import type { ReviewQueueItem } from "@/lib/types/api";

function formatActivityTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function CompletedPage() {
  const [selected, setSelected] = useState<ReviewQueueItem | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["review-queue", "completed"],
    queryFn: () => fetchReviewQueue("completed", 100),
    refetchInterval: 60_000,
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["email-detail", selected?.correlation_id],
    queryFn: () => fetchEmailDetail(selected!.correlation_id),
    enabled: Boolean(selected?.correlation_id),
  });

  const { data: activity, isLoading: activityLoading } = useQuery({
    queryKey: ["email-activity", selected?.correlation_id],
    queryFn: () => fetchEmailActivity(selected!.correlation_id),
    enabled: Boolean(selected?.correlation_id),
  });

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">Abgeschlossen</h2>
        <p className="mt-1 text-sm text-slate-600">
          Erledigte Reviews mit Mail-Detail und Arbeitsverlauf.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="max-h-[70vh] overflow-y-auto p-0">
          {isLoading ? (
            <p className="p-4 text-slate-500">Lade…</p>
          ) : (data?.items.length ?? 0) === 0 ? (
            <p className="p-4 text-slate-500">Noch keine abgeschlossenen Reviews.</p>
          ) : (
            <ul>
              {data!.items.map((item) => (
                <li key={item.correlation_id}>
                  <button
                    type="button"
                    className={`w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-slate-50 ${
                      selected?.correlation_id === item.correlation_id
                        ? "bg-indigo-50"
                        : ""
                    }`}
                    onClick={() => setSelected(item)}
                  >
                    <p className="text-sm font-medium">{item.subject}</p>
                    <p className="text-xs text-slate-500">{item.from_address}</p>
                    <div className="mt-1">
                      <IntentBadge intent={item.intent} />
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          {!selected ? (
            <p className="text-slate-500">Eintrag aus der Liste wählen</p>
          ) : (
            <div className="space-y-4">
              <div>
                <h3 className="font-medium">{selected.subject}</h3>
                <p className="text-sm text-slate-500">{selected.from_address}</p>
              </div>
              <EmailDetailPanel detail={detail} isLoading={detailLoading} />
              <div>
                <p className="mb-2 text-xs font-medium uppercase text-slate-500">
                  Arbeitsverlauf
                </p>
                {activityLoading ? (
                  <p className="text-sm text-slate-500">Lade Verlauf…</p>
                ) : (activity?.events.length ?? 0) === 0 ? (
                  <p className="text-sm text-slate-500">Kein Verlauf verfügbar.</p>
                ) : (
                  <ol className="space-y-2 border-l border-slate-200 pl-4">
                    {activity!.events.map((event) => (
                      <li key={`${event.kind}-${event.at}`} className="relative">
                        <span className="absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full bg-indigo-500" />
                        <p className="text-sm font-medium text-slate-800">
                          {event.label}
                        </p>
                        <p className="text-xs text-slate-500">
                          {formatActivityTime(event.at)}
                        </p>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
