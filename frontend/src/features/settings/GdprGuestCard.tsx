import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Download, ShieldCheck, Trash2, UserSearch } from "lucide-react";
import {
  deleteGuest,
  exportGuest,
  getGuestConsent,
  setGuestConsent,
} from "@/lib/api/guests";
import type { GuestConsent, GuestExportResponse } from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { Input } from "@/shared/ui/Input";
import { Toggle } from "@/shared/ui/Toggle";
import { toast } from "@/shared/feedback/toastStore";

function downloadJson(data: GuestExportResponse) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `gast-export-${data.email}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function GdprGuestCard() {
  const [email, setEmail] = useState("");
  const [activeEmail, setActiveEmail] = useState<string | null>(null);
  const [exportData, setExportData] = useState<GuestExportResponse | null>(null);
  const [consent, setConsent] = useState<GuestConsent | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const exportMut = useMutation({
    mutationFn: () => exportGuest(email.trim()),
    meta: { skipGlobalError: true },
    onSuccess: (data) => {
      setActiveEmail(data.email);
      setExportData(data);
      setConsent(data.consent);
      toast.success(`${data.mail_count} Mail(s) gefunden.`);
    },
    onError: () => toast.error("Gast nicht gefunden oder Export fehlgeschlagen."),
  });

  const consentMut = useMutation({
    mutationFn: (next: boolean) => setGuestConsent(activeEmail!, next),
    onSuccess: (data) => {
      setConsent(data);
      toast.success("Einwilligung aktualisiert.");
    },
  });

  const refreshConsentMut = useMutation({
    mutationFn: () => getGuestConsent(activeEmail!),
    onSuccess: (data) => setConsent(data),
  });

  const deleteMut = useMutation({
    mutationFn: () => deleteGuest(activeEmail!),
    onSuccess: (res) => {
      const total = Object.values(res.deleted).reduce((a, b) => a + b, 0);
      toast.success(`Gast-Daten gelöscht (${total} Dokumente).`);
      setConfirmOpen(false);
      setActiveEmail(null);
      setExportData(null);
      setConsent(null);
      setEmail("");
    },
  });

  const onSearch = () => {
    if (!email.trim()) return;
    exportMut.mutate();
  };

  return (
    <Card className="space-y-5">
      <div className="flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-infobg text-infotext">
          <ShieldCheck size={18} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-ink">DSGVO – Gastdaten</h3>
          <p className="text-xs text-muted">
            Daten eines Gasts exportieren, Einwilligung verwalten oder löschen.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch()}
          placeholder="gast@example.com"
          className="flex-1"
        />
        <Button
          variant="secondary"
          onClick={onSearch}
          loading={exportMut.isPending}
          disabled={!email.trim()}
        >
          <UserSearch size={15} />
          Daten exportieren
        </Button>
      </div>

      {exportData && activeEmail && (
        <div className="space-y-4 rounded-xl border border-border bg-surface2/40 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-ink">{exportData.email}</p>
              <p className="text-xs text-muted font-numeric">
                {exportData.mail_count} Mail(s) · ID {exportData.guest_id}
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => downloadJson(exportData)}
            >
              <Download size={14} />
              JSON herunterladen
            </Button>
          </div>

          <Toggle
            label="WhatsApp-Einwilligung"
            checked={consent?.whatsapp_consent ?? false}
            disabled={consentMut.isPending || refreshConsentMut.isPending}
            onChange={(on) => consentMut.mutate(on)}
          />
          {consent?.consent_at && (
            <p className="text-xs text-faint">
              Einwilligung seit{" "}
              <span className="font-numeric">{consent.consent_at}</span>
            </p>
          )}

          <div className="border-t border-border pt-3">
            <Button
              variant="danger"
              size="sm"
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 size={14} />
              Gast-Daten löschen
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        tone="danger"
        title="Gast-Daten unwiderruflich löschen"
        message="Alle Mails, Extraktionen, Reviews, Embeddings und die Einwilligung dieses Gasts werden gelöscht. Dieser Vorgang kann nicht rückgängig gemacht werden."
        confirmLabel="Endgültig löschen"
        requirePhrase={activeEmail ?? undefined}
        loading={deleteMut.isPending}
        onConfirm={() => deleteMut.mutate()}
        onCancel={() => setConfirmOpen(false)}
      />
    </Card>
  );
}
