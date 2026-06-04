import type { AdminLlmPreviewStep } from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

export interface AdminLlmPreviewCardProps {
  previewStep: AdminLlmPreviewStep;
  onPreviewStepChange: (step: AdminLlmPreviewStep) => void;
  previewSubject: string;
  onPreviewSubjectChange: (value: string) => void;
  previewBody: string;
  onPreviewBodyChange: (value: string) => void;
  previewResult: string | null;
  previewError: string | null;
  previewPending: boolean;
  onRunPreview: () => void;
}

export function AdminLlmPreviewCard({
  previewStep,
  onPreviewStepChange,
  previewSubject,
  onPreviewSubjectChange,
  previewBody,
  onPreviewBodyChange,
  previewResult,
  previewError,
  previewPending,
  onRunPreview,
}: AdminLlmPreviewCardProps) {
  return (
    <Card className="space-y-4">
      <h3 className="font-medium text-slate-900">Preview (Dry-Run)</h3>
      <p className="text-xs text-slate-500">
        Keine echten Mail-Inhalte — nur der Beispieltext unten wird verarbeitet.
      </p>
      <label className="block text-sm text-slate-600">
        Schritt
        <select
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={previewStep}
          onChange={(e) => onPreviewStepChange(e.target.value as AdminLlmPreviewStep)}
        >
          <option value="classify">Klassifikation</option>
          <option value="extract">Extraktion</option>
        </select>
      </label>
      <label className="block text-sm text-slate-600">
        Betreff
        <Input
          className="mt-1"
          value={previewSubject}
          onChange={(e) => onPreviewSubjectChange(e.target.value)}
        />
      </label>
      <label className="block text-sm text-slate-600">
        Mail-Text
        <textarea
          className="mt-1 min-h-[100px] w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={previewBody}
          onChange={(e) => onPreviewBodyChange(e.target.value)}
        />
      </label>
      <Button
        variant="secondary"
        disabled={previewPending}
        onClick={onRunPreview}
      >
        Preview ausführen
      </Button>
      {previewError && (
        <div
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
          role="alert"
        >
          <p className="font-medium">Preview fehlgeschlagen</p>
          <p className="mt-1 whitespace-pre-wrap">{previewError}</p>
        </div>
      )}
      {previewResult && (
        <pre className="max-h-48 overflow-auto rounded border border-emerald-200 bg-emerald-50 p-3 text-xs text-slate-800">
          {previewResult}
        </pre>
      )}
    </Card>
  );
}
