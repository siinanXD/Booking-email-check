import { apiClient } from "@/api/client";
import type {
  PlatformSettingsResponse,
  PlatformSettingsUpdate,
  WhatsAppTestResponse,
  WipeDataResponse,
} from "@/types/api";

export async function fetchSettings(): Promise<PlatformSettingsResponse> {
  const { data } = await apiClient.get<PlatformSettingsResponse>("/api/settings");
  return data;
}

export async function saveSettings(
  payload: PlatformSettingsUpdate
): Promise<PlatformSettingsResponse> {
  const { data } = await apiClient.put<PlatformSettingsResponse>(
    "/api/settings",
    payload
  );
  return data;
}

export async function testWhatsApp(
  recipientE164?: string
): Promise<WhatsAppTestResponse> {
  const { data } = await apiClient.post<WhatsAppTestResponse>(
    "/api/settings/whatsapp/test",
    recipientE164 ? { recipient_e164: recipientE164 } : {}
  );
  return data;
}

export async function wipeAllData(): Promise<WipeDataResponse> {
  const { data } = await apiClient.post<WipeDataResponse>(
    "/api/settings/wipe-all",
    { confirm: "ALLE DATEN LOESCHEN" }
  );
  return data;
}
