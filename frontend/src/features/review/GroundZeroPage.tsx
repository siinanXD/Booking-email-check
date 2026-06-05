import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { fetchEmailDetail } from "@/lib/api/emails";
import {
  approveReview,
  completeReview,
  fetchGroundZeroQueue,
  rejectReview,
} from "@/lib/api/review";
import { ReviewWhatsAppCard } from "@/features/review/ReviewWhatsAppCard";
import { EmailDetailPanel } from "@/shared/components/EmailDetailPanel";
import { IntentCategoryFilter } from "@/shared/components/IntentCategoryFilter";
import { IntentBadge } from "@/shared/components/IntentBadge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";
import type { ReviewQueueItem } from "@/lib/types/api";

export function GroundZeroPage() {
  const [intentFilter, setIntentFilter] = useState("");
  const [selected, setSelected] = useState<ReviewQueueItem | null>(null);
  const [draftEdit, setDraftEdit] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const queryClient = useQueryClient();

  const { data: queue, isLoading } = useQuery({
    queryKey: ["review-ground-zero", intentFilter],
    queryFn: () => fetchGroundZeroQueue(50, intentFilter || undefined),
    refetchInterval: 30_000,
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["email-detail", selected?.correlation_id],
    queryFn: () => fetchEmailDetail(selected!.correlation_id),
    enabled: Boolean(selected?.correlation_id),
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["review-ground-zero"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const approveMut = useMutation({
    mutationFn: () =>
      approveReview(selected!.correlation_id, draftEdit || undefined),
    onSuccess: () => {
      setSelected(null);
      setDraftEdit("");
      invalidate();
    },
  });

  const completeMut = useMutation({
    mutationFn: () => completeReview(selected!.correlation_id),
    onSuccess: () => {
      setSelected(null);
      invalidate();
    },
  });

  const rejectMut = useMutation({
    mutationFn: () => rejectReview(selected!.correlation_id, rejectReason),
    onSuccess: () => {
      setSelected(null);
      setRejectReason("");
      invalidate();
    },
  });

  function selectItem(item: ReviewQueueItem) {
    setSelected(item);
    setDraftEdit(item.draft_body);
    setRejectReason("");
  }

  const isPending = selected?.review_status === "pending";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">Ground Zero</h2>
        <p className="mt-1 text-sm text-slate-600">
          Grounding prüfen — offene Fälle mit Hinweis zu Buchungsnr., Gast oder
          Datum. Nach Freigabe lernt die KI aus dem Fall.
        </p>
      </div>
      <IntentCategoryFilter value={intentFilter} onChange={setIntentFilter} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="max-h-[70vh] overflow-y-auto p-0">
          {isLoading ? (
            <p className="p-4 text-slate-500">Lade…</p>
          ) : (queue?.items.length ?? 0) === 0 ? (
            <p className="p-4 text-slate-500">Keine Grounding-Fälle offen.</p>
          ) : (
            <ul>
              {queue!.items.map((item) => (
                <li key={item.correlation_id}>
                  <button
                    type="button"
                    className={`w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-slate-50 ${
                      selected?.correlation_id === item.correlation_id
                        ? "bg-indigo-50"
                        : ""
                    }`}
                    onClick={() => selectItem(item)}
                  >
                    <p className="text-sm font-medium">{item.subject}</p>
                    <p className="text-xs text-slate-500">{item.from_address}</p>
                    <div className="mt-1 flex gap-2">
                      <IntentBadge intent={item.intent} />
                      <span className="text-xs text-amber-600">Grounding</span>
                      {item.review_status === "approved" && (
                        <span className="text-xs text-green-700">Freigegeben</span>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-4">
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
                {isPending && (
                  <>
                    <div>
                      <p className="mb-1 text-xs font-medium uppercase text-slate-500">
                        E-Mail-Antwort an Gast (bearbeitbar)
                      </p>
                      <textarea
                        className="h-40 w-full rounded-lg border border-slate-300 p-3 text-sm"
                        value={draftEdit}
                        onChange={(e) => setDraftEdit(e.target.value)}
                      />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        onClick={() => approveMut.mutate()}
                        disabled={approveMut.isPending || !draftEdit.trim()}
                      >
                        Freigeben
                      </Button>
                    </div>
                    <div className="border-t pt-4">
                      <Input
                        placeholder="Ablehnungsgrund (optional)"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                      />
                      <Button
                        variant="danger"
                        className="mt-2"
                        onClick={() => rejectMut.mutate()}
                        disabled={rejectMut.isPending}
                      >
                        Ablehnen
                      </Button>
                    </div>
                  </>
                )}
                {!isPending && (
                  <Button
                    onClick={() => completeMut.mutate()}
                    disabled={completeMut.isPending}
                  >
                    Als abgeschlossen markieren
                  </Button>
                )}
              </div>
            )}
          </Card>
          <ReviewWhatsAppCard correlationId={selected?.correlation_id ?? null} />
        </div>
      </div>
    </div>
  );
}
