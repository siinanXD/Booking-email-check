import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuthStore } from "@/features/auth/authStore";
import {
  fetchMailConnection,
  testMailConnection,
} from "@/lib/api/mail";
import {
  fetchSettings,
  saveSettings,
  testWhatsApp,
  wipeAllData,
} from "@/lib/api/settings";
import { SettingsDangerZone } from "@/features/settings/SettingsDangerZone";
import { SettingsWhatsAppCard } from "@/features/settings/SettingsWhatsAppCard";
import { SettingsWhatsAppRecipientsCard } from "@/features/settings/SettingsWhatsAppRecipientsCard";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

export function SettingsPage() {
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
    enabled: !isPlatformAdmin,
  });

  const [whatsappEnabled, setWhatsappEnabled] = useState(false);
  const [defaultRecipients, setDefaultRecipients] = useState("");
  const [testRecipient, setTestRecipient] = useState("");
  const [userPhone, setUserPhone] = useState("");
  const [userWhatsappEnabled, setUserWhatsappEnabled] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [wipeConfirm, setWipeConfirm] = useState("");

  const { data: mailData } = useQuery({
    queryKey: ["mail-connection"],
    queryFn: fetchMailConnection,
    enabled: !isPlatformAdmin,
  });

  const mailTestMut = useMutation({
    mutationFn: testMailConnection,
    onSuccess: (res) => {
      setSaveMessage(
        res.success
          ? `Postfach-Verbindung OK${res.mailbox_count != null ? ` (${res.mailbox_count} Nachrichten)` : ""}.`
          : `Postfach-Test fehlgeschlagen: ${res.message}`
      );
    },
    onError: () => setSaveMessage("Postfach-Test fehlgeschlagen."),
  });

  useEffect(() => {
    if (!data) return;
    setWhatsappEnabled(data.whatsapp_enabled);
    setDefaultRecipients(data.whatsapp_default_recipients);
    setTestRecipient(data.whatsapp_test_recipient);
    setUserPhone(data.user_profile.whatsapp_phone_e164 ?? "");
    setUserWhatsappEnabled(data.user_profile.whatsapp_enabled);
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () =>
      saveSettings({
        whatsapp_enabled: whatsappEnabled,
        whatsapp_default_recipients: defaultRecipients,
        whatsapp_test_recipient: testRecipient,
        user_profile: {
          whatsapp_phone_e164: userPhone.trim() || null,
          whatsapp_enabled: userWhatsappEnabled,
        },
      }),
    onSuccess: () => {
      setSaveMessage("Einstellungen gespeichert.");
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: () => setSaveMessage("Speichern fehlgeschlagen."),
  });

  const testMut = useMutation({
    mutationFn: () => testWhatsApp(testRecipient || undefined),
    onSuccess: (res) => {
      setTestMessage(
        res.success
          ? `Test erfolgreich (ID: ${res.provider_message_id ?? "—"})`
          : `Test fehlgeschlagen: ${res.error ?? "Unbekannter Fehler"}`
      );
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { error?: string } } })?.response?.data
          ?.error;
      setTestMessage(
        detail ? `Test fehlgeschlagen: ${detail}` : "Test-Anfrage fehlgeschlagen."
      );
    },
  });

  const wipeMut = useMutation({
    mutationFn: wipeAllData,
    onSuccess: (res) => {
      const total = Object.values(res.deleted).reduce((a, b) => a + b, 0);
      setSaveMessage(`Alle Daten gelöscht (${total} Dokumente).`);
      setWipeConfirm("");
      void queryClient.invalidateQueries();
    },
    onError: () => setSaveMessage("Löschen fehlgeschlagen."),
  });

  if (isPlatformAdmin) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-slate-800">Einstellungen</h2>
          <p className="mt-1 text-sm text-slate-600">
            Als Plattform-Administrator verwaltest du Mandanten über die{" "}
            <Link to="/admin/overview" className="text-indigo-600 hover:underline">
              Admin-Konsole
            </Link>
            . Postfach- und WhatsApp-Verbindungen richten Mandanten selbst ein.
          </p>
        </div>
        <Card className="space-y-2">
          <h3 className="font-medium text-slate-800">Plattform-Administration</h3>
          <p className="text-sm text-slate-600">
            Verbindungstests pro Mandant folgen unter Admin → Diagnose (Phase 2).
          </p>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return <p className="text-slate-500">Einstellungen werden geladen…</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-slate-800">Einstellungen</h2>
        <p className="mt-1 text-sm text-slate-600">
          Werte aus der <code className="text-xs">.env</code> werden automatisch
          vorausgefüllt. Nach dem Speichern gelten die Einträge dauerhaft in der
          Datenbank.
        </p>
      </div>

      <Card className="space-y-4">
        <h3 className="font-medium text-slate-800">Mein Profil (Host)</h3>
        <label className="block text-sm text-slate-600">
          Meine WhatsApp-Nummer (E.164, z. B. +491701234567)
          <Input
            className="mt-1"
            value={userPhone}
            onChange={(e) => setUserPhone(e.target.value)}
            placeholder="+491701234567"
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={userWhatsappEnabled}
            onChange={(e) => setUserWhatsappEnabled(e.target.checked)}
          />
          WhatsApp-Benachrichtigungen für mich aktiv (z. B. „Neue Buchung“)
        </label>
      </Card>

      <SettingsWhatsAppRecipientsCard />

      <SettingsWhatsAppCard
        data={data}
        whatsappEnabled={whatsappEnabled}
        onWhatsappEnabledChange={setWhatsappEnabled}
        defaultRecipients={defaultRecipients}
        onDefaultRecipientsChange={setDefaultRecipients}
        testRecipient={testRecipient}
        onTestRecipientChange={setTestRecipient}
        testPending={testMut.isPending}
        onTest={() => testMut.mutate()}
        testMessage={testMessage}
      />

      <Card className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-medium text-slate-800">Postfach</h3>
          <Link
            to="/onboarding?edit=1"
            className="text-sm text-indigo-600 hover:underline"
          >
            Bearbeiten
          </Link>
        </div>
        {mailData ? (
          <>
            <p className="text-sm text-slate-600">
              {mailData.provider === "outlook" ? "Microsoft Outlook" : "IMAP"} ·{" "}
              {mailData.email_address || "—"}
            </p>
            <p className="text-sm text-slate-500">
              Status:{" "}
              <span
                className={
                  mailData.status === "connected"
                    ? "text-green-700"
                    : mailData.status === "error"
                      ? "text-red-600"
                      : "text-slate-600"
                }
              >
                {mailData.status}
              </span>
              {mailData.last_sync_at && (
                <span className="block text-xs text-slate-500">
                  Letzter Sync:{" "}
                  {new Date(mailData.last_sync_at).toLocaleString("de-DE")}
                </span>
              )}
              {mailData.last_error && (
                <span className="block text-xs text-red-600">
                  {mailData.last_error}
                </span>
              )}
            </p>
            <Button
              variant="secondary"
              onClick={() => mailTestMut.mutate()}
              disabled={mailTestMut.isPending}
            >
              Postfach-Verbindung testen
            </Button>
          </>
        ) : (
          <p className="text-sm text-slate-500">
            Noch kein Postfach verbunden.{" "}
            <Link to="/onboarding?edit=1" className="text-indigo-600 hover:underline">
              Jetzt einrichten
            </Link>
          </p>
        )}
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
          Einstellungen speichern
        </Button>
      </div>
      {saveMessage && <p className="text-sm text-slate-700">{saveMessage}</p>}

      <SettingsDangerZone
        wipeConfirm={wipeConfirm}
        onWipeConfirmChange={setWipeConfirm}
        onWipe={() => wipeMut.mutate()}
        wipePending={wipeMut.isPending}
      />
    </div>
  );
}
