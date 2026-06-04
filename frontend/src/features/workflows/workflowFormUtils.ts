import type {
  TenantWorkflowCreateRequest,
  TenantWorkflowSuggestResponse,
  WorkflowMediaAttachment,
} from "@/lib/types/api";

export const EMPTY_FORM: TenantWorkflowCreateRequest = {
  label: "",
  slug: "",
  description: "",
  search_hints: "",
  importance: "medium",
  required_fields: [],
  optional_fields: [],
  extraction_schema: {},
  classify_prompt: "",
  extract_prompt: "",
  draft_prompt: "",
  test_emails: [],
  match_rules: { subject_keywords: [], from_domains: [], body_keywords: [] },
  llm_provider: "openai",
  supports_multimodal: false,
  multimodal_prompt: "",
  enabled: false,
  sandbox_only: true,
  priority: 0,
};

export function applySuggestion(
  suggestion: TenantWorkflowSuggestResponse
): TenantWorkflowCreateRequest {
  return {
    ...EMPTY_FORM,
    label: suggestion.label,
    slug: suggestion.slug,
    description: suggestion.description,
    search_hints: suggestion.search_hints,
    importance: suggestion.importance,
    required_fields: suggestion.required_fields,
    optional_fields: suggestion.optional_fields,
    extraction_schema: suggestion.extraction_schema,
    classify_prompt: suggestion.classify_prompt,
    extract_prompt: suggestion.extract_prompt,
    test_emails: suggestion.test_emails,
    match_rules: suggestion.match_rules,
    llm_provider: suggestion.llm_provider,
    supports_multimodal: suggestion.supports_multimodal,
    multimodal_prompt: suggestion.multimodal_prompt ?? "",
    enabled: false,
    sandbox_only: true,
  };
}

export function fieldsToText(fields: string[]): string {
  return fields.join(", ");
}

export function textToFields(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export async function filesToAttachments(
  files: FileList | null
): Promise<WorkflowMediaAttachment[]> {
  if (!files?.length) return [];
  const allowed = new Set([
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
  ]);
  const out: WorkflowMediaAttachment[] = [];
  for (const file of Array.from(files).slice(0, 5)) {
    if (!allowed.has(file.type)) continue;
    const buffer = await file.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i] ?? 0);
    }
    out.push({
      filename: file.name,
      mime_type: file.type,
      data_base64: btoa(binary),
    });
  }
  return out;
}
