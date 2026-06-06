import type { CostSeriesPoint } from "./api-cost";

export interface AccountListItem {
  id: string;
  display_name: string;
  contact_email: string;
  account_type: string;
  company_name?: string | null;
  phone?: string | null;
  status: string;
  rejection_reason?: string | null;
  created_at: string;
}

export interface AccountListResponse {
  items: AccountListItem[];
  total: number;
}

export interface AdminMeResponse {
  id: string;
  email: string;
  role: string;
  account_id?: string | null;
  mail_onboarding_required: boolean;
}

export type AdminWhatsAppTestTemplate =
  | "hello_world"
  | "cleaning_task"
  | "status_notice"
  | "guest_inquiry"
  | "support_ticket";

export interface AdminWhatsAppTemplatesUpdate {
  template_language?: string;
  template_cleaning_task?: string;
  template_status_notice?: string;
  template_guest_inquiry?: string;
  template_support_ticket?: string;
}

export interface AdminWhatsAppInfoResponse {
  whatsapp_enabled: boolean;
  access_token_configured: boolean;
  phone_number_id: string;
  test_recipient: string;
  template_language: string;
  templates: Record<string, string>;
}

export interface AdminWhatsAppTestResponse {
  success: boolean;
  template: AdminWhatsAppTestTemplate;
  template_name?: string | null;
  provider_message_id?: string | null;
  error?: string | null;
}

export type ActivityStatus = "active" | "idle" | "never";

export interface AdminTenantRow {
  account: AccountListItem;
  activity_status: ActivityStatus;
  costs_30d_usd: number;
  tokens_30d: number;
  mails_processed_30d: number;
  last_sync_at: string | null;
  last_mail_received_at: string | null;
}

export interface AdminOverviewResponse {
  total_accounts: number;
  pending_accounts: number;
  active_accounts: number;
  active_users_7d: number;
  total_cost_usd_30d: number;
  total_tokens_30d: number;
  mails_processed_30d: number;
  tenants: AdminTenantRow[];
}

export interface AdminUserSummary {
  id: string;
  email: string;
  role: string;
  created_at: string;
}

export interface MailConnectionSummary {
  provider: string;
  status: string;
  email_address: string;
  connected: boolean;
  last_sync_at: string | null;
  last_error: string | null;
  onboarding_completed: boolean;
}

export interface AdminAccountDetailResponse {
  account: AccountListItem;
  users: AdminUserSummary[];
  mail_connection: MailConnectionSummary | null;
  activity_status: ActivityStatus;
  db_counts: Record<string, number>;
  costs_30d_usd: number;
  tokens_30d: number;
  mails_processed_30d: number;
  last_mail_received_at: string | null;
  latest_correlation_id: string | null;
  langfuse_session_url: string | null;
}

export interface AdminAccountCostRow {
  account_id: string;
  display_name: string;
  cost_usd: number;
  total_tokens: number;
  mail_count: number;
}

export interface AdminExpensiveMailRow {
  correlation_id: string;
  account_id: string | null;
  cost_usd: number;
  total_tokens: number;
  processed_at: string;
  langfuse_session_url: string | null;
}

export interface AdminCostsMetricsResponse {
  days: number;
  series: CostSeriesPoint[];
  total_usd: number;
  unassigned_cost_usd: number;
  by_account: AdminAccountCostRow[];
  top_mails: AdminExpensiveMailRow[];
}

export interface AdminTokensMetricsResponse {
  days: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  by_account: AdminAccountCostRow[];
}

export interface AdminPublicConfigResponse {
  langfuse_host: string;
  langfuse_project_id: string | null;
  langfuse_tracing_enabled: boolean;
}

export type AdminLlmPreviewStep = "classify" | "extract";

export interface AdminLlmConfigResponse {
  classify_temperature: number;
  extract_temperature: number;
  draft_temperature: number;
  similarity_top_k: number;
  classify_prompt_override: string | null;
  extract_prompt_override: string | null;
  draft_prompt_override: string | null;
  default_classify_prompt: string;
  default_extract_prompt: string;
  default_draft_prompt: string;
  updated_at: string | null;
  updated_by_user_id: string | null;
}

export interface AdminLlmConfigUpdateRequest {
  classify_temperature: number;
  extract_temperature: number;
  draft_temperature: number;
  similarity_top_k: number;
  classify_prompt_override?: string | null;
  extract_prompt_override?: string | null;
  draft_prompt_override?: string | null;
}

export interface AdminLlmPreviewRequest {
  step?: AdminLlmPreviewStep;
  subject?: string;
  body?: string;
}

export interface AdminLlmPreviewResponse {
  step: AdminLlmPreviewStep;
  success: boolean;
  result: string | null;
  error: string | null;
  model: string;
}

export type AdminLlmPromptType = "classify" | "extract" | "draft";

export interface AdminLlmPromptHistoryEntry {
  id: string;
  prompt_type: AdminLlmPromptType;
  prompt_text: string | null;
  user_id: string | null;
  created_at: string;
}

export interface AdminLlmPromptHistoryResponse {
  prompt_type: AdminLlmPromptType;
  entries: AdminLlmPromptHistoryEntry[];
}
