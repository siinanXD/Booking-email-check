import type {
  GeminiStatusResponse,
  TenantWorkflowCreateRequest,
  WorkflowImportance,
  WorkflowLlmProvider,
} from "@/lib/types/api";
import { fieldsToText, textToFields } from "@/features/workflows/workflowFormUtils";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

export interface WorkflowEditorFormCardProps {
  form: TenantWorkflowCreateRequest;
  onFormChange: (form: TenantWorkflowCreateRequest) => void;
  testsPassed: boolean;
  geminiStatus: GeminiStatusResponse | undefined;
}

export function WorkflowEditorFormCard({
  form,
  onFormChange,
  testsPassed,
  geminiStatus,
}: WorkflowEditorFormCardProps) {
  const setForm = onFormChange;

  return (
    <Card className="space-y-4">
      <h2 className="font-medium text-slate-900">Grunddaten</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-sm text-slate-600">
          Name
          <Input
            className="mt-1"
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
          />
        </label>
        <label className="block text-sm text-slate-600">
          Slug
          <Input
            className="mt-1 font-mono text-xs"
            value={form.slug ?? ""}
            onChange={(e) => setForm({ ...form, slug: e.target.value })}
          />
        </label>
      </div>
      <label className="block text-sm text-slate-600">
        Beschreibung
        <textarea
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </label>
      <label className="block text-sm text-slate-600">
        Suchhinweise
        <textarea
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={form.search_hints}
          onChange={(e) => setForm({ ...form, search_hints: e.target.value })}
        />
      </label>
      <label className="block text-sm text-slate-600">
        Wichtigkeit
        <select
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={form.importance}
          onChange={(e) =>
            setForm({
              ...form,
              importance: e.target.value as WorkflowImportance,
            })
          }
        >
          <option value="high">Hoch</option>
          <option value="medium">Mittel</option>
          <option value="low">Niedrig</option>
        </select>
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-sm text-slate-600">
          Pflichtfelder (kommagetrennt)
          <Input
            className="mt-1 font-mono text-xs"
            value={fieldsToText(form.required_fields ?? [])}
            onChange={(e) =>
              setForm({ ...form, required_fields: textToFields(e.target.value) })
            }
          />
        </label>
        <label className="block text-sm text-slate-600">
          Optionale Felder
          <Input
            className="mt-1 font-mono text-xs"
            value={fieldsToText(form.optional_fields ?? [])}
            onChange={(e) =>
              setForm({ ...form, optional_fields: textToFields(e.target.value) })
            }
          />
        </label>
      </div>
      <label className="block text-sm text-slate-600">
        LLM-Provider
        <select
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={form.llm_provider ?? "openai"}
          onChange={(e) =>
            setForm({
              ...form,
              llm_provider: e.target.value as WorkflowLlmProvider,
            })
          }
        >
          <option value="openai">OpenAI (Text)</option>
          <option value="gemini">Gemini (Multimodal Sandbox)</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={form.supports_multimodal}
          onChange={(e) => {
            const checked = e.target.checked;
            setForm({
              ...form,
              supports_multimodal: checked,
              llm_provider: checked ? "gemini" : form.llm_provider,
            });
          }}
        />
        Multimodal (Bilder/PDF in Preview/Tests)
      </label>
      {form.llm_provider === "gemini" && geminiStatus && !geminiStatus.available && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          GEMINI_API_KEY fehlt in der Server-.env (Google AI Studio). OpenAI bleibt
          für andere Schritte aktiv; Gemini-Preview schlägt fehl bis der Key gesetzt ist.
        </p>
      )}
      {form.supports_multimodal && (
        <label className="block text-sm text-slate-600">
          Multimodal-Prompt
          <textarea
            className="mt-1 min-h-[80px] w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={form.multimodal_prompt ?? ""}
            onChange={(e) =>
              setForm({ ...form, multimodal_prompt: e.target.value })
            }
            placeholder="z.B. Lies Rechnungsbeträge und Bestellnummern aus Screenshots/PDFs."
          />
        </label>
      )}
      {form.llm_provider === "gemini" && (
        <p className="text-xs text-slate-500">
          Live-Workflows nutzen Gemini nur mit Mail-Text; Anhänge aus echten Mails
          kommen in einer späteren Phase.
        </p>
      )}
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={form.sandbox_only ?? true}
          onChange={(e) => setForm({ ...form, sandbox_only: e.target.checked })}
        />
        Nur Sandbox (empfohlen bis Tests grün)
      </label>
      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={form.enabled ?? false}
          disabled={!testsPassed}
          onChange={(e) =>
            setForm({
              ...form,
              enabled: e.target.checked,
              sandbox_only: e.target.checked ? form.sandbox_only : false,
            })
          }
        />
        Live aktiv (Routing auf eingehende Mails)
      </label>
      {!testsPassed && (
        <p className="text-xs text-amber-700">
          Live-Aktivierung erst nach bestandener Test-Suite möglich.
        </p>
      )}
    </Card>
  );
}
