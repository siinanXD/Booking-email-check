import { apiClient } from "@/lib/api/client";

export type SearchHit = {
  id: string;
  title: string;
  subtitle?: string;
  /** Ziel-Route innerhalb der App. */
  href: string;
};

export type SearchResponse = {
  bookings: SearchHit[];
  properties: SearchHit[];
  mails: SearchHit[];
};

export async function globalSearch(query: string): Promise<SearchResponse> {
  const { data } = await apiClient.get<SearchResponse>("/api/search", {
    params: { q: query },
  });
  return data;
}
