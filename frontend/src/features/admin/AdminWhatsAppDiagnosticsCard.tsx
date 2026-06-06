import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  saveAccountWhatsAppTemplates,
  testAccountWhatsApp,
} from "@/lib/api/admin";
import type {
  AdminWhatsAppInfoResponse,
  AdminWhatsAppTestTemplate,
} from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

const TEMPLATE_OPTIONS: { value: AdminWhatsAppTestTemplate; label: string }[] = [
  { value: "hello_world", label: "hello_world (Meta-Standard)" },
  { value: "cleaning_task", label: "Reinigungsauftrag (Mitarbeiter)" },
  { value: "status_notice", label: "Neue Buchung / Status (Host)" },
  { value: "guest_inquiry", label: "Gastanfrage" },
  { value: "support_ticket", label: "Support-Ticket (Plattform-Admin)" },
];

const TEMPLATE_FIELDS: {
  key: keyof AdminWhatsAppInfoResponse["templates"];
  label: string;
}[] = [
  { key: "cleaning_task", label: "Reinigungsauftrag" },
  { key: "status_notice", label: "Neue Buchung / Status" },
  { key: "guest_inquiry", label: "Gastanfrage" },
  { key: "support_ticket", label: "Support-Ticket" },
];

type Props = {
  accountId: string;
  whatsappInfo: AdminWhatsAppInfoResponse | undefined;
  loading: boolean;
};

export function AdminWhatsAppDiagnosticsCard({
  accountId,
  whatsappInfo,
  loading,
}: Props) {
  const queryClient = useQueryClient();
  const [templateLanguage, setTemplateLanguage] = useState("de");
  const [templates, setTemplates] = useState<AdminWhatsAppInfoResponse["templates"]>(
    {}
  );
  const [recipient, setRecipient] = useState("");
  const [template, setTemplate] = useState<AdminWhatsAppTestTemplate>("hello_world");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [waResult, setWaResult] = useState<string | null>(null);

  useEffect(() => {
    if (!whatsappInfo) return;
    setTemplateLanguage(whatsappInfo.template_language || "de");
    setTemplates(whatsappInfo.templates);
    if (!recipient && whatsappInfo.test_recipient) {
      setRecipient(whatsappInfo.test_recipient);
    }
  }, [whatsappInfo, recipient]);

  const saveMut = useMutation({
    mutationFn: () =>
      saveAccountWhatsAppTemplates(accountId, {
        template_language: templateLanguage,
        template_cleaning_task: templates.cleaning_task,
        template_status_notice: templates.status_notice,
        template_guest_inquiry: templates.guest_inquiry,
        template_support_ticket: templates.support_ticket,
      }),
    onSuccess: () => {
      setSaveMessage("Template-Namen gespeichert.");
      void queryClient.invalidateQueries({
        queryKey: ["admin-whatsapp-info", accountId],
      });
    },
    onError: () => setSaveMessage("Speichern fehlgeschlagen."),
  });

  const waTestMut = useMutation({
    mutationFn: () =>
      testAccountWhatsApp(accountId, {
        recipient_e164: recipient.trim() || undefined,
        template,
      }),
    onSuccess: (res) => {
      setWaResult(
        res.success
          ? `OK — Template ${res.template_name ?? res.template} (ID: ${res.provider_message_id ?? "—"})`
          : `Fehler: ${res.error ?? "Unbekannt"}`
      );
    },
    onError: () => setWaResult("WhatsApp-Test fehlgeschlagen."),
  });

  return (
    <Card className="space-y-4">
      <h2 className="text-lg font-medium text-slate-900">WhatsApp</h2>
      {loading && (
        <p className="text-sm text-slate-500">Lade WhatsApp-Konfiguration…</p>
      )}
      {whatsappInfo && (
        <>
          <p className="text-sm text-slate-600">
            Aktiv: {whatsappInfo.whatsapp_enabled ? "ja" : "nein"} · Token:{" "}
            {whatsappInfo.access_token_configured ? "hinterlegt" : "fehlt"} · Phone
            ID: {whatsappInfo.phone_number_id || "—"}
          </p>

          <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50/80 p-4">
            <h3 className="text-sm font-medium text-slate-900">
              Meta-Template-Namen (genehmigt in Meta Business Manager)
            </h3>
            <label className="block text-sm text-slate-600">
              Sprache
              <Input
                className="mt-1"
                value={templateLanguage}
                onChange={(e) => setTemplateLanguage(e.target.value)}
                placeholder="de"
              />
            </label>
            {TEMPLATE_FIELDS.map(({ key, label }) => (
              <label key={key} className="block text-sm text-slate-600">
                {label}
                <Input
                  className="mt-1 font-mono text-xs"
                  value={templates[key] ?? ""}
                  onChange={(e) =>
                    setTemplates((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                />
              </label>
            ))}
            <Button
              variant="secondary"
              disabled={saveMut.isPending}
              onClick={() => saveMut.mutate()}
            >
              Template-Namen speichern
            </Button>
            {saveMessage && (
              <p
                className={`text-sm ${saveMessage.includes("gespeichert") ? "text-green-700" : "text-red-600"}`}
              >
                {saveMessage}
              </p>
            )}
          </div>

          <label className="block text-sm text-slate-600">
            Test-Template
            <select
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={template}
              onChange={(e) =>
                setTemplate(e.target.value as AdminWhatsAppTestTemplate)
              }
            >
              {TEMPLATE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm text-slate-600">
            Test-Empfänger (E.164)
            <Input
              className="mt-1"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder={whatsappInfo.test_recipient || "+491701234567"}
            />
          </label>
          <Button
            variant="secondary"
            disabled={waTestMut.isPending}
            onClick={() => waTestMut.mutate()}
          >
            WhatsApp testen
          </Button>
          {waResult && (
            <p
              className={`text-sm ${waResult.startsWith("OK") ? "text-green-700" : "text-red-600"}`}
            >
              {waResult}
            </p>
          )}
        </>
      )}
    </Card>
  );
}
