import { apiClient } from "@/lib/api/client";
import type { PlanCatalogResponse, SubscriptionResponse } from "@/lib/types/api";

export async function fetchAdminAccountSubscription(
  accountId: string
): Promise<SubscriptionResponse> {
  const { data } = await apiClient.get<SubscriptionResponse>(
    `/api/admin/accounts/${accountId}/subscription`
  );
  return data;
}

export async function fetchPlanCatalog(): Promise<PlanCatalogResponse> {
  const { data } = await apiClient.get<PlanCatalogResponse>("/api/billing/plans");
  return data;
}

export async function setAccountSubscription(
  accountId: string,
  planId: string,
  periodEnd?: string | null
): Promise<SubscriptionResponse> {
  const { data } = await apiClient.put<SubscriptionResponse>(
    `/api/admin/accounts/${accountId}/subscription`,
    { plan_id: planId, period_end: periodEnd ?? null }
  );
  return data;
}

export async function extendAccountTrial(
  accountId: string,
  days: number
): Promise<SubscriptionResponse> {
  const { data } = await apiClient.post<SubscriptionResponse>(
    `/api/admin/accounts/${accountId}/subscription/extend-trial`,
    { days }
  );
  return data;
}

export async function setSubscriptionOverrides(
  accountId: string,
  overrides: {
    override_max_mails?: number | null;
    override_max_properties?: number | null;
    override_max_users?: number | null;
  }
): Promise<SubscriptionResponse> {
  const { data } = await apiClient.put<SubscriptionResponse>(
    `/api/admin/accounts/${accountId}/subscription/overrides`,
    overrides
  );
  return data;
}
