import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { fetchDashboardStats } from "@/lib/api/dashboard";
import {
  bulkApprove,
  fetchGroundZeroQueue,
  fetchReviewQueue,
  type ReviewQueueTab,
} from "@/lib/api/review";
import { useReviewActions } from "@/features/review/useReviewActions";
import { useReviewShortcuts } from "@/features/review/useReviewShortcuts";
import { BulkApproveBar } from "@/features/review/BulkApproveBar";
import { ReviewActionPanel } from "@/features/review/ReviewActionPanel";
import { ReviewList } from "@/features/review/ReviewList";
import { ReviewWhatsAppCard } from "@/features/review/ReviewWhatsAppCard";
import { IntentCategoryFilter } from "@/shared/components/IntentCategoryFilter";
import { toast } from "@/shared/feedback/toastStore";

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

  const queryClient = useQueryClient();
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

  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());

  const setTab = (next: ReviewTab) => {
    clearSelection();
    setCheckedIds(new Set());
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

  const items = queue?.items;
  const selectable = tab === "pending";

  // Drop checked IDs that are no longer present in the current queue.
  useEffect(() => {
    if (!items) return;
    setCheckedIds((prev) => {
      if (prev.size === 0) return prev;
      const present = new Set(items.map((i) => i.correlation_id));
      const next = new Set([...prev].filter((id) => present.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [items]);

  const toggleCheck = (id: string) =>
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const bulkMut = useMutation({
    mutationFn: () => bulkApprove([...checkedIds]),
    onSuccess: (res) => {
      toast.success(
        res.failed > 0
          ? `${res.approved} freigegeben, ${res.failed} fehlgeschlagen.`
          : `${res.approved} freigegeben.`
      );
      setCheckedIds(new Set());
      clearSelection();
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
  });

  const selectedIndex = useMemo(() => {
    if (!items || !selected) return -1;
    return items.findIndex((i) => i.correlation_id === selected.correlation_id);
  }, [items, selected]);

  useReviewShortcuts(items, {
    onMove: (delta) => {
      if (!items || items.length === 0) return;
      const base = selectedIndex < 0 ? (delta > 0 ? -1 : 0) : selectedIndex;
      const nextIndex = Math.min(
        items.length - 1,
        Math.max(0, base + delta)
      );
      selectItem(items[nextIndex]);
    },
    onApprove: () => {
      if (selected && tab === "pending" && draftEdit.trim()) approveMut.mutate();
    },
    onEdit: () => {
      const ta = document.querySelector<HTMLTextAreaElement>(
        "textarea[data-review-draft]"
      );
      ta?.focus();
    },
    onReject: () => {
      if (selected && tab === "pending") rejectMut.mutate();
    },
  });

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-ink">Review</h2>
        <p className="mt-0.5 text-sm text-muted">
          Entwürfe prüfen, freigeben, abschließen — und offene Grounding-Fälle klären.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex max-w-full overflow-x-auto rounded-xl border border-border bg-surface p-1 shadow-card">
          {TABS.map((t) => {
            const count = tabCount(t.id);
            return (
              <button
                key={t.id}
                type="button"
                className={`flex min-h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-4 py-1.5 text-sm font-medium transition-all duration-150 ${
                  tab === t.id
                    ? "bg-brand-gradient text-white shadow-card"
                    : "text-muted hover:text-ink2"
                }`}
                onClick={() => setTab(t.id)}
              >
                {t.label}
                {count != null && count > 0 && (
                  <span
                    className={`rounded-full px-1.5 text-[10px] font-bold font-numeric ${
                      tab === t.id
                        ? "bg-white/25 text-white"
                        : "bg-surface2 text-muted"
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

      <p className="text-xs text-faint">
        Kürzel: <span className="font-numeric">J/K</span> Auswahl ·{" "}
        <span className="font-numeric">Enter</span> Freigeben ·{" "}
        <span className="font-numeric">E</span> Bearbeiten ·{" "}
        <span className="font-numeric">R</span> Ablehnen
      </p>

      {selectable && (
        <BulkApproveBar
          count={checkedIds.size}
          pending={bulkMut.isPending}
          onApprove={() => bulkMut.mutate()}
          onClear={() => setCheckedIds(new Set())}
        />
      )}

      {/* Split layout */}
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <ReviewList
          items={items}
          isLoading={isLoading}
          isError={isError}
          onRetry={() => refetch()}
          selectedId={selected?.correlation_id}
          onSelect={selectItem}
          checkedIds={selectable ? checkedIds : undefined}
          onToggleCheck={selectable ? toggleCheck : undefined}
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
