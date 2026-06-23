import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { approveReview, completeReview, rejectReview } from "@/lib/api/review";
import { toast } from "@/shared/feedback/toastStore";
import type { ReviewQueueItem } from "@/lib/types/api";

/**
 * Shared review-action logic for the Review queue and Ground Zero pages.
 * `listQueryKey` is the root key of the list to invalidate after each action.
 */
export function useReviewActions(listQueryKey: string) {
  const [selected, setSelected] = useState<ReviewQueueItem | null>(null);
  const [draftEdit, setDraftEdit] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const qc = useQueryClient();

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: [listQueryKey] });
    void qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
  };

  const clearSelection = () => {
    setSelected(null);
    setDraftEdit("");
    setRejectReason("");
  };

  const approveMut = useMutation({
    mutationFn: () =>
      approveReview(selected!.correlation_id, draftEdit || undefined),
    onSuccess: () => {
      toast.success("Entwurf freigegeben.");
      clearSelection();
      invalidate();
    },
  });

  const completeMut = useMutation({
    mutationFn: () => completeReview(selected!.correlation_id),
    onSuccess: () => {
      toast.success("Als abgeschlossen markiert.");
      clearSelection();
      invalidate();
    },
  });

  const rejectMut = useMutation({
    mutationFn: () => rejectReview(selected!.correlation_id, rejectReason),
    onSuccess: () => {
      toast.success("Eintrag abgelehnt.");
      clearSelection();
      invalidate();
    },
  });

  const selectItem = (item: ReviewQueueItem) => {
    setSelected(item);
    setDraftEdit(item.draft_body);
    setRejectReason("");
  };

  return {
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
  };
}
