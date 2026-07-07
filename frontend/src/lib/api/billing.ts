import { apiClient } from "@/lib/api/client";
import type { PlanCatalogResponse, SubscriptionResponse } from "@/lib/types/api";

export async function fetchSubscription(): Promise<SubscriptionResponse> {
  const { data } = await apiClient.get<SubscriptionResponse>(
    "/api/billing/subscription"
  );
  return data;
}

export async function fetchPlanCatalog(): Promise<PlanCatalogResponse> {
  const { data } = await apiClient.get<PlanCatalogResponse>("/api/billing/plans");
  return data;
}

export async function startCheckout(planId: string): Promise<void> {
  const { data } = await apiClient.post<{ url: string }>("/api/billing/checkout", {
    plan_id: planId,
  });
  window.location.assign(data.url);
}

export async function openBillingPortal(): Promise<void> {
  const { data } = await apiClient.post<{ url: string }>("/api/billing/portal");
  window.location.assign(data.url);
}
