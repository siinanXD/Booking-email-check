export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: string;
  account_id?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  account_status?: string | null;
  account_display_name?: string | null;
  mail_connection_status?: string | null;
  mail_onboarding_completed?: boolean | null;
}

export interface ImapPresetItem {
  id: string;
  label: string;
  host: string;
  port: number;
  use_ssl: boolean;
}

export interface MailConnectionResponse {
  provider: "outlook" | "imap" | string;
  status: string;
  email_address: string;
  preset?: string | null;
  imap_host: string;
  imap_port: number;
  imap_username: string;
  imap_password_set: boolean;
  imap_use_ssl: boolean;
  outlook_auth_mode: string;
  outlook_mailbox: string;
  outlook_oauth_connected?: boolean;
  last_error?: string | null;
  last_sync_at?: string | null;
  onboarding_completed: boolean;
  imap_presets: ImapPresetItem[];
}

export interface MailTestResponse {
  success: boolean;
  message: string;
  mailbox_count?: number | null;
}

export interface MailSyncResponse {
  success: boolean;
  processed: number;
  duplicates: number;
  error_count: number;
  reprocessed?: number;
  message: string;
  last_sync_at?: string | null;
  item_errors?: string[];
  reprocess_errors?: string[];
}

export interface RegisterRequest {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  phone: string;
  account_type: "private" | "business";
  company_name?: string;
}

export interface RegisterResponse {
  message: string;
  account_id: string;
  status: string;
}

export interface DashboardStats {
  total_emails_today: number;
  total_emails_week: number;
  pending_review: number;
  processed_today: number;
  spam_discarded_today: number;
  new_bookings_today: number;
  cancellations_today: number;
  changes_today: number;
  booking_emails_total: number;
  booking_emails_week: number;
  cost_today_usd: number;
  cost_week_usd: number;
  avg_cost_per_mail_usd: number;
  grounding_failures_today: number;
  /** Ausstehende Reviews mit Grounding-Hinweis (für Review-Filter). */
  pending_grounding_review?: number;
  reviewed_today: number;
  last_sync_at?: string | null;
  last_email_received_at?: string | null;
  last_booking_detected_at?: string | null;
  mail_fetch_unread_only?: boolean;
  nav_bookings?: number;
  nav_cancellations?: number;
  nav_changes?: number;
  nav_messages?: number;
  nav_ground_zero?: number;
  nav_completed?: number;
}

export interface EmailListItem {
  correlation_id: string;
  message_id: string;
  subject: string;
  from_address: string;
  received_at: string | null;
  platform: string | null;
  intent: string | null;
  booking_number: string | null;
  processing_state: string;
  review_status: string | null;
  grounding_flag: boolean;
}

export interface EmailListResponse {
  items: EmailListItem[];
  total: number;
  page: number;
  pages: number;
}

export interface EmailDetail extends EmailListItem {
  to_addresses: string[];
  body_text: string;
  draft_body: string;
  extraction: Record<string, unknown> | null;
  approved_body: string | null;
  mail_summary?: string | null;
  mail_sentiment?: string | null;
}

export interface EmailActivityEvent {
  at: string;
  kind: string;
  label: string;
  actor?: string | null;
}

export interface EmailActivityResponse {
  correlation_id: string;
  events: EmailActivityEvent[];
}

export interface WhatsAppPreviewMessage {
  recipient_e164: string;
  template_name: string;
  template_language: string;
  template_params: string[];
  kind: string;
}

export interface WhatsAppPreviewResponse {
  correlation_id: string;
  enabled: boolean;
  messages: WhatsAppPreviewMessage[];
  note?: string | null;
}

export interface ReviewQueueItem {
  correlation_id: string;
  message_id: string;
  subject: string;
  from_address: string;
  intent: string | null;
  draft_body: string;
  grounding_flag: boolean;
  review_status: string;
  received_at: string | null;
}

export interface ReviewQueueResponse {
  items: ReviewQueueItem[];
  total: number;
}

export interface PropertyRecipientItem {
  property_name: string;
  phones: string[];
}

export interface UserProfileSettings {
  whatsapp_phone_e164: string | null;
  whatsapp_enabled: boolean;
}

export interface PlatformSettingsResponse {
  whatsapp_enabled: boolean;
  whatsapp_access_token_set: boolean;
  whatsapp_phone_number_id: string;
  whatsapp_api_version: string;
  whatsapp_template_language: string;
  whatsapp_template_cleaning_task: string;
  whatsapp_template_status_notice: string;
  whatsapp_template_guest_inquiry: string;
  whatsapp_default_recipients: string;
  whatsapp_test_recipient: string;
  outlook_mailbox: string;
  property_recipients: PropertyRecipientItem[];
  user_profile: UserProfileSettings;
}

export interface PlatformSettingsUpdate {
  whatsapp_enabled?: boolean;
  whatsapp_access_token?: string;
  whatsapp_phone_number_id?: string;
  whatsapp_api_version?: string;
  whatsapp_template_language?: string;
  whatsapp_template_cleaning_task?: string;
  whatsapp_template_status_notice?: string;
  whatsapp_template_guest_inquiry?: string;
  whatsapp_default_recipients?: string;
  whatsapp_test_recipient?: string;
  outlook_mailbox?: string;
  property_recipients?: PropertyRecipientItem[];
  user_profile?: UserProfileSettings;
}

export interface WhatsAppTestResponse {
  success: boolean;
  provider_message_id?: string | null;
  error?: string | null;
}

export interface WipeDataResponse {
  deleted: Record<string, number>;
}

export interface ApiError {
  error: string;
  code: number;
}

export * from "./api-admin";
export * from "./api-cost";
export * from "./api-workflows";
