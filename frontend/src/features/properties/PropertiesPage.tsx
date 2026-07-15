import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PropertyPlanLimitDialog } from "@/features/properties/PropertyPlanLimitDialog";
import { PropertyRecipientsCard } from "@/features/properties/PropertyRecipientsCard";
import { PropertySuggestionsCard } from "@/features/properties/PropertySuggestionsCard";
import { getApiErrorCode } from "@/lib/api/errors";
import {
  createProperty,
  fetchProperties,
  fetchPropertyHistory,
  fetchPropertyRecipients,
  fetchPropertySuggestions,
  normalizePropertyRecipientItem,
  savePropertyRecipients,
} from "@/lib/api/properties";
import type { PropertyRecipientItem } from "@/lib/types/api";
import {
  DEFAULT_EMPLOYEE_WHATSAPP_LOCALE,
  type EmployeeWhatsAppLocale,
} from "@/lib/whatsappLocales";
import { EmptyState } from "@/shared/components/EmptyState";
import { toast } from "@/shared/feedback/toastStore";
import { Card } from "@/shared/ui/Card";

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
  const [addedNames, setAddedNames] = useState<Set<string>>(new Set());
  const [upgradeOpen, setUpgradeOpen] = useState(false);

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
      toast.success("Unterkünfte gespeichert.");
      void queryClient.invalidateQueries({ queryKey: ["property-recipients"] });
    },
  });

  const adoptMut = useMutation({
    mutationFn: (name: string) =>
      createProperty({ name, from_suggestion: true }),
    onSuccess: (created) => {
      toast.success("Unterkunft angelegt.");
      void queryClient.invalidateQueries({ queryKey: ["property-suggestions"] });
      void queryClient.invalidateQueries({ queryKey: ["properties"] });
      navigate(`/properties/${created.property_id}`);
    },
    onError: (err: unknown) => {
      if (getApiErrorCode(err) === "plan_limit_reached") {
        setUpgradeOpen(true);
        return;
      }
      toast.error("Unterkunft konnte nicht angelegt werden.");
    },
  });

  function addRowFromSuggestion(name: string) {
    const alreadyInList = propertyRows.some(
      (r) => r.property_name.toLowerCase() === name.toLowerCase()
    );
    if (!alreadyInList) {
      setPropertyRows((rows) => [
        ...rows,
        { property_name: name, employees: [{ phone_e164: "", locale: DEFAULT_EMPLOYEE_WHATSAPP_LOCALE }] },
      ]);
    }
    setAddedNames((prev) => new Set(prev).add(name));
    document.getElementById("empfaenger-liste")?.scrollIntoView({ behavior: "smooth" });
  }

  function addEmptyRow() {
    setPropertyRows((rows) => [
      ...rows,
      { property_name: "", employees: [{ phone_e164: "", locale: DEFAULT_EMPLOYEE_WHATSAPP_LOCALE }] },
    ]);
  }

  function removeRow(index: number) {
    setPropertyRows((rows) => rows.filter((_, i) => i !== index));
  }

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

  const hasIncompleteData = (properties?.items ?? []).some(
    (p) => (p.stats?.incomplete_data_count ?? 0) > 0
  );

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted">
        Profile, WhatsApp-Empfänger, Statistiken und KI-Vorschläge aus deinen
        Buchungs-Mails.
      </p>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-base font-semibold text-ink">Unterkünfte</h3>
          <span className="font-numeric text-xs text-faint">{year}</span>
        </div>
        {(properties?.items.length ?? 0) === 0 ? (
          <EmptyState
            bare
            title="Noch keine Unterkünfte angelegt"
            message="Lege unten eine Unterkunft an oder übernimm einen KI-Vorschlag aus deinen Buchungs-Mails."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-faint">
                  <th className="pb-2 pr-4 font-medium">Name</th>
                  <th className="pb-2 pr-4 text-right font-medium">Tage</th>
                  <th className="pb-2 pr-4 text-right font-medium">Umsatz</th>
                  <th className="pb-2 pr-4 text-right font-medium">Buchungen</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody>
                {properties!.items.map((p) => (
                  <tr
                    key={p.property_id}
                    className="border-b border-border last:border-0"
                  >
                    <td className="py-2.5 pr-4 font-medium text-ink">{p.name}</td>
                    <td className="py-2.5 pr-4 text-right font-numeric text-ink2">
                      {p.stats?.booked_days ?? 0}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-numeric text-ink2">
                      {(p.stats?.revenue ?? 0).toLocaleString("de-DE", {
                        style: "currency",
                        currency: "EUR",
                      })}
                    </td>
                    <td className="py-2.5 pr-4 text-right font-numeric text-ink2">
                      {p.stats?.booking_count ?? 0}
                    </td>
                    <td className="py-2.5 text-right">
                      <Link
                        to={`/properties/${p.property_id}`}
                        className="font-medium text-brandink hover:underline"
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
        {hasIncompleteData && (
          <p className="mt-3 inline-flex rounded-lg bg-warnbg px-2.5 py-1.5 text-xs text-warntext">
            Einige Buchungen haben unvollständige Preis- oder Datumsdaten in der
            Extraktion.
          </p>
        )}
      </Card>

      <div id="empfaenger-liste">
        <PropertyRecipientsCard
          rows={propertyRows}
          isLoading={isLoading}
          saving={saveMut.isPending}
          onUpdate={updatePropertyRow}
          onAdd={addEmptyRow}
          onRemove={removeRow}
          onSave={() => saveMut.mutate()}
        />
      </div>

      <PropertySuggestionsCard
        suggestions={suggestions?.items ?? []}
        addedNames={addedNames}
        adoptPending={adoptMut.isPending}
        onAddToList={addRowFromSuggestion}
        onCreateProfile={(name) => adoptMut.mutate(name)}
      />

      <Card>
        <h3 className="mb-3 text-base font-semibold text-ink">
          Letzte Buchungs-Mails
        </h3>
        <ul className="max-h-64 overflow-y-auto text-sm">
          {(history?.items ?? []).map((h) => (
            <li
              key={h.correlation_id}
              className="flex gap-2 border-b border-border py-2 last:border-0"
            >
              <span className="shrink-0 font-medium text-ink">
                {h.property_name ?? "—"}
              </span>
              <span className="truncate text-muted">{h.subject}</span>
            </li>
          ))}
        </ul>
      </Card>

      <PropertyPlanLimitDialog open={upgradeOpen} onClose={() => setUpgradeOpen(false)} />
    </div>
  );
}
