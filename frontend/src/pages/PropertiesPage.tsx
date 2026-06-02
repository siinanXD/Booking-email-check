import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { fetchSettings, saveSettings } from "@/api/settings";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import type { PropertyRecipientItem } from "@/types/api";

export function PropertiesPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
  });

  const [propertyRows, setPropertyRows] = useState<PropertyRecipientItem[]>([]);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    setPropertyRows(
      data.property_recipients.length > 0
        ? data.property_recipients
        : [{ property_name: "", phones: [""] }]
    );
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () =>
      saveSettings({
        property_recipients: propertyRows
          .filter((row) => row.property_name.trim())
          .map((row) => ({
            property_name: row.property_name.trim(),
            phones: row.phones.map((p) => p.trim()).filter(Boolean),
          })),
      }),
    onSuccess: () => {
      setSaveMessage("Unterkünfte gespeichert.");
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: () => setSaveMessage("Speichern fehlgeschlagen."),
  });

  function updatePropertyRow(
    index: number,
    field: "property_name" | "phones",
    value: string
  ) {
    setPropertyRows((rows) =>
      rows.map((row, i) =>
        i === index
          ? field === "property_name"
            ? { ...row, property_name: value }
            : { ...row, phones: value.split(",").map((p) => p.trim()) }
          : row
      )
    );
  }

  function addPropertyRow() {
    setPropertyRows((rows) => [...rows, { property_name: "", phones: [""] }]);
  }

  function removePropertyRow(index: number) {
    setPropertyRows((rows) =>
      rows.length <= 1 ? rows : rows.filter((_, i) => i !== index)
    );
  }

  if (isLoading) {
    return <p className="text-slate-500">Unterkünfte werden geladen…</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">
          Unterkünfte & Mitarbeiter
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          WhatsApp-Nummern der Putzfrau oder Mitarbeiter pro Unterkunft. Bei
          neuer Buchung (nach Freigabe im Review) erhalten diese Personen eine
          Reinigungs-Aufgabe.
        </p>
      </div>

      <Card className="space-y-4">
        {propertyRows.map((row, index) => (
          <div key={index} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <Input
              placeholder="Unterkunftsname (wie in E-Mails)"
              value={row.property_name}
              onChange={(e) =>
                updatePropertyRow(index, "property_name", e.target.value)
              }
            />
            <Input
              placeholder="WhatsApp-Nummern, kommagetrennt (E.164)"
              value={row.phones.join(", ")}
              onChange={(e) => updatePropertyRow(index, "phones", e.target.value)}
            />
            <Button
              variant="ghost"
              className="text-red-600"
              onClick={() => removePropertyRow(index)}
              disabled={propertyRows.length <= 1}
            >
              Entfernen
            </Button>
          </div>
        ))}
        <div className="flex flex-wrap gap-3">
          <Button variant="ghost" onClick={addPropertyRow}>
            + Unterkunft hinzufügen
          </Button>
          <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            Speichern
          </Button>
        </div>
        {saveMessage && <p className="text-sm text-slate-700">{saveMessage}</p>}
      </Card>
    </div>
  );
}
