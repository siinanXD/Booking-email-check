import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, XCircle, ChevronRight, Loader2, Undo2 } from "lucide-react";
import type { UseMutationResult } from "@tanstack/react-query";
import { fetchEmailActivity, fetchEmailDetail } from "@/lib/api/emails";
import { translateDraft, undoAutoApproval } from "@/lib/api/review";
import { EmailDetailPanel } from "@/shared/components/EmailDetailPanel";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";
import { toast } from "@/shared/feedback/toastStore";
import type { ReviewQueueItem } from "@/lib/types/api";
import type { ReviewQueueTab } from "@/lib/api/review";

type ReplyLang = "de" | "en";

function formatActivityTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type Mut = UseMutationResult<void, Error, void, unknown>;

type ReviewTab = ReviewQueueTab | "grounding";

type Props = {
  tab: ReviewTab;
  selected: ReviewQueueItem | null;
  draftEdit: string;
  setDraftEdit: (v: string) => void;
  rejectReason: string;
  setRejectReason: (v: string) => void;
  approveMut: Mut;
  completeMut: Mut;
  rejectMut: Mut;
};

/** Detail + tab-aware actions for one selected review item. */
export function ReviewActionPanel({
  tab,
  selected,
  draftEdit,
  setDraftEdit,
  rejectReason,
  setRejectReason,
  approveMut,
  completeMut,
  rejectMut,
}: Props) {
  const correlationId = selected?.correlation_id ?? null;
  const queryClient = useQueryClient();

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ["email-detail", correlationId],
    queryFn: () => fetchEmailDetail(correlationId!),
    enabled: Boolean(correlationId),
  });

  const [lang, setLang] = useState<ReplyLang>("de");

  // Initialise the language toggle from the detected reply language.
  useEffect(() => {
    setLang(detail?.reply_language ?? "de");
  }, [detail?.reply_language, correlationId]);

  const translateMut = useMutation({
    mutationFn: (target: ReplyLang) =>
      translateDraft(correlationId!, target, draftEdit),
    meta: { skipGlobalError: true },
    onSuccess: (res) => {
      setDraftEdit(res.translated_body);
      setLang(res.target_language === "en" ? "en" : "de");
    },
    onError: () => toast.error("Übersetzung fehlgeschlagen."),
  });

  const undoMut = useMutation({
    mutationFn: () => undoAutoApproval(correlationId!),
    meta: { skipGlobalError: true },
    onSuccess: () => {
      toast.success("Auto-Freigabe rückgängig gemacht");
      void queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    },
    onError: () =>
      toast.error("Rückgängig nicht möglich (Zeitfenster abgelaufen)."),
  });

  const switchLang = (target: ReplyLang) => {
    if (target === lang || !correlationId || translateMut.isPending) return;
    translateMut.mutate(target);
  };

  const { data: activity, isLoading: activityLoading } = useQuery({
    queryKey: ["email-activity", correlationId],
    queryFn: () => fetchEmailActivity(correlationId!),
    enabled: Boolean(correlationId) && tab === "completed",
  });

  if (!selected) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-border/80 bg-surface py-16 text-center shadow-card">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface2 text-faint">
          <ChevronRight size={20} />
        </div>
        <p className="text-sm text-muted">Eintrag aus der Liste wählen</p>
      </div>
    );
  }

  const isGroundingPending =
    tab === "grounding" && selected.review_status === "pending";
  const canApprove = tab === "pending" || isGroundingPending;
  const canComplete =
    tab === "released" ||
    (tab === "grounding" && selected.review_status === "approved");
  const isReadOnly = tab === "completed";

  return (
    <div className="overflow-hidden rounded-xl border border-border/80 bg-surface shadow-card">
      <div className="space-y-4 p-5">
        <div className="border-b border-border pb-4">
          <h3 className="font-semibold text-ink">{selected.subject}</h3>
          <p className="mt-0.5 text-sm text-muted">{selected.from_address}</p>
        </div>

        <EmailDetailPanel
          detail={detail}
          isLoading={detailLoading}
          showFullBody={isReadOnly}
        />

        {detail?.auto_approved && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => undoMut.mutate()}
            loading={undoMut.isPending}
          >
            <Undo2 size={14} />
            Rückgängig
          </Button>
        )}

        {canApprove && (
          <>
            <div className="flex items-center gap-2">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-faint">
                Sprache
              </p>
              <div className="inline-flex items-center rounded-lg border border-border bg-surface2 p-0.5">
                {(["de", "en"] as ReplyLang[]).map((l) => (
                  <button
                    key={l}
                    type="button"
                    onClick={() => switchLang(l)}
                    disabled={translateMut.isPending}
                    className={`rounded-md px-2.5 py-1 text-xs font-semibold uppercase transition ${
                      lang === l
                        ? "bg-surface text-brandink shadow-sm"
                        : "text-faint hover:text-ink2"
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>
              {translateMut.isPending && (
                <Loader2 size={14} className="animate-spin text-faint" />
              )}
            </div>
            <div className="rounded-xl border border-border bg-surface2 p-1">
              <p className="mb-2 px-2 pt-1 text-[10px] font-semibold uppercase tracking-wide text-faint">
                E-Mail-Antwort an Gast (bearbeitbar)
              </p>
              <textarea
                data-review-draft
                className="h-40 w-full resize-none rounded-lg border border-transparent bg-surface px-3 py-2 text-sm text-ink shadow-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
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
            <div className="space-y-3 rounded-xl border border-red-100 bg-dangerbg/50 p-4">
              <p className="text-xs font-semibold text-dangertext">Ablehnen</p>
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

        {canComplete && (
          <Button
            onClick={() => completeMut.mutate()}
            loading={completeMut.isPending}
          >
            <CheckCircle2 size={15} />
            Als abgeschlossen markieren
          </Button>
        )}

        {isReadOnly && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase text-muted">
              Arbeitsverlauf
            </p>
            {activityLoading ? (
              <p className="text-sm text-muted">Lade Verlauf…</p>
            ) : (activity?.events.length ?? 0) === 0 ? (
              <p className="text-sm text-muted">Kein Verlauf verfügbar.</p>
            ) : (
              <ol className="space-y-2 border-l border-border pl-4">
                {activity!.events.map((event) => (
                  <li key={`${event.kind}-${event.at}`} className="relative">
                    <span className="absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full bg-brand" />
                    <p className="text-sm font-medium text-ink">
                      {event.label}
                    </p>
                    <p className="text-xs text-muted">
                      {formatActivityTime(event.at)}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
