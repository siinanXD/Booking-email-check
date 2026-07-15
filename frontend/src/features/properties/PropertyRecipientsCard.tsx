import { Trash2 } from "lucide-react";
import type { PropertyRecipientItem } from "@/lib/types/api";
import { DEFAULT_EMPLOYEE_WHATSAPP_LOCALE } from "@/lib/whatsappLocales";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";
import { EmployeeWhatsAppField } from "@/shared/ui/EmployeeWhatsAppField";

interface PropertyRecipientsCardProps {
  rows: PropertyRecipientItem[];
  isLoading: boolean;
  saving: boolean;
  onUpdate: (
    index: number,
    field: "property_name" | "phone" | "locale",
    value: string
  ) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
  onSave: () => void;
}

/** Editierbare Liste der WhatsApp-Empfänger (Mitarbeiter) je Unterkunft. */
export function PropertyRecipientsCard({
  rows,
  isLoading,
  saving,
  onUpdate,
  onAdd,
  onRemove,
  onSave,
}: PropertyRecipientsCardProps) {
  return (
    <Card className="space-y-4">
      <div>
        <h3 className="text-base font-semibold text-ink">Mitarbeiter</h3>
        <p className="mt-1 text-sm text-muted">
          WhatsApp-Empfänger je Unterkunft. Die Sprache gilt nur für
          Reinigungs-Nachrichten; Storno, Änderungen und Gastnachrichten bleiben auf
          Deutsch.
        </p>
      </div>
      {isLoading ? (
        <p className="text-sm text-muted">Lade…</p>
      ) : (
        <div className="space-y-2.5">
          {rows.map((row, index) => (
            <div
              key={index}
              className="rounded-xl border border-border2 bg-surface2 p-3"
            >
              <div className="flex items-start gap-2">
                <div className="grid flex-1 gap-2 sm:grid-cols-2">
                  <Input
                    placeholder="Unterkunftsname"
                    aria-label="Unterkunftsname"
                    value={row.property_name}
                    onChange={(e) =>
                      onUpdate(index, "property_name", e.target.value)
                    }
                  />
                  <EmployeeWhatsAppField
                    phone={row.employees[0]?.phone_e164 ?? ""}
                    locale={
                      row.employees[0]?.locale ?? DEFAULT_EMPLOYEE_WHATSAPP_LOCALE
                    }
                    onPhoneChange={(phone) => onUpdate(index, "phone", phone)}
                    onLocaleChange={(locale) => onUpdate(index, "locale", locale)}
                  />
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-0.5"
                  aria-label="Mitarbeiter entfernen"
                  onClick={() => onRemove(index)}
                >
                  <Trash2 size={15} aria-hidden />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button onClick={onSave} loading={saving}>
          Speichern
        </Button>
        <Button variant="secondary" onClick={onAdd}>
          + Mitarbeiter hinzufügen
        </Button>
      </div>
    </Card>
  );
}
