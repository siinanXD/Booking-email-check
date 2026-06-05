export type SupportTicketUrgency = "low" | "normal" | "high" | "critical";
export type SupportTicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type WhatsAppNotifyStatus = "pending" | "sent" | "failed" | "skipped";

export interface SupportTicketResponse {
  ticket_id: string;
  account_id: string;
  created_by_user_id: string;
  created_by_email: string;
  subject: string | null;
  message: string;
  urgency: SupportTicketUrgency;
  status: SupportTicketStatus;
  admin_note: string | null;
  whatsapp_notify_status: WhatsAppNotifyStatus;
  created_at: string;
  updated_at: string;
}

export interface SupportTicketListResponse {
  items: SupportTicketResponse[];
  total: number;
}

export interface SupportTicketCreateRequest {
  subject?: string;
  message: string;
  urgency: SupportTicketUrgency;
}

export interface AdminSupportTicketResponse extends SupportTicketResponse {
  whatsapp_notify_error: string | null;
  whatsapp_message_id: string | null;
  account_display_name: string | null;
}

export interface AdminSupportTicketListResponse {
  items: AdminSupportTicketResponse[];
  total: number;
  open_count: number;
}

export interface PlatformAdminConfigResponse {
  platform_admin_whatsapp_e164: string;
  whatsapp_template_support_ticket: string;
  updated_at: string | null;
}

export interface PlatformAdminConfigUpdateRequest {
  platform_admin_whatsapp_e164?: string;
  whatsapp_template_support_ticket?: string;
}
