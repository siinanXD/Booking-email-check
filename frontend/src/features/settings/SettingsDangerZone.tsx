import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

export interface SettingsDangerZoneProps {
  wipeConfirm: string;
  onWipeConfirmChange: (value: string) => void;
  onWipe: () => void;
  wipePending: boolean;
}

export function SettingsDangerZone({
  wipeConfirm,
  onWipeConfirmChange,
  onWipe,
  wipePending,
}: SettingsDangerZoneProps) {
  return (
    <Card className="space-y-3 border-red-200 bg-red-50">
      <h3 className="font-medium text-red-800">Gefahrenzone</h3>
      <p className="text-sm text-red-700">
        Löscht alle E-Mails, Reviews, Metriken und gespeicherten Einstellungen.
        Login-Benutzer bleiben erhalten.
      </p>
      <Input
        value={wipeConfirm}
        onChange={(e) => onWipeConfirmChange(e.target.value)}
        placeholder='Tippe "ALLE DATEN LOESCHEN" zur Bestätigung'
      />
      <Button
        variant="danger"
        disabled={wipeConfirm !== "ALLE DATEN LOESCHEN" || wipePending}
        onClick={onWipe}
      >
        Alle Daten löschen
      </Button>
    </Card>
  );
}
