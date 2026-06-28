import { apiClient } from "@/lib/api/client";
import type {
  GuestConsent,
  GuestDeleteResponse,
  GuestExportResponse,
} from "@/lib/types/api";

export async function exportGuest(
  email: string
): Promise<GuestExportResponse> {
  const { data } = await apiClient.get<GuestExportResponse>(
    `/api/guests/${encodeURIComponent(email)}/export`
  );
  return data;
}

export async function deleteGuest(
  email: string
): Promise<GuestDeleteResponse> {
  const { data } = await apiClient.delete<GuestDeleteResponse>(
    `/api/guests/${encodeURIComponent(email)}`
  );
  return data;
}

export async function getGuestConsent(email: string): Promise<GuestConsent> {
  const { data } = await apiClient.get<GuestConsent>(
    `/api/guests/${encodeURIComponent(email)}/consent`
  );
  return data;
}

export async function setGuestConsent(
  email: string,
  whatsappConsent: boolean
): Promise<GuestConsent> {
  const { data } = await apiClient.put<GuestConsent>(
    `/api/guests/${encodeURIComponent(email)}/consent`,
    { whatsapp_consent: whatsappConsent }
  );
  return data;
}
