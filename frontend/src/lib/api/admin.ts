import { apiClient } from "@/lib/api/client";
import type {
  AccountListResponse,
  AdminActivityResponse,
  AdminAuditLogResponse,
  AdminAccountDetailResponse,
  AdminCostsMetricsResponse,
  AdminMeResponse,
  AdminOverviewResponse,
  AdminPublicConfigResponse,
  AdminTokensMetricsResponse,
  AdminLlmConfigResponse,
  AdminLlmConfigUpdateRequest,
  AdminLlmPreviewRequest,
  AdminLlmPreviewResponse,
  AdminLlmPromptHistoryResponse,
  AdminLlmPromptType,
  AdminWhatsAppInfoResponse,
  AdminWhatsAppTemplatesUpdate,
  AdminWhatsAppTestResponse,
  AdminWhatsAppTestTemplate,
  MailConnectionResponse,
  MailTestResponse,
} from "@/lib/types/api";

export async function fetchAdminMe(): Promise<AdminMeResponse> {
  const { data } = await apiClient.get<AdminMeResponse>("/api/admin/me");
  return data;
}

export async function fetchPendingAccounts(): Promise<AccountListResponse> {
  const { data } = await apiClient.get<AccountListResponse>(
    "/api/admin/accounts?status=pending"
  );
  return data;
}

export async function fetchAllAccounts(): Promise<AccountListResponse> {
  const { data } = await apiClient.get<AccountListResponse>(
    "/api/admin/accounts"
  );
  return data;
}

export async function approveAccount(accountId: string): Promise<void> {
  await apiClient.post(`/api/admin/accounts/${accountId}/approve`);
}

export async function rejectAccount(
  accountId: string,
  reason?: string
): Promise<void> {
  await apiClient.post(`/api/admin/accounts/${accountId}/reject`, {
    reason: reason ?? null,
  });
}

// ── Account management ─────────────────────────────────────────────────────

export async function suspendAccount(accountId: string): Promise<void> {
  await apiClient.post(`/api/admin/accounts/${accountId}/suspend`);
}

export async function unsuspendAccount(accountId: string): Promise<void> {
  await apiClient.post(`/api/admin/accounts/${accountId}/unsuspend`);
}

export async function setAccountExpiry(accountId: string, expiresAt: string | null): Promise<void> {
  await apiClient.post(`/api/admin/accounts/${accountId}/expiry`, { expires_at: expiresAt });
}

export async function deleteAccount(accountId: string): Promise<void> {
  await apiClient.delete(`/api/admin/accounts/${accountId}`);
}

// ── User management ────────────────────────────────────────────────────────

export async function lockUser(accountId: string, userId: string, locked: boolean): Promise<void> {
  await apiClient.post(`/api/admin/accounts/${accountId}/users/${userId}/lock`, { locked });
}

export async function resetUserPassword(accountId: string, userId: string, newPassword: string): Promise<void> {
  await apiClient.post(`/api/admin/accounts/${accountId}/users/${userId}/reset-password`, { new_password: newPassword });
}

export async function deleteUser(accountId: string, userId: string): Promise<void> {
  await apiClient.delete(`/api/admin/accounts/${accountId}/users/${userId}`);
}

export async function fetchAccountMailConnection(
  accountId: string
): Promise<MailConnectionResponse> {
  const { data } = await apiClient.get<MailConnectionResponse>(
    `/api/admin/accounts/${accountId}/mail/connection`
  );
  return data;
}

export async function testAccountMailConnection(
  accountId: string
): Promise<MailTestResponse> {
  const { data } = await apiClient.post<MailTestResponse>(
    `/api/admin/accounts/${accountId}/mail/test`
  );
  return data;
}

export async function fetchAccountWhatsAppInfo(
  accountId: string
): Promise<AdminWhatsAppInfoResponse> {
  const { data } = await apiClient.get<AdminWhatsAppInfoResponse>(
    `/api/admin/accounts/${accountId}/whatsapp`
  );
  return data;
}

export async function testAccountWhatsApp(
  accountId: string,
  payload: {
    recipient_e164?: string;
    template?: AdminWhatsAppTestTemplate;
  }
): Promise<AdminWhatsAppTestResponse> {
  const { data } = await apiClient.post<AdminWhatsAppTestResponse>(
    `/api/admin/accounts/${accountId}/whatsapp/test`,
    payload
  );
  return data;
}

export async function saveAccountWhatsAppTemplates(
  accountId: string,
  payload: AdminWhatsAppTemplatesUpdate
): Promise<AdminWhatsAppInfoResponse> {
  const { data } = await apiClient.put<AdminWhatsAppInfoResponse>(
    `/api/admin/accounts/${accountId}/whatsapp/templates`,
    payload
  );
  return data;
}

export async function fetchAdminActivity(
  limit = 50
): Promise<AdminActivityResponse> {
  const { data } = await apiClient.get<AdminActivityResponse>(
    "/api/admin/activity",
    { params: { limit } }
  );
  return data;
}

export async function fetchAdminAuditLog(
  limit = 100
): Promise<AdminAuditLogResponse> {
  const { data } = await apiClient.get<AdminAuditLogResponse>(
    "/api/admin/audit-log",
    { params: { limit } }
  );
  return data;
}

export async function fetchAdminOverview(): Promise<AdminOverviewResponse> {
  const { data } = await apiClient.get<AdminOverviewResponse>(
    "/api/admin/overview"
  );
  return data;
}

export async function fetchAdminAccountDetail(
  accountId: string
): Promise<AdminAccountDetailResponse> {
  const { data } = await apiClient.get<AdminAccountDetailResponse>(
    `/api/admin/accounts/${accountId}/detail`
  );
  return data;
}

export async function fetchAdminCostsMetrics(
  days = 30
): Promise<AdminCostsMetricsResponse> {
  const { data } = await apiClient.get<AdminCostsMetricsResponse>(
    "/api/admin/metrics/costs",
    { params: { days } }
  );
  return data;
}

export async function fetchAdminTokensMetrics(
  days = 30
): Promise<AdminTokensMetricsResponse> {
  const { data } = await apiClient.get<AdminTokensMetricsResponse>(
    "/api/admin/metrics/tokens",
    { params: { days } }
  );
  return data;
}

export async function fetchAdminPublicConfig(): Promise<AdminPublicConfigResponse> {
  const { data } = await apiClient.get<AdminPublicConfigResponse>(
    "/api/admin/config/public"
  );
  return data;
}

export async function fetchAdminLlmConfig(): Promise<AdminLlmConfigResponse> {
  const { data } = await apiClient.get<AdminLlmConfigResponse>(
    "/api/admin/llm-config"
  );
  return data;
}

export async function updateAdminLlmConfig(
  payload: AdminLlmConfigUpdateRequest
): Promise<AdminLlmConfigResponse> {
  const { data } = await apiClient.put<AdminLlmConfigResponse>(
    "/api/admin/llm-config",
    payload
  );
  return data;
}

export async function previewAdminLlmConfig(
  payload: AdminLlmPreviewRequest
): Promise<AdminLlmPreviewResponse> {
  const { data } = await apiClient.post<AdminLlmPreviewResponse>(
    "/api/admin/llm-config/preview",
    payload
  );
  return data;
}

export async function fetchAdminLlmPromptHistory(
  promptType: AdminLlmPromptType,
  limit = 15
): Promise<AdminLlmPromptHistoryResponse> {
  const { data } = await apiClient.get<AdminLlmPromptHistoryResponse>(
    `/api/admin/llm-config/prompt-history/${promptType}`,
    { params: { limit } }
  );
  return data;
}
