import { apiClient } from "@/lib/api/client";
import type {
  AdminSupportTicketListResponse,
  AdminSupportTicketResponse,
  PlatformAdminConfigResponse,
  PlatformAdminConfigUpdateRequest,
  SupportTicketCreateRequest,
  SupportTicketListResponse,
  SupportTicketResponse,
  SupportTicketStatus,
  SupportTicketUrgency,
} from "@/lib/types/api-support";

export async function createSupportTicket(
  payload: SupportTicketCreateRequest
): Promise<SupportTicketResponse> {
  const { data } = await apiClient.post<SupportTicketResponse>(
    "/api/support/tickets",
    payload
  );
  return data;
}

export async function fetchSupportTickets(
  limit = 50
): Promise<SupportTicketListResponse> {
  const { data } = await apiClient.get<SupportTicketListResponse>(
    "/api/support/tickets",
    { params: { limit } }
  );
  return data;
}

export async function fetchAdminSupportTickets(params?: {
  status?: SupportTicketStatus;
  urgency?: SupportTicketUrgency;
  account_id?: string;
}): Promise<AdminSupportTicketListResponse> {
  const { data } = await apiClient.get<AdminSupportTicketListResponse>(
    "/api/admin/support/tickets",
    { params }
  );
  return data;
}

export async function patchAdminSupportTicket(
  ticketId: string,
  body: { status?: SupportTicketStatus; admin_note?: string }
): Promise<AdminSupportTicketResponse> {
  const { data } = await apiClient.patch<AdminSupportTicketResponse>(
    `/api/admin/support/tickets/${ticketId}`,
    body
  );
  return data;
}

export async function retryAdminSupportTicketWhatsApp(
  ticketId: string
): Promise<AdminSupportTicketResponse> {
  const { data } = await apiClient.post<AdminSupportTicketResponse>(
    `/api/admin/support/tickets/${ticketId}/retry-whatsapp`
  );
  return data;
}

export async function fetchAdminSupportConfig(): Promise<PlatformAdminConfigResponse> {
  const { data } = await apiClient.get<PlatformAdminConfigResponse>(
    "/api/admin/support/config"
  );
  return data;
}

export async function saveAdminSupportConfig(
  payload: PlatformAdminConfigUpdateRequest
): Promise<PlatformAdminConfigResponse> {
  const { data } = await apiClient.put<PlatformAdminConfigResponse>(
    "/api/admin/support/config",
    payload
  );
  return data;
}
