import { apiClient } from "@/api/client";
import type { EmailDetail, EmailListResponse } from "@/types/api";

export interface EmailListParams {
  status?: string;
  intent?: string;
  /** Komma-getrennte Intent-Liste (z. B. guest_inquiry,other) */
  intents?: string;
  booking_related?: boolean;
  platform?: string;
  search?: string;
  page?: number;
  limit?: number;
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

export async function fetchBookings(
  params: Omit<EmailListParams, "intent"> = {}
): Promise<EmailListResponse> {
  const { data } = await apiClient.get<EmailListResponse>("/api/bookings/", {
    params,
  });
  return data;
}
