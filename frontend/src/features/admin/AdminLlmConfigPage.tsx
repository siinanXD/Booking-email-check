import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  fetchAdminLlmConfig,
  previewAdminLlmConfig,
  updateAdminLlmConfig,
} from "@/lib/api/admin";
import type { AdminLlmPreviewStep } from "@/lib/types/api";
import { AdminLlmPreviewCard } from "@/features/admin/AdminLlmPreviewCard";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { PromptHistoryPanel } from "@/features/admin/components/PromptHistoryPanel";
import { LlmTemperatureChart } from "@/features/admin/components/charts/LlmTemperatureChart";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

type PromptTab = "classify" | "extract" | "draft";

const TABS: { id: PromptTab; label: string }[] = [
  { id: "classify", label: "Klassifikation" },
  { id: "extract", label: "Extraktion" },
  { id: "draft", label: "Antwortentwurf" },
];

export function AdminLlmConfigPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<PromptTab>("classify");
  const [classifyTemp, setClassifyTemp] = useState(0);
  const [extractTemp, setExtractTemp] = useState(0);
  const [draftTemp, setDraftTemp] = useState(0);
  const [similarityTopK, setSimilarityTopK] = useState(3);
  const [classifyOverride, setClassifyOverride] = useState("");
  const [extractOverride, setExtractOverride] = useState("");
  const [draftOverride, setDraftOverride] = useState("");
  const [previewSubject, setPreviewSubject] = useState("Neue Buchung AB123");
  const [previewBody, setPreviewBody] = useState(
    "Guten Tag, ich habe eine Buchung AB123 vom 12.06. bis 15.06."
  );
  const [previewStep, setPreviewStep] = useState<AdminLlmPreviewStep>("classify");
  const [previewResult, setPreviewResult] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin-llm-config"],
    queryFn: fetchAdminLlmConfig,
  });

  useEffect(() => {
    if (!data) return;
    setClassifyTemp(data.classify_temperature);
    setExtractTemp(data.extract_temperature);
    setDraftTemp(data.draft_temperature);
    setSimilarityTopK(data.similarity_top_k);
    setClassifyOverride(data.classify_prompt_override ?? "");
    setExtractOverride(data.extract_prompt_override ?? "");
    setDraftOverride(data.draft_prompt_override ?? "");
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () =>
      updateAdminLlmConfig({
        classify_temperature: classifyTemp,
        extract_temperature: extractTemp,
        draft_temperature: draftTemp,
        similarity_top_k: similarityTopK,
        classify_prompt_override: classifyOverride || null,
        extract_prompt_override: extractOverride || null,
        draft_prompt_override: draftOverride || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin-llm-config"] });
      void queryClient.invalidateQueries({
        queryKey: ["admin-llm-prompt-history"],
      });
      setSaveMessage("Konfiguration gespeichert.");
    },
    onError: () => setSaveMessage("Speichern fehlgeschlagen."),
  });

  const previewMut = useMutation({
    mutationFn: () =>
      previewAdminLlmConfig({
        step: previewStep,
        subject: previewSubject,
        body: previewBody,
      }),
    onSuccess: (res) => {
      setPreviewResult(res.success ? res.result : null);
      setPreviewError(res.success ? null : res.error ?? "Unbekannter Fehler");
    },
    onError: () => {
      setPreviewResult(null);
      setPreviewError("Preview-Anfrage fehlgeschlagen (Netzwerk oder Server).");
    },
  });

  if (isLoading || !data) {
    return <p className="text-sm text-slate-500">Lade LLM-Konfiguration…</p>;
  }

  const defaultPrompt =
    tab === "classify"
      ? data.default_classify_prompt
      : tab === "extract"
        ? data.default_extract_prompt
        : data.default_draft_prompt;

  const overrideValue =
    tab === "classify"
      ? classifyOverride
      : tab === "extract"
        ? extractOverride
        : draftOverride;

  const setOverride =
    tab === "classify"
      ? setClassifyOverride
      : tab === "extract"
        ? setExtractOverride
        : setDraftOverride;

  const temperature =
    tab === "classify" ? classifyTemp : tab === "extract" ? extractTemp : draftTemp;

  const setTemperature =
    tab === "classify"
      ? setClassifyTemp
      : tab === "extract"
        ? setExtractTemp
        : setDraftTemp;

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="LLM-Konfiguration"
        description="Steuere plattformweit Temperatur, Similarity Top-K und optionale Prompt-Texte für Klassifikation, Extraktion und Antwortentwurf. Leere Prompt-Felder nutzen weiterhin die Markdown-Dateien im Repository."
        impact="Nach dem Speichern gelten neue Werte sofort für alle Mandanten und jede neu verarbeitete Mail — ohne Neustart. Top-K steuert, wie viele ähnliche Fälle beim Entwurf herangezogen werden; höhere Temperatur kann Kosten und Varianz erhöhen."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <LlmTemperatureChart
          classify={classifyTemp}
          extract={extractTemp}
          draft={draftTemp}
        />
        <Card className="space-y-3">
          <h3 className="font-medium text-slate-900">Similarity Top-K</h3>
          <p className="text-sm text-slate-600">
            Aktuell: <strong>{similarityTopK}</strong> ähnliche Fälle pro Entwurf
          </p>
          <p className="text-xs text-slate-500">
            Mehr Top-K = mehr Kontext aus der Vektorsuche, oft höhere Token-Kosten.
            Weniger = schneller und günstiger, aber weniger historischer Kontext.
          </p>
        </Card>
      </div>

      <Card className="space-y-4">
        <h2 className="text-lg font-medium text-slate-900">Prompts & Parameter</h2>
        {data.updated_at && (
          <p className="text-xs text-slate-500">
            Zuletzt geändert: {new Date(data.updated_at).toLocaleString("de-DE")}
          </p>
        )}
        <label className="block text-sm text-slate-600">
          Ähnliche Fälle (Similarity Top-K)
          <Input
            className="mt-1 w-24"
            type="number"
            min={1}
            max={20}
            value={similarityTopK}
            onChange={(e) => setSimilarityTopK(Number(e.target.value))}
          />
        </label>

        <div className="flex gap-2 border-b border-slate-200 pb-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`rounded-lg px-3 py-1.5 text-sm ${
                tab === t.id
                  ? "bg-indigo-100 font-medium text-indigo-800"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <label className="block text-sm text-slate-600">
          Temperatur ({tab})
          <input
            className="mt-2 w-full"
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
          />
          <span className="text-xs text-slate-500">{temperature.toFixed(1)}</span>
        </label>

        <details className="text-sm">
          <summary className="cursor-pointer text-slate-600">Standard-Prompt anzeigen</summary>
          <pre className="mt-2 max-h-48 overflow-auto rounded bg-slate-50 p-3 text-xs text-slate-700">
            {defaultPrompt}
          </pre>
        </details>

        <label className="block text-sm text-slate-600">
          Prompt-Override (Markdown, optional)
          <textarea
            className="mt-1 min-h-[200px] w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs"
            value={overrideValue}
            onChange={(e) => setOverride(e.target.value)}
            placeholder="Leer lassen für Standard-Prompt aus Datei…"
          />
        </label>

        <PromptHistoryPanel
          promptType={tab}
          currentText={overrideValue}
          onRestore={(text) => setOverride(text)}
        />

        <div className="flex gap-2">
          <Button
            disabled={saveMut.isPending}
            onClick={() => {
              setSaveMessage(null);
              saveMut.mutate();
            }}
          >
            Speichern
          </Button>
          {saveMessage && (
            <p className="self-center text-sm text-slate-600">{saveMessage}</p>
          )}
        </div>
      </Card>

      <AdminLlmPreviewCard
        previewStep={previewStep}
        onPreviewStepChange={setPreviewStep}
        previewSubject={previewSubject}
        onPreviewSubjectChange={setPreviewSubject}
        previewBody={previewBody}
        onPreviewBodyChange={setPreviewBody}
        previewResult={previewResult}
        previewError={previewError}
        previewPending={previewMut.isPending}
        onRunPreview={() => {
          setPreviewResult(null);
          setPreviewError(null);
          previewMut.mutate();
        }}
      />
    </div>
  );
}
