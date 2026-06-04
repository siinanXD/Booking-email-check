export type WorkflowImportance = "high" | "medium" | "low";
export type WorkflowLlmProvider = "openai" | "gemini";

export interface WorkflowMatchRules {
  subject_keywords: string[];
  from_domains: string[];
  body_keywords: string[];
}

export interface WorkflowMediaAttachment {
  filename: string;
  mime_type: string;
  data_base64: string;
}

export interface WorkflowTestEmail {
  subject: string;
  body: string;
  expected_fields?: Record<string, unknown> | null;
  attachments?: WorkflowMediaAttachment[];
}

export interface WorkflowFewShotExample {
  subject: string;
  body: string;
  expected_json: Record<string, unknown>;
}

export interface TenantWorkflowSummary {
  id: string;
  slug: string;
  label: string;
  description: string;
  enabled: boolean;
  sandbox_only: boolean;
  importance: WorkflowImportance;
  supports_multimodal: boolean;
  test_email_count: number;
  tests_passed: boolean;
  updated_at: string;
}

export interface TenantWorkflowListResponse {
  items: TenantWorkflowSummary[];
}

export interface TenantWorkflowNavItem {
  id: string;
  slug: string;
  label: string;
  description: string;
}

export interface TenantWorkflowNavResponse {
  items: TenantWorkflowNavItem[];
}

export interface TenantWorkflowResponse {
  id: string;
  account_id: string;
  slug: string;
  label: string;
  description: string;
  enabled: boolean;
  sandbox_only: boolean;
  priority: number;
  search_hints: string;
  importance: WorkflowImportance;
  required_fields: string[];
  optional_fields: string[];
  extraction_schema: Record<string, unknown>;
  classify_prompt: string;
  extract_prompt: string;
  draft_prompt: string;
  few_shot_examples: WorkflowFewShotExample[];
  test_emails: WorkflowTestEmail[];
  match_rules: WorkflowMatchRules;
  llm_provider: WorkflowLlmProvider;
  supports_multimodal: boolean;
  multimodal_prompt: string;
  last_test_passed_at: string | null;
  last_test_passed_count: number;
  last_test_passed_total: number;
  created_by_user_id: string | null;
  updated_by_user_id: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface TenantWorkflowCreateRequest {
  label: string;
  slug?: string | null;
  description?: string;
  search_hints?: string;
  importance?: WorkflowImportance;
  required_fields?: string[];
  optional_fields?: string[];
  extraction_schema?: Record<string, unknown>;
  classify_prompt?: string;
  extract_prompt?: string;
  draft_prompt?: string;
  few_shot_examples?: WorkflowFewShotExample[];
  test_emails?: WorkflowTestEmail[];
  match_rules?: WorkflowMatchRules;
  llm_provider?: WorkflowLlmProvider;
  supports_multimodal?: boolean;
  multimodal_prompt?: string;
  enabled?: boolean;
  sandbox_only?: boolean;
  priority?: number;
}

export type TenantWorkflowUpdateRequest = TenantWorkflowCreateRequest;

export interface TenantWorkflowSuggestRequest {
  description: string;
  label_hint?: string | null;
  attachments?: WorkflowMediaAttachment[];
}

export interface TenantWorkflowSuggestResponse {
  label: string;
  slug: string;
  description: string;
  search_hints: string;
  importance: WorkflowImportance;
  required_fields: string[];
  optional_fields: string[];
  extraction_schema: Record<string, unknown>;
  classify_prompt: string;
  extract_prompt: string;
  multimodal_prompt?: string;
  match_rules: WorkflowMatchRules;
  test_emails: WorkflowTestEmail[];
  llm_provider: WorkflowLlmProvider;
  supports_multimodal: boolean;
}

export interface TenantWorkflowPreviewRequest {
  subject?: string;
  body?: string;
  attachments?: WorkflowMediaAttachment[];
}

export interface TenantWorkflowPreviewResponse {
  success: boolean;
  result: string | null;
  error: string | null;
  model: string;
  notice?: string | null;
}

export interface GeminiStatusResponse {
  configured: boolean;
  available: boolean;
  model: string;
}

export interface TenantWorkflowTestCaseResult {
  subject: string;
  success: boolean;
  result: string | null;
  error: string | null;
}

export interface TenantWorkflowRunTestsResponse {
  workflow_id: string;
  total: number;
  passed: number;
  results: TenantWorkflowTestCaseResult[];
}
