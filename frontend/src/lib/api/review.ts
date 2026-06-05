import { apiClient } from "@/lib/api/client";
import type {
  ReviewQueueResponse,
  WhatsAppPreviewResponse,
} from "@/lib/types/api";

export type ReviewQueueTab = "pending" | "released" | "completed";

export async function fetchReviewQueue(
  tab: ReviewQueueTab,
  limit = 50,
  intent?: string,
  groundingOnly?: boolean
): Promise<ReviewQueueResponse> {
  const path =
    tab === "pending"
      ? "/api/review/pending"
      : tab === "released"
        ? "/api/review/released"
        : "/api/review/completed";
  const { data } = await apiClient.get<ReviewQueueResponse>(path, {
    params: {
      limit,
      ...(intent ? { intent } : {}),
      ...(groundingOnly ? { grounding: "1" } : {}),
    },
  });
  return data;
}

export async function fetchReviewPending(
  limit = 50
): Promise<ReviewQueueResponse> {
  return fetchReviewQueue("pending", limit);
}

export async function fetchGroundZeroQueue(
  limit = 50,
  intent?: string
): Promise<ReviewQueueResponse> {
  const { data } = await apiClient.get<ReviewQueueResponse>(
    "/api/review/ground-zero",
    {
      params: {
        limit,
        ...(intent ? { intent } : {}),
      },
    }
  );
  return data;
}

export async function fetchWhatsAppPreview(
  correlationId: string
): Promise<WhatsAppPreviewResponse> {
  const { data } = await apiClient.get<WhatsAppPreviewResponse>(
    `/api/review/whatsapp-preview/${correlationId}`
  );
  return data;
}

export async function approveReview(
  correlationId: string,
  approvedBody?: string
): Promise<void> {
  await apiClient.post("/api/review/approve", {
    correlation_id: correlationId,
    approved_body: approvedBody,
  });
}

export async function completeReview(correlationId: string): Promise<void> {
  await apiClient.post("/api/review/complete", {
    correlation_id: correlationId,
  });
}

export async function rejectReview(
  correlationId: string,
  reason: string
): Promise<void> {
  await apiClient.post("/api/review/reject", {
    correlation_id: correlationId,
    reason,
  });
}
