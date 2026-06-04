import type { UseMutationResult } from "@tanstack/react-query";
import type {
  GeminiStatusResponse,
  TenantWorkflowCreateRequest,
  TenantWorkflowPreviewResponse,
  TenantWorkflowRunTestsResponse,
} from "@/lib/types/api";
import { WorkflowEditorAssistCard } from "@/features/workflows/WorkflowEditorAssistCard";
import { WorkflowEditorFormCard } from "@/features/workflows/WorkflowEditorFormCard";
import { fieldsToText, textToFields } from "@/features/workflows/workflowFormUtils";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

export interface WorkflowEditorPanelProps {
  mode: "create" | "edit";
  form: TenantWorkflowCreateRequest;
  onFormChange: (form: TenantWorkflowCreateRequest) => void;
  message: string | null;
  testsPassed: boolean;
  editingId: string | null;
  assistDescription: string;
  onAssistDescriptionChange: (value: string) => void;
  assistFiles: FileList | null;
  onAssistFilesChange: (files: FileList | null) => void;
  geminiStatus: GeminiStatusResponse | undefined;
  suggestMut: UseMutationResult<unknown, unknown, void, unknown>;
  saveMut: UseMutationResult<unknown, unknown, void, unknown>;
  deleteMut: UseMutationResult<unknown, unknown, void, unknown>;
  previewMut: UseMutationResult<TenantWorkflowPreviewResponse, unknown, void, unknown>;
  testsMut: UseMutationResult<TenantWorkflowRunTestsResponse, unknown, void, unknown>;
  previewSubject: string;
  onPreviewSubjectChange: (value: string) => void;
  previewBody: string;
  onPreviewBodyChange: (value: string) => void;
  onPreviewFilesChange: (files: FileList | null) => void;
  previewResult: string | null;
  previewError: string | null;
  previewNotice: string | null;
  onBack: () => void;
}

export function WorkflowEditorPanel({
  mode,
  form,
  onFormChange,
  message,
  testsPassed,
  editingId,
  assistDescription,
  onAssistDescriptionChange,
  assistFiles,
  onAssistFilesChange,
  geminiStatus,
  suggestMut,
  saveMut,
  deleteMut,
  previewMut,
  testsMut,
  previewSubject,
  onPreviewSubjectChange,
  previewBody,
  onPreviewBodyChange,
  onPreviewFilesChange,
  previewResult,
  previewError,
  previewNotice,
  onBack,
}: WorkflowEditorPanelProps) {
  const setForm = onFormChange;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="secondary" onClick={onBack}>
          ← Zurück
        </Button>
        <h1 className="text-xl font-semibold text-slate-900">
          {mode === "create" ? "Workflow anlegen" : form.label || "Workflow"}
        </h1>
      </div>

      {message && <p className="text-sm text-slate-600">{message}</p>}

      <WorkflowEditorAssistCard
        assistDescription={assistDescription}
        onAssistDescriptionChange={onAssistDescriptionChange}
        assistFiles={assistFiles}
        onAssistFilesChange={onAssistFilesChange}
        geminiStatus={geminiStatus}
        suggestMut={suggestMut}
      />

      <WorkflowEditorFormCard
        form={form}
        onFormChange={onFormChange}
        testsPassed={testsPassed}
        geminiStatus={geminiStatus}
      />

      <Card className="space-y-3">
        <h2 className="font-medium text-slate-900">Prompts</h2>
        <label className="block text-sm text-slate-600">
          Klassifikation
          <textarea
            className="mt-1 min-h-[120px] w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            value={form.classify_prompt}
            onChange={(e) => setForm({ ...form, classify_prompt: e.target.value })}
          />
        </label>
        <label className="block text-sm text-slate-600">
          Extraktion (Platzhalter: {"{subject}"}, {"{body}"})
          <textarea
            className="mt-1 min-h-[160px] w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            value={form.extract_prompt}
            onChange={(e) => setForm({ ...form, extract_prompt: e.target.value })}
          />
        </label>
      </Card>

      <Card className="space-y-3">
        <h2 className="font-medium text-slate-900">Routing-Hinweise (für Phase B)</h2>
        <label className="block text-sm text-slate-600">
          Betreff-Keywords (kommagetrennt)
          <Input
            className="mt-1"
            value={fieldsToText(form.match_rules?.subject_keywords ?? [])}
            onChange={(e) =>
              setForm({
                ...form,
                match_rules: {
                  ...form.match_rules!,
                  subject_keywords: textToFields(e.target.value),
                },
              })
            }
          />
        </label>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button disabled={saveMut.isPending} onClick={() => saveMut.mutate()}>
          Speichern
        </Button>
        {editingId && (
          <>
            <Button
              variant="secondary"
              disabled={previewMut.isPending}
              onClick={() => previewMut.mutate()}
            >
              Preview
            </Button>
            <Button
              variant="secondary"
              disabled={testsMut.isPending}
              onClick={() => testsMut.mutate()}
            >
              Test-Suite
            </Button>
            <Button
              variant="danger"
              disabled={deleteMut.isPending}
              onClick={() => {
                if (window.confirm("Workflow wirklich löschen?")) {
                  deleteMut.mutate();
                }
              }}
            >
              Löschen
            </Button>
          </>
        )}
      </div>

      {editingId && (
        <Card className="space-y-3">
          <h2 className="font-medium text-slate-900">Preview</h2>
          <Input
            value={previewSubject}
            onChange={(e) => onPreviewSubjectChange(e.target.value)}
            placeholder="Betreff"
          />
          <textarea
            className="min-h-[80px] w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={previewBody}
            onChange={(e) => onPreviewBodyChange(e.target.value)}
          />
          {form.supports_multimodal && form.llm_provider === "gemini" && (
            <label className="block text-sm text-slate-600">
              Anhänge (JPEG, PNG, WebP, PDF — max. 5)
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,application/pdf"
                multiple
                className="mt-1 block w-full text-sm"
                onChange={(e) => onPreviewFilesChange(e.target.files)}
              />
            </label>
          )}
          {previewNotice && (
            <p className="text-xs text-amber-800">{previewNotice}</p>
          )}
          {previewError && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {previewError}
            </div>
          )}
          {previewResult && (
            <pre className="max-h-48 overflow-auto rounded bg-emerald-50 p-3 text-xs">
              {previewResult}
            </pre>
          )}
        </Card>
      )}
    </div>
  );
}
