import { ChevronRight } from "lucide-react";
import { EmptyState } from "@/shared/components/EmptyState";
import { ErrorState } from "@/shared/components/ErrorState";
import { IntentBadge } from "@/shared/components/IntentBadge";
import type { ReviewQueueItem } from "@/lib/types/api";

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

type Props = {
  items: ReviewQueueItem[] | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  selectedId: string | undefined;
  onSelect: (item: ReviewQueueItem) => void;
  emptyHint?: string;
};

/** Shared selectable list for all review tabs (pending, released, completed, grounding). */
export function ReviewList({
  items,
  isLoading,
  isError,
  onRetry,
  selectedId,
  onSelect,
  emptyHint = "Keine Einträge in diesem Tab.",
}: Props) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-card">
      <div className="border-b border-slate-100 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {items?.length ?? 0} Einträge
        </p>
      </div>
      <div className="max-h-[65vh] overflow-y-auto">
        {isLoading ? (
          <QueueSkeleton />
        ) : isError ? (
          <ErrorState
            className="m-4"
            message="Liste konnte nicht geladen werden."
            onRetry={onRetry}
          />
        ) : (items?.length ?? 0) === 0 ? (
          <EmptyState bare title={emptyHint} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {items!.map((item) => (
              <li key={item.correlation_id}>
                <button
                  type="button"
                  className={`group w-full px-4 py-3.5 text-left transition-colors ${
                    selectedId === item.correlation_id
                      ? "bg-indigo-50"
                      : "hover:bg-slate-50"
                  }`}
                  onClick={() => onSelect(item)}
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
                        selectedId === item.correlation_id
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
  );
}
