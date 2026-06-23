import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { fetchDashboardStats } from "@/lib/api/dashboard";
import {
  fetchGroundZeroQueue,
  fetchReviewQueue,
  type ReviewQueueTab,
} from "@/lib/api/review";
import { useReviewActions } from "@/features/review/useReviewActions";
import { ReviewActionPanel } from "@/features/review/ReviewActionPanel";
import { ReviewList } from "@/features/review/ReviewList";
import { ReviewWhatsAppCard } from "@/features/review/ReviewWhatsAppCard";
import { IntentCategoryFilter } from "@/shared/components/IntentCategoryFilter";

type ReviewTab = ReviewQueueTab | "grounding";

const TABS: { id: ReviewTab; label: string }[] = [
  { id: "pending", label: "Ausstehend" },
  { id: "released", label: "Freigegeben" },
  { id: "completed", label: "Abgeschlossen" },
  { id: "grounding", label: "Grounding" },
];

const VALID_TABS = new Set<ReviewTab>(["pending", "released", "completed", "grounding"]);

function initialTab(params: URLSearchParams): ReviewTab {
  if (params.get("grounding") === "1") return "grounding";
  const t = params.get("tab") as ReviewTab | null;
  return t && VALID_TABS.has(t) ? t : "pending";
}

export function ReviewQueuePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = initialTab(searchParams);
  const intentFilter = searchParams.get("intent") ?? "";

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

  const setTab = (next: ReviewTab) => {
    clearSelection();
    setSearchParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        p.set("tab", next);
        p.delete("grounding");
        return p;
      },
      { replace: true }
    );
  };

  const setIntentFilter = (value: string) => {
    setSearchParams(
      (prev) => {
        const p = new URLSearchParams(prev);
        if (value) p.set("intent", value);
        else p.delete("intent");
        return p;
      },
      { replace: true }
    );
  };

  const { data: queue, isLoading, isError, refetch } = useQuery({
    queryKey: ["review-queue", tab, intentFilter],
    queryFn: () =>
      tab === "grounding"
        ? fetchGroundZeroQueue(50, intentFilter || undefined)
        : fetchReviewQueue(
            tab,
            tab === "completed" ? 100 : 50,
            intentFilter || undefined
          ),
    refetchInterval: 30_000,
  });

  const { data: stats } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboardStats,
    refetchInterval: 30_000,
  });

  const tabCount = (id: ReviewTab): number | undefined => {
    if (!stats) return undefined;
    if (id === "pending") return stats.pending_review;
    if (id === "grounding") return stats.nav_ground_zero;
    if (id === "completed") return stats.nav_completed;
    return undefined;
  };

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Review</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Entwürfe prüfen, freigeben, abschließen — und offene Grounding-Fälle klären.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex max-w-full overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
          {TABS.map((t) => {
            const count = tabCount(t.id);
            return (
              <button
                key={t.id}
                type="button"
                className={`flex min-h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-4 py-1.5 text-sm font-medium transition-all duration-150 ${
                  tab === t.id
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
                {count != null && count > 0 && (
                  <span
                    className={`rounded-full px-1.5 text-[10px] font-bold ${
                      tab === t.id
                        ? "bg-white/25 text-white"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <IntentCategoryFilter value={intentFilter} onChange={setIntentFilter} />
      </div>

      {/* Split layout */}
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <ReviewList
          items={queue?.items}
          isLoading={isLoading}
          isError={isError}
          onRetry={() => refetch()}
          selectedId={selected?.correlation_id}
          onSelect={selectItem}
          emptyHint={
            tab === "grounding"
              ? "Keine Grounding-Fälle offen."
              : tab === "completed"
                ? "Noch keine abgeschlossenen Reviews."
                : "Keine Einträge in diesem Tab."
          }
        />

        <div className="space-y-4">
          <ReviewActionPanel
            tab={tab}
            selected={selected}
            draftEdit={draftEdit}
            setDraftEdit={setDraftEdit}
            rejectReason={rejectReason}
            setRejectReason={setRejectReason}
            approveMut={approveMut}
            completeMut={completeMut}
            rejectMut={rejectMut}
          />
          <ReviewWhatsAppCard correlationId={selected?.correlation_id ?? null} />
        </div>
      </div>
    </div>
  );
}
