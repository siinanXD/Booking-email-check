export interface SubscriptionResponse {
  plan_id: string;
  plan_name: string;
  status: string;
  period_end: string;
  quota_window_start: string;
  mails_used: number;
  mails_limit: number;
  properties_used: number;
  properties_limit: number;
  users_used: number;
  users_limit: number;
  mailboxes_limit: number;
  effective_features: string[];
  self_service: boolean;
}

export interface PlanCatalogItem {
  plan_id: string;
  display_name: string;
  price_eur_monthly: number;
  monthly_mail_quota: number;
  max_properties: number;
  max_users: number;
  max_mailboxes: number;
  features: string[];
}

export interface PlanCatalogResponse {
  items: PlanCatalogItem[];
}
