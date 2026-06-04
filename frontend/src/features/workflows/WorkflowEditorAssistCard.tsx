import type { GeminiStatusResponse } from "@/lib/types/api";
import type { UseMutationResult } from "@tanstack/react-query";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";

export interface WorkflowEditorAssistCardProps {
  assistDescription: string;
  onAssistDescriptionChange: (value: string) => void;
  assistFiles: FileList | null;
  onAssistFilesChange: (files: FileList | null) => void;
  geminiStatus: GeminiStatusResponse | undefined;
  suggestMut: UseMutationResult<unknown, unknown, void, unknown>;
}

export function WorkflowEditorAssistCard({
  assistDescription,
  onAssistDescriptionChange,
  assistFiles,
  onAssistFilesChange,
  geminiStatus,
  suggestMut,
}: WorkflowEditorAssistCardProps) {
  return (
    <Card className="space-y-3">
      <h2 className="font-medium text-slate-900">KI-Assistent</h2>
      <p className="text-xs text-slate-500">
        Lade einen Screenshot oder ein PDF einer Beispiel-Mail hoch — Gemini
        schlägt Felder, Routing-Keywords und eine Test-Mail vor. Optional
        ergänzt du eine kurze Beschreibung.
      </p>
      <label className="block text-sm text-slate-600">
        Beispiel-Mail (Screenshot/PDF, max. 5)
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          multiple
          className="mt-1 block w-full text-sm"
          onChange={(e) => onAssistFilesChange(e.target.files)}
        />
      </label>
      <textarea
        className="min-h-[100px] w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        value={assistDescription}
        onChange={(e) => onAssistDescriptionChange(e.target.value)}
        placeholder="Optional: z.B. Tracking-Mails von DHL — Sendungsnummer ist Pflicht."
      />
      {assistFiles?.length && geminiStatus && !geminiStatus.available && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          GEMINI_API_KEY fehlt — Screenshot-Vorschläge sind nur mit Gemini möglich.
        </p>
      )}
      <Button
        variant="secondary"
        disabled={
          (assistDescription.trim().length < 10 && !assistFiles?.length) ||
          suggestMut.isPending ||
          Boolean(assistFiles?.length && geminiStatus && !geminiStatus.available)
        }
        onClick={() => suggestMut.mutate()}
      >
        Vorschlag generieren
      </Button>
    </Card>
  );
}
