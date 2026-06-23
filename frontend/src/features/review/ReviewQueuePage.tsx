import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle, Inbox, ChevronRight } from "lucide-react";
import { fetchEmailDetail } from "@/lib/api/emails";
import { fetchReviewQueue, type ReviewQueueTab } from "@/lib/api/review";
import { useReviewActions } from "@/features/review/useReviewActions";
import { ReviewWhatsAppCard } from "@/features/review/ReviewWhatsAppCard";
import { EmailDetailPanel } from "@/shared/components/EmailDetailPanel";
import { ErrorState } from "@/shared/components/ErrorState";
import { IntentCategoryFilter } from "@/shared/components/IntentCategoryFilter";
import { IntentBadge } from "@/shared/components/IntentBadge";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";

const TABS: { id: ReviewQueueTab; label: string }[] = [
  { id: "pending", label: "Ausstehend" },
  { id: "released", label: "Freigegeben" },
];

function QueueSkeleton() {
  return (
    <div className="space-y-0.5 p-2">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="rounded-lg p-3 animate-pulse">
          <div className="h-3.5 w-3/4 rounded bg-slate-100" />
          <div className="mt-2 h-3 w-1/2 rounded bg-slate-100" />
          <div className="mt-2 h-5 w-20 rounded-full bg-slate-100" />
        </div>
      ))}
    </div>
  );
}

export function ReviewQueuePage() {
  const [searchParams] = useSearchParams();
  const redirectGrounding = searchParams.get("grounding") === "1";
  const [tab, setTab] = useState<ReviewQueueTab>("pending");
  const [intentFilter, setIntentFilter] = useState("");
  const {
    selected,
    draftEdit,
    setDraftEdit,
    rejectReason,
    setRejectReason,
    approveMut,
    completeMut,
    rejectMut,
    selectItem,
    clearSelection,
  } = useReviewActions("review-queue");

  const { data: queue, isLoading, isError, refetch } = useQuery({
    queryKey: ["review-queue", tab, intentFilter],
    queryFn: () => fetchReviewQueue(tab, 50, intentFilter || undefined),
    refetchInterval: 30_000,
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["email-detail", selected?.correlation_id],
    queryFn: () => fetchEmailDetail(selected!.correlation_id),
    enabled: Boolean(selected?.correlation_id),
  });

  if (redirectGrounding) {
    return <Navigate to="/ground-zero" replace />;
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Review-Warteschlange</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Entwurf prüfen, freigeben und optional abschließen.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all duration-150 ${
                tab === t.id
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              onClick={() => { setTab(t.id); clearSelection(); }}
            >
              {t.label}
            </button>
          ))}
        </div>
        <IntentCategoryFilter value={intentFilter} onChange={setIntentFilter} />
      </div>

      {/* Split layout */}
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        {/* Queue list */}
        <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-card">
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              {queue?.items.length ?? 0} Einträge
            </p>
          </div>
          <div className="max-h-[65vh] overflow-y-auto">
            {isLoading ? (
              <QueueSkeleton />
            ) : isError ? (
              <ErrorState
                className="m-4"
                message="Warteschlange konnte nicht geladen werden."
                onRetry={() => refetch()}
              />
            ) : (queue?.items.length ?? 0) === 0 ? (
              <div className="flex flex-col items-center gap-3 py-14 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                  <Inbox size={20} />
                </div>
                <p className="text-sm text-slate-500">Keine Einträge in diesem Tab.</p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {queue!.items.map((item) => (
                  <li key={item.correlation_id}>
                    <button
                      type="button"
                      className={`group w-full px-4 py-3.5 text-left transition-colors ${
                        selected?.correlation_id === item.correlation_id
                          ? "bg-indigo-50"
                          : "hover:bg-slate-50"
                      }`}
                      onClick={() => selectItem(item)}
                    >
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-semibold text-slate-900">
                            {item.subject}
                          </p>
                          <p className="mt-0.5 truncate text-xs text-slate-500">
                            {item.from_address}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            <IntentBadge intent={item.intent} />
                            {item.grounding_flag && (
                              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 ring-1 ring-amber-200/80">
                                Grounding
                              </span>
                            )}
                            {item.review_status === "approved" && (
                              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 ring-1 ring-emerald-200/80">
                                Freigegeben
                              </span>
                            )}
                          </div>
                        </div>
                        <ChevronRight
                          size={15}
                          className={`mt-0.5 flex-shrink-0 transition-colors ${
                            selected?.correlation_id === item.correlation_id
                              ? "text-indigo-500"
                              : "text-slate-300 group-hover:text-slate-400"
                          }`}
                        />
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Detail panel */}
        <div className="space-y-4">
          <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-card">
            {!selected ? (
              <div className="flex flex-col items-center gap-3 py-16 text-center">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                  <ChevronRight size={20} />
                </div>
                <p className="text-sm text-slate-500">Eintrag aus der Liste wählen</p>
              </div>
            ) : (
              <div className="space-y-4 p-5">
                <div className="border-b border-slate-100 pb-4">
                  <h3 className="font-semibold text-slate-900">{selected.subject}</h3>
                  <p className="mt-0.5 text-sm text-slate-500">{selected.from_address}</p>
                </div>

                <EmailDetailPanel detail={detail} isLoading={detailLoading} />

                {tab === "pending" && (
                  <>
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-1">
                      <p className="mb-2 px-2 pt-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                        E-Mail-Antwort an Gast (bearbeitbar)
                      </p>
                      <textarea
                        className="h-40 w-full resize-none rounded-lg border border-transparent bg-white px-3 py-2 text-sm text-slate-800 shadow-sm outline-none transition focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100"
                        value={draftEdit}
                        onChange={(e) => setDraftEdit(e.target.value)}
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => approveMut.mutate()}
                        loading={approveMut.isPending}
                        disabled={!draftEdit.trim()}
                      >
                        <CheckCircle2 size={15} />
                        Freigeben
                      </Button>
                    </div>
                    <div className="rounded-xl border border-red-100 bg-red-50/50 p-4 space-y-3">
                      <p className="text-xs font-semibold text-red-700">Ablehnen</p>
                      <Input
                        placeholder="Ablehnungsgrund (optional)"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                      />
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => rejectMut.mutate()}
                        loading={rejectMut.isPending}
                      >
                        <XCircle size={14} />
                        Ablehnen
                      </Button>
                    </div>
                  </>
                )}

                {tab === "released" && (
                  <Button
                    onClick={() => completeMut.mutate()}
                    loading={completeMut.isPending}
                  >
                    <CheckCircle2 size={15} />
                    Als abgeschlossen markieren
                  </Button>
                )}
              </div>
            )}
          </div>
          <ReviewWhatsAppCard correlationId={selected?.correlation_id ?? null} />
        </div>
      </div>
    </div>
  );
}
