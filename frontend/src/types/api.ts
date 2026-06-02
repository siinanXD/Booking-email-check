export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: string;
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
}

export interface CostSeriesPoint {
  date: string;
  cost_usd: number;
  total_tokens: number;
  mail_count: number;
}

export interface CostsResponse {
  series: CostSeriesPoint[];
  total_usd: number;
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

export interface ApiError {
  error: string;
  code: number;
}
