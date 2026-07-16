import { Trash2 } from "lucide-react";
import {
  DEFAULT_EMPLOYEE_WHATSAPP_LOCALE,
  normalizeEmployeeLocale,
  type EmployeeWhatsAppLocale,
} from "@/lib/whatsappLocales";
import type { PropertyWhatsAppEmployee } from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { EmployeeLocalePicker } from "@/shared/ui/EmployeeLocalePicker";
import { Input } from "@/shared/ui/Input";

type Props = {
  employees: PropertyWhatsAppEmployee[];
  onChange: (employees: PropertyWhatsAppEmployee[]) => void;
};

const EMPTY: PropertyWhatsAppEmployee = {
  phone_e164: "",
  locale: DEFAULT_EMPLOYEE_WHATSAPP_LOCALE,
  name: "",
  test_mode: false,
};

/**
 * Mitarbeiter einer Unterkunft — mehrere pro Objekt, dieselbe Person kann an
 * mehreren Objekten hängen. Die Nummer ist der Schlüssel: identische Nummer =
 * dieselbe Person, deshalb wirken Name und Testmodus objektübergreifend.
 */
export function PropertyEmployeesCard({ employees, onChange }: Props) {
  const update = (index: number, patch: Partial<PropertyWhatsAppEmployee>) =>
    onChange(employees.map((e, i) => (i === index ? { ...e, ...patch } : e)));

  return (
    <div className="space-y-3 border-t border-slate-100 pt-4">
      <div>
        <p className="text-sm font-medium text-slate-700">Mitarbeiter</p>
        <p className="text-xs text-slate-500">
          Bekommen Putzaufträge für diese Unterkunft per WhatsApp. Die Sprache
          gilt nur für Reinigungs-Aufträge — Stornos &amp; Co. bleiben Deutsch.
        </p>
      </div>

      {employees.length === 0 && (
        <p className="text-sm text-slate-500">
          Noch niemand zugeordnet — für diese Unterkunft wird niemand
          benachrichtigt.
        </p>
      )}

      {employees.map((employee, index) => (
        <div
          key={index}
          className="space-y-2 rounded-lg border border-slate-200 p-3"
        >
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1 space-y-2">
              <Input
                placeholder="Name"
                value={employee.name ?? ""}
                onChange={(e) => update(index, { name: e.target.value })}
              />
              <div className="flex items-center gap-2">
                <Input
                  className="min-w-0 flex-1"
                  placeholder="WhatsApp +49…"
                  value={employee.phone_e164}
                  onChange={(e) =>
                    update(index, { phone_e164: e.target.value })
                  }
                />
                <EmployeeLocalePicker
                  value={normalizeEmployeeLocale(employee.locale)}
                  onChange={(locale: EmployeeWhatsAppLocale) =>
                    update(index, { locale })
                  }
                />
              </div>
            </div>
            <Button
              variant="ghost"
              aria-label="Mitarbeiter entfernen"
              onClick={() => onChange(employees.filter((_, i) => i !== index))}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={Boolean(employee.test_mode)}
              onChange={(e) => update(index, { test_mode: e.target.checked })}
            />
            Testmodus — bekommt keine echte WhatsApp
          </label>
        </div>
      ))}

      <Button
        variant="secondary"
        onClick={() => onChange([...employees, { ...EMPTY }])}
      >
        Mitarbeiter hinzufügen
      </Button>
    </div>
  );
}
