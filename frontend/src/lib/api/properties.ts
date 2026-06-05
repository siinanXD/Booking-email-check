import { apiClient } from "@/lib/api/client";
import type { PropertyRecipientItem } from "@/lib/types/api";

export type PropertyHistoryItem = {
  correlation_id: string;
  subject: string;
  received_at: string | null;
  intent: string | null;
  booking_number: string | null;
  property_name: string | null;
};

export type PropertySuggestion = {
  property_name: string;
  mail_count: number;
};

export async function fetchPropertyHistory(params?: {
  property_name?: string;
  limit?: number;
}): Promise<{ items: PropertyHistoryItem[]; total: number }> {
  const { data } = await apiClient.get("/api/properties/history", { params });
  return data;
}

export async function fetchPropertyRecipients(): Promise<{
  items: PropertyRecipientItem[];
}> {
  const { data } = await apiClient.get("/api/properties/recipients");
  return data;
}

export async function savePropertyRecipients(
  items: PropertyRecipientItem[]
): Promise<{ items: PropertyRecipientItem[] }> {
  const { data } = await apiClient.put("/api/properties/recipients", { items });
  return data;
}

export async function fetchPropertySuggestions(limit = 20): Promise<{
  items: PropertySuggestion[];
}> {
  const { data } = await apiClient.get("/api/properties/suggestions", {
    params: { limit },
  });
  return data;
}

export type PropertyYearStats = {
  year: number;
  booked_days: number;
  revenue: number;
  booking_count: number;
  incomplete_data_count: number;
};

export type PropertyListItem = {
  property_id: string;
  name: string;
  platform: string | null;
  location: string | null;
  stats: PropertyYearStats | null;
};

export type PropertyProfile = {
  property_id: string;
  name: string;
  platform: string | null;
  location: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  notes: string | null;
  whatsapp_phones: string[];
};

export async function fetchProperties(year?: number): Promise<{
  items: PropertyListItem[];
}> {
  const { data } = await apiClient.get("/api/properties", {
    params: year ? { year } : undefined,
  });
  return data;
}

export async function createProperty(payload: {
  name: string;
  from_suggestion?: boolean;
}): Promise<PropertyProfile> {
  const { data } = await apiClient.post("/api/properties", payload);
  return data;
}

export async function fetchPropertyProfile(
  propertyId: string
): Promise<PropertyProfile> {
  const { data } = await apiClient.get(`/api/properties/${propertyId}`);
  return data;
}

export async function updatePropertyProfile(
  propertyId: string,
  payload: Partial<
    Pick<
      PropertyProfile,
      | "name"
      | "platform"
      | "location"
      | "contact_name"
      | "contact_phone"
      | "contact_email"
      | "notes"
      | "whatsapp_phones"
    >
  >
): Promise<PropertyProfile> {
  const { data } = await apiClient.put(`/api/properties/${propertyId}`, payload);
  return data;
}

export async function fetchPropertyStats(
  propertyId: string,
  year?: number
): Promise<PropertyYearStats> {
  const { data } = await apiClient.get(`/api/properties/${propertyId}/stats`, {
    params: year ? { year } : undefined,
  });
  return data;
}
