import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useAuthStore } from "@/features/auth/authStore";
import { WorkflowEditorPanel } from "@/features/workflows/WorkflowEditorPanel";
import { WorkflowListPanel } from "@/features/workflows/WorkflowListPanel";
import {
  applySuggestion,
  EMPTY_FORM,
  filesToAttachments,
} from "@/features/workflows/workflowFormUtils";
import { createWorkflowApi } from "@/lib/api/workflows";
import type { TenantWorkflowCreateRequest } from "@/lib/types/api";
import { Card } from "@/shared/ui/Card";

type EditorMode = "list" | "create" | "edit";

export interface WorkflowsPageProps {
  /** Plattform-Admin: Workflows für diesen Mandanten bearbeiten. */
  adminAccountId?: string;
  subtitle?: string;
}

export function WorkflowsPage(props: WorkflowsPageProps = {}) {
  const { adminAccountId, subtitle } = props;
  const queryClient = useQueryClient();
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const api = useMemo(() => createWorkflowApi(adminAccountId), [adminAccountId]);
  const queryKey = useMemo(
    () => (adminAccountId ? ["workflows", "admin", adminAccountId] : ["workflows"]),
    [adminAccountId]
  );
  const [mode, setMode] = useState<EditorMode>("list");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<TenantWorkflowCreateRequest>(EMPTY_FORM);
  const [assistDescription, setAssistDescription] = useState("");
  const [assistFiles, setAssistFiles] = useState<FileList | null>(null);
  const [previewSubject, setPreviewSubject] = useState("Test-Betreff");
  const [previewBody, setPreviewBody] = useState("Test-Inhalt");
  const [previewResult, setPreviewResult] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewNotice, setPreviewNotice] = useState<string | null>(null);
  const [previewFiles, setPreviewFiles] = useState<FileList | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [testsPassed, setTestsPassed] = useState(false);

  const { data: list, isLoading } = useQuery({
    queryKey,
    queryFn: () => api.fetchWorkflows(),
    enabled: Boolean(adminAccountId) || isPlatformAdmin,
  });

  const { data: geminiStatus } = useQuery({
    queryKey: [...queryKey, "gemini-status"],
    queryFn: () => api.fetchGeminiStatus(),
    enabled: Boolean(adminAccountId) || isPlatformAdmin,
  });

  const suggestMut = useMutation({
    mutationFn: async () => {
      const attachments = await filesToAttachments(assistFiles);
      const description =
        assistDescription.trim() ||
        (attachments.length > 0 ? "Workflow aus Beispiel-Screenshot" : "");
      return api.suggestWorkflow({
        description,
        label_hint: form.label || null,
        attachments,
      });
    },
    onSuccess: (res) => {
      setForm(applySuggestion(res));
      if (res.test_emails[0]) {
        setPreviewSubject(res.test_emails[0].subject);
        setPreviewBody(res.test_emails[0].body);
      }
      setMessage(
        res.supports_multimodal
          ? "KI-Vorschlag aus Beispiel übernommen (Felder, Regeln, Test-Mail) — bitte prüfen und speichern."
          : "KI-Vorschlag übernommen — bitte prüfen und speichern."
      );
    },
    onError: (err: unknown) => {
      const msg =
        err &&
        typeof err === "object" &&
        "response" in err &&
        err.response &&
        typeof err.response === "object" &&
        "data" in err.response &&
        err.response.data &&
        typeof err.response.data === "object" &&
        "error" in err.response.data &&
        typeof err.response.data.error === "string"
          ? err.response.data.error
          : "KI-Vorschlag fehlgeschlagen.";
      setMessage(msg);
    },
  });

  const saveMut = useMutation({
    mutationFn: async () => {
      if (mode === "edit" && editingId) {
        return api.updateWorkflow(editingId, form);
      }
      return api.createWorkflow(form);
    },
    onSuccess: (saved) => {
      void queryClient.invalidateQueries({ queryKey });
      setEditingId(saved.id);
      setMode("edit");
      setTestsPassed(
        Boolean(
          saved.last_test_passed_at &&
            saved.last_test_passed_total > 0 &&
            saved.last_test_passed_count === saved.last_test_passed_total
        )
      );
      setMessage("Workflow gespeichert.");
    },
    onError: () => setMessage("Speichern fehlgeschlagen."),
  });

  const deleteMut = useMutation({
    mutationFn: () => api.deleteWorkflow(editingId!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
      setMode("list");
      setEditingId(null);
      setForm(EMPTY_FORM);
      setMessage("Workflow gelöscht.");
    },
  });

  const previewMut = useMutation({
    mutationFn: async () => {
      const attachments = await filesToAttachments(previewFiles);
      return api.previewWorkflow(editingId!, {
        subject: previewSubject,
        body: previewBody,
        attachments,
      });
    },
    onSuccess: (res) => {
      setPreviewResult(res.success ? res.result : null);
      setPreviewError(res.success ? null : res.error ?? "Unbekannter Fehler");
      setPreviewNotice(res.notice ?? null);
    },
  });

  const testsMut = useMutation({
    mutationFn: () => api.runWorkflowTests(editingId!),
    onSuccess: (res) => {
      const ok = res.total > 0 && res.passed === res.total;
      setTestsPassed(ok);
      setMessage(
        ok
          ? `Test-Suite bestanden (${res.passed}/${res.total}). Live-Aktivierung möglich.`
          : `Test-Suite: ${res.passed}/${res.total} — Live-Aktivierung gesperrt.`
      );
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setAssistDescription("");
    setAssistFiles(null);
    setPreviewResult(null);
    setPreviewError(null);
    setMessage(null);
    setMode("create");
  };

  const openEdit = async (id: string) => {
    const wf = await api.fetchWorkflow(id);
    setForm({
      label: wf.label,
      slug: wf.slug,
      description: wf.description,
      search_hints: wf.search_hints,
      importance: wf.importance,
      required_fields: wf.required_fields,
      optional_fields: wf.optional_fields,
      extraction_schema: wf.extraction_schema,
      classify_prompt: wf.classify_prompt,
      extract_prompt: wf.extract_prompt,
      draft_prompt: wf.draft_prompt,
      few_shot_examples: wf.few_shot_examples,
      test_emails: wf.test_emails,
      match_rules: wf.match_rules,
      llm_provider: wf.llm_provider,
      supports_multimodal: wf.supports_multimodal,
      multimodal_prompt: wf.multimodal_prompt,
      enabled: wf.enabled,
      sandbox_only: wf.sandbox_only,
      priority: wf.priority,
    });
    setEditingId(id);
    setMode("edit");
    setTestsPassed(
      Boolean(
        wf.last_test_passed_at &&
          wf.last_test_passed_total > 0 &&
          wf.last_test_passed_count === wf.last_test_passed_total
      )
    );
    setMessage(null);
    if (wf.test_emails[0]) {
      setPreviewSubject(wf.test_emails[0].subject);
      setPreviewBody(wf.test_emails[0].body);
    }
  };

  if (!adminAccountId && !isPlatformAdmin) {
    return (
      <Card>
        <p className="text-sm text-slate-600">
          Workflow-Verwaltung ist nur für Plattform-Administratoren verfügbar
          (Menü Admin → Workflows, Mandant wählen).
        </p>
      </Card>
    );
  }

  const pageSubtitle =
    subtitle ??
    (adminAccountId
      ? "Workflows dieses Mandanten — Live-Routing wenn aktiviert und Tests grün."
      : "Eigene Regeln und Prompts — Live-Routing wenn aktiviert und Tests grün.");

  if (mode === "list") {
    return (
      <WorkflowListPanel
        pageSubtitle={pageSubtitle}
        isLoading={isLoading}
        items={list?.items ?? []}
        onCreate={openCreate}
        onEdit={openEdit}
      />
    );
  }

  return (
    <WorkflowEditorPanel
      mode={mode}
      form={form}
      onFormChange={setForm}
      message={message}
      testsPassed={testsPassed}
      editingId={editingId}
      assistDescription={assistDescription}
      onAssistDescriptionChange={setAssistDescription}
      assistFiles={assistFiles}
      onAssistFilesChange={setAssistFiles}
      geminiStatus={geminiStatus}
      suggestMut={suggestMut}
      saveMut={saveMut}
      deleteMut={deleteMut}
      previewMut={previewMut}
      testsMut={testsMut}
      previewSubject={previewSubject}
      onPreviewSubjectChange={setPreviewSubject}
      previewBody={previewBody}
      onPreviewBodyChange={setPreviewBody}
      onPreviewFilesChange={setPreviewFiles}
      previewResult={previewResult}
      previewError={previewError}
      previewNotice={previewNotice}
      onBack={() => setMode("list")}
    />
  );
}
