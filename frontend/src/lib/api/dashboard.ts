import { apiClient } from "@/lib/api/client";
import type { CostsResponse, DashboardStats } from "@/lib/types/api";

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await apiClient.get<DashboardStats>("/api/dashboard/stats");
  return data;
}

/** Tenant-scoped daily mail/cost series for the dashboard trend chart. */
export async function fetchMailVolume(
  fromDate?: string,
  toDate?: string
): Promise<CostsResponse> {
  const { data } = await apiClient.get<CostsResponse>(
    "/api/dashboard/mail-volume",
    { params: { from_date: fromDate, to_date: toDate, group_by: "day" } }
  );
  return data;
}
