import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  fetchAccountMailConnection,
  fetchAccountWhatsAppInfo,
  testAccountMailConnection,
} from "@/lib/api/admin";
import { useAllAccounts } from "@/features/admin/useAllAccounts";
import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { AdminWhatsAppDiagnosticsCard } from "@/features/admin/AdminWhatsAppDiagnosticsCard";
import { AdminCleaningDiagnosticsCard } from "@/features/admin/AdminCleaningDiagnosticsCard";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";

export function AdminDiagnosticsPage() {
  const [accountId, setAccountId] = useState("");
  const [mailResult, setMailResult] = useState<{ ok: boolean; message: string } | null>(null);

  const { data: accounts } = useAllAccounts();

  const activeAccounts = useMemo(
    () => accounts?.items.filter((a) => a.status === "active") ?? [],
    [accounts]
  );

  const { data: mailConnection, isLoading: mailLoading } = useQuery({
    queryKey: ["admin-mail-connection", accountId],
    queryFn: () => fetchAccountMailConnection(accountId),
    enabled: Boolean(accountId),
  });

  const { data: whatsappInfo, isLoading: waLoading } = useQuery({
    queryKey: ["admin-whatsapp-info", accountId],
    queryFn: () => fetchAccountWhatsAppInfo(accountId),
    enabled: Boolean(accountId),
  });

  const mailTestMut = useMutation({
    mutationFn: () => testAccountMailConnection(accountId),
    onSuccess: (res) => {
      setMailResult({
        ok: res.success,
        message: res.success
          ? `${res.message}${res.mailbox_count != null ? ` (${res.mailbox_count} Nachrichten)` : ""}`
          : res.message,
      });
    },
    onError: () =>
      setMailResult({ ok: false, message: "Postfach-Test fehlgeschlagen." }),
  });

  function handleAccountChange(id: string) {
    setAccountId(id);
    setMailResult(null);
  }

  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Diagnose: Mail, WhatsApp & Putzplan"
        description="Wähle einen Mandanten und prüfe dessen Verbindungen und Putzplan — du verbindest kein eigenes Postfach. Der Mail-Test prüft IMAP/Outlook mit den Mandanten-Credentials; der WhatsApp-Test sendet eine Template-Nachricht an eine Testnummer; der Putzplan zeigt Partner und Aufträge des Mandanten (read-only)."
        impact="Tests lösen echte Verbindungsversuche aus (max. 5 pro Minute pro Mandant). Erfolg oder Fehler werden sofort angezeigt; Credentials bleiben serverseitig und erscheinen nicht in der Antwort."
      />

      <Card className="space-y-4">
        <h2 className="text-lg font-medium text-slate-900">Mandant wählen</h2>
        <label className="block text-sm text-slate-600">
          Aktiver Mandant
          <select
            className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            value={accountId}
            onChange={(e) => handleAccountChange(e.target.value)}
          >
            <option value="">— Bitte wählen —</option>
            {activeAccounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.display_name} ({a.contact_email})
              </option>
            ))}
          </select>
        </label>
        {activeAccounts.length === 0 && (
          <p className="text-sm text-slate-500">Keine aktiven Mandanten vorhanden.</p>
        )}
      </Card>

      {accountId && (
        <>
          <Card className="space-y-4">
            <h2 className="text-lg font-medium text-slate-900">Postfach</h2>
            {mailLoading && (
              <p className="text-sm text-slate-500">Lade Postfach-Status…</p>
            )}
            {mailConnection && (
              <>
                <p className="text-sm text-slate-600">
                  {mailConnection.provider === "outlook" ? "Outlook" : "IMAP"} ·{" "}
                  {mailConnection.email_address || "—"}
                </p>
                <p className="text-sm text-slate-500">
                  Status:{" "}
                  <span
                    className={
                      mailConnection.status === "connected"
                        ? "text-green-700"
                        : mailConnection.status === "error"
                          ? "text-red-600"
                          : "text-slate-600"
                    }
                  >
                    {mailConnection.status}
                  </span>
                  {mailConnection.onboarding_completed ? "" : " · Onboarding offen"}
                </p>
                {mailConnection.last_sync_at && (
                  <p className="text-xs text-slate-500">
                    Letzter Sync:{" "}
                    {new Date(mailConnection.last_sync_at).toLocaleString("de-DE")}
                  </p>
                )}
                {mailConnection.last_error && (
                  <p className="text-xs text-red-600">{mailConnection.last_error}</p>
                )}
                <Button
                  variant="secondary"
                  disabled={mailTestMut.isPending}
                  onClick={() => mailTestMut.mutate()}
                >
                  Postfach-Verbindung testen
                </Button>
                {mailResult && (
                  <p
                    role="status"
                    aria-live="polite"
                    className={`text-sm ${mailResult.ok ? "text-green-700" : "text-red-600"}`}
                  >
                    {mailResult.ok ? "OK — " : "Fehler: "}
                    {mailResult.message}
                  </p>
                )}
              </>
            )}
          </Card>

          <AdminWhatsAppDiagnosticsCard
            accountId={accountId}
            whatsappInfo={whatsappInfo}
            loading={waLoading}
          />

          <AdminCleaningDiagnosticsCard accountId={accountId} />
        </>
      )}
    </div>
  );
}
