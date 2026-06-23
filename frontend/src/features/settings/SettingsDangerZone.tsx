import { useState } from "react";
import { TriangleAlert, Trash2 } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";

export interface SettingsDangerZoneProps {
  onWipe: () => Promise<unknown>;
  wipePending: boolean;
}

export function SettingsDangerZone({ onWipe, wipePending }: SettingsDangerZoneProps) {
  const [open, setOpen] = useState(false);

  const handleConfirm = async () => {
    try {
      await onWipe();
      setOpen(false);
    } catch {
      // Failure is surfaced via the global error toast — keep the dialog open.
    }
  };

  return (
    <div className="rounded-xl border border-red-200/80 bg-red-50/50 p-5 space-y-4">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-red-100 text-red-600">
          <TriangleAlert size={16} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-red-800">Gefahrenzone</h3>
          <p className="mt-0.5 text-xs text-red-600">
            Löscht alle E-Mails, Reviews, Metriken und gespeicherten Einstellungen.
            Login-Benutzer bleiben erhalten.
          </p>
        </div>
      </div>
      <Button variant="danger" size="sm" onClick={() => setOpen(true)}>
        <Trash2 size={14} />
        Alle Daten löschen
      </Button>

      <ConfirmDialog
        open={open}
        title="Wirklich alle Daten löschen?"
        message="Diese Aktion kann nicht rückgängig gemacht werden. Alle E-Mails, Reviews, Metriken und Einstellungen werden dauerhaft entfernt."
        confirmLabel="Endgültig löschen"
        tone="danger"
        loading={wipePending}
        requirePhrase="ALLE DATEN LOESCHEN"
        onConfirm={handleConfirm}
        onCancel={() => !wipePending && setOpen(false)}
      />
    </div>
  );
}
