import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createProperty,
  fetchProperties,
  fetchPropertyHistory,
  fetchPropertyRecipients,
  fetchPropertySuggestions,
  savePropertyRecipients,
} from "@/lib/api/properties";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";
import {
  normalizePropertyRecipientItem,
} from "@/lib/api/properties";
import type { PropertyRecipientItem } from "@/lib/types/api";
import {
  DEFAULT_EMPLOYEE_WHATSAPP_LOCALE,
  type EmployeeWhatsAppLocale,
} from "@/lib/whatsappLocales";
import { EmployeeWhatsAppField } from "@/shared/ui/EmployeeWhatsAppField";

export function PropertiesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const year = new Date().getFullYear();

  const { data: recipients, isLoading } = useQuery({
    queryKey: ["property-recipients"],
    queryFn: fetchPropertyRecipients,
  });
  const { data: properties } = useQuery({
    queryKey: ["properties", year],
    queryFn: () => fetchProperties(year),
  });
  const { data: suggestions } = useQuery({
    queryKey: ["property-suggestions"],
    queryFn: () => fetchPropertySuggestions(15),
  });
  const { data: history } = useQuery({
    queryKey: ["property-history"],
    queryFn: () => fetchPropertyHistory({ limit: 20 }),
  });

  const [propertyRows, setPropertyRows] = useState<PropertyRecipientItem[]>([]);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [adoptMessage, setAdoptMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!recipients) return;
    setPropertyRows(
      recipients.items.length > 0
        ? recipients.items.map(normalizePropertyRecipientItem)
        : [
            {
              property_name: "",
              employees: [
                { phone_e164: "", locale: DEFAULT_EMPLOYEE_WHATSAPP_LOCALE },
              ],
            },
          ]
    );
  }, [recipients]);

  const saveMut = useMutation({
    mutationFn: () =>
      savePropertyRecipients(
        propertyRows
          .filter((row) => row.property_name.trim())
          .map((row) => ({
            property_name: row.property_name.trim(),
            employees: row.employees
              .map((employee) => ({
                phone_e164: employee.phone_e164.trim(),
                locale: employee.locale || DEFAULT_EMPLOYEE_WHATSAPP_LOCALE,
              }))
              .filter((employee) => employee.phone_e164),
          }))
      ),
    onSuccess: () => {
      setSaveMessage("Unterkünfte gespeichert.");
      void queryClient.invalidateQueries({ queryKey: ["property-recipients"] });
    },
    onError: () => setSaveMessage("Speichern fehlgeschlagen."),
  });

  const adoptMut = useMutation({
    mutationFn: (name: string) =>
      createProperty({ name, from_suggestion: true }),
    onSuccess: (created) => {
      setAdoptMessage("Unterkunft angelegt.");
      void queryClient.invalidateQueries({ queryKey: ["property-suggestions"] });
      void queryClient.invalidateQueries({ queryKey: ["properties"] });
      navigate(`/properties/${created.property_id}`);
    },
    onError: () => setAdoptMessage("Anlegen fehlgeschlagen."),
  });

  function updatePropertyRow(
    index: number,
    field: "property_name" | "phone" | "locale",
    value: string
  ) {
    setPropertyRows((rows) =>
      rows.map((row, i) => {
        if (i !== index) return row;
        if (field === "property_name") return { ...row, property_name: value };
        const employees = row.employees.length
          ? [...row.employees]
          : [{ phone_e164: "", locale: DEFAULT_EMPLOYEE_WHATSAPP_LOCALE }];
        if (field === "phone") {
          employees[0] = { ...employees[0], phone_e164: value };
        } else {
          employees[0] = {
            ...employees[0],
            locale: value as EmployeeWhatsAppLocale,
          };
        }
        return { ...row, employees };
      })
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">Unterkünfte</h2>
        <p className="text-sm text-slate-500">
          Profile, WhatsApp-Empfänger, Statistiken und KI-Vorschläge aus Buchungs-Mails.
        </p>
      </div>

      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-medium">Unterkünfte ({year})</h3>
        </div>
        {(properties?.items.length ?? 0) === 0 ? (
          <p className="text-sm text-slate-500">Noch keine Unterkünfte angelegt.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Name</th>
                  <th className="py-2 pr-4">Tage</th>
                  <th className="py-2 pr-4">Umsatz</th>
                  <th className="py-2 pr-4">Buchungen</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {properties!.items.map((p) => (
                  <tr key={p.property_id} className="border-b">
                    <td className="py-2 pr-4 font-medium">{p.name}</td>
                    <td className="py-2 pr-4">{p.stats?.booked_days ?? 0}</td>
                    <td className="py-2 pr-4">
                      {(p.stats?.revenue ?? 0).toLocaleString("de-DE", {
                        style: "currency",
                        currency: "EUR",
                      })}
                    </td>
                    <td className="py-2 pr-4">{p.stats?.booking_count ?? 0}</td>
                    <td className="py-2 text-right">
                      <Link
                        to={`/properties/${p.property_id}`}
                        className="text-indigo-600 hover:underline"
                      >
                        Profil
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {(properties?.items ?? []).some(
          (p) => (p.stats?.incomplete_data_count ?? 0) > 0
        ) && (
          <p className="mt-2 text-xs text-amber-600">
            Einige Buchungen haben unvollständige Preis- oder Datumsdaten in der Extraktion.
          </p>
        )}
      </Card>

      <Card className="space-y-4">
        <h3 className="font-medium">Mitarbeiter-Empfänger</h3>
        <p className="text-sm text-slate-500">
          Sprache gilt nur für Reinigungs-Nachrichten an Putzfrau/Mitarbeiter. Storno,
          Änderungen und Gastnachrichten bleiben auf Deutsch.
        </p>
        {isLoading ? (
          <p className="text-slate-500">Lade…</p>
        ) : (
          propertyRows.map((row, index) => (
            <div key={index} className="grid gap-2 sm:grid-cols-2">
              <Input
                placeholder="Unterkunftsname"
                value={row.property_name}
                onChange={(e) =>
                  updatePropertyRow(index, "property_name", e.target.value)
                }
              />
              <EmployeeWhatsAppField
                phone={row.employees[0]?.phone_e164 ?? ""}
                locale={row.employees[0]?.locale ?? DEFAULT_EMPLOYEE_WHATSAPP_LOCALE}
                onPhoneChange={(phone) => updatePropertyRow(index, "phone", phone)}
                onLocaleChange={(locale) => updatePropertyRow(index, "locale", locale)}
              />
            </div>
          ))
        )}
        <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
          Speichern
        </Button>
        {saveMessage && <p className="text-sm text-slate-600">{saveMessage}</p>}
      </Card>

      <Card>
        <h3 className="mb-2 font-medium">KI-Vorschläge (neue Namen)</h3>
        {(suggestions?.items.length ?? 0) === 0 ? (
          <p className="text-sm text-slate-500">Keine Vorschläge.</p>
        ) : (
          <ul className="text-sm space-y-2">
            {suggestions!.items.map((s) => (
              <li
                key={s.property_name}
                className="flex flex-wrap items-center justify-between gap-2"
              >
                <span>
                  {s.property_name}{" "}
                  <span className="text-slate-400">({s.mail_count} Mails)</span>
                </span>
                <Button
                  variant="secondary"
                  className="py-1 px-3"
                  disabled={adoptMut.isPending}
                  onClick={() => adoptMut.mutate(s.property_name)}
                >
                  Übernehmen
                </Button>
              </li>
            ))}
          </ul>
        )}
        {adoptMessage && <p className="mt-2 text-sm text-slate-600">{adoptMessage}</p>}
      </Card>

      <Card>
        <h3 className="mb-2 font-medium">Historie (letzte Buchungs-Mails)</h3>
        <ul className="text-sm space-y-2 max-h-64 overflow-y-auto">
          {(history?.items ?? []).map((h) => (
            <li key={h.correlation_id} className="border-b pb-1">
              <span className="font-medium">{h.property_name ?? "—"}</span> —{" "}
              {h.subject}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
