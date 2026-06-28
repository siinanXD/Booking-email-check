// Typen fürs Admin-Datenfluss-Board (Funnel/Entscheidungen, Status, Stuck).
// Re-exportiert über `api-admin.ts`.

export interface FunnelStage {
  state: string;
  label: string;
  count: number;
}

export interface ConfidenceBucket {
  bucket: string;
  count: number;
}

export interface SourceFlagCount {
  flag: string;
  count: number;
}

export interface DecisionBreakdown {
  auto_approved: number;
  human_approved: number;
  escalated: number;
  rejected: number;
  pending: number;
  confidence_buckets: ConfidenceBucket[];
  grounding: { ok: number; fail: number };
  top_source_flags: SourceFlagCount[];
}

export interface AdminPipelineResponse {
  days: number;
  funnel: {
    states: FunnelStage[];
    total: number;
  };
  decisions: DecisionBreakdown;
}

export interface AdminStatusResponse {
  db: { ok: boolean };
  polling: {
    expected: boolean;
    stale: boolean;
    last_sync_at: string | null;
    pollable_accounts: number;
  };
  whatsapp_24h: {
    sent: number;
    failed: number;
    skipped: number;
    pending: number;
  };
  accounts: { connected: number; error: number; total: number };
  integrations: {
    langfuse_configured: boolean;
    sentry_configured: boolean;
  };
  overall: "ok" | "degraded" | "down";
}

export interface AdminStuckItem {
  correlation_id: string;
  account_id: string | null;
  tenant: string | null;
  subject: string;
  processing_state: string;
  updated_at: string | null;
  age_hours: number;
  reason: string | null;
}

export interface AdminStuckResponse {
  kind: string;
  items: AdminStuckItem[];
  total: number;
}
