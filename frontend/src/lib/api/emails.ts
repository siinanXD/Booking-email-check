import { apiClient } from "@/lib/api/client";
import type {
  EmailActivityResponse,
  EmailDetail,
  EmailListResponse,
} from "@/lib/types/api";

export interface EmailListParams {
  status?: string;
  intent?: string;
  /** Komma-getrennte Intent-Liste (z. B. guest_inquiry,other) */
  intents?: string;
  booking_related?: boolean;
  workflow_slug?: string;
  platform?: string;
  search?: string;
  page?: number;
  limit?: number;
  from_date?: string;
  to_date?: string;
}

export async function fetchEmails(
  params: EmailListParams = {}
): Promise<EmailListResponse> {
  const { data } = await apiClient.get<EmailListResponse>("/api/emails/", {
    params,
  });
  return data;
}

export async function fetchEmailDetail(
  correlationId: string
): Promise<EmailDetail> {
  const { data } = await apiClient.get<EmailDetail>(
    `/api/emails/${correlationId}`
  );
  return data;
}

export async function fetchEmailActivity(
  correlationId: string
): Promise<EmailActivityResponse> {
  const { data } = await apiClient.get<EmailActivityResponse>(
    `/api/emails/${correlationId}/activity`
  );
  return data;
}

export async function fetchBookings(
  params: Omit<EmailListParams, "intent"> = {}
): Promise<EmailListResponse> {
  const { data } = await apiClient.get<EmailListResponse>("/api/bookings/", {
    params,
  });
  return data;
}
