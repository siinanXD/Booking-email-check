import { apiClient } from "@/api/client";
import type { ReviewQueueResponse } from "@/types/api";

export async function fetchReviewPending(
  limit = 50
): Promise<ReviewQueueResponse> {
  const { data } = await apiClient.get<ReviewQueueResponse>(
    "/api/review/pending",
    { params: { limit } }
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

export async function rejectReview(
  correlationId: string,
  reason: string
): Promise<void> {
  await apiClient.post("/api/review/reject", {
    correlation_id: correlationId,
    reason,
  });
}
