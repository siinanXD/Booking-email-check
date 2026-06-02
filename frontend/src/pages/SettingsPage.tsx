import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  fetchSettings,
  saveSettings,
  testWhatsApp,
  wipeAllData,
} from "@/api/settings";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: fetchSettings,
  });

  const [whatsappEnabled, setWhatsappEnabled] = useState(false);
  const [accessToken, setAccessToken] = useState("");
  const [phoneNumberId, setPhoneNumberId] = useState("");
  const [defaultRecipients, setDefaultRecipients] = useState("");
  const [testRecipient, setTestRecipient] = useState("");
  const [outlookMailbox, setOutlookMailbox] = useState("");
  const [userPhone, setUserPhone] = useState("");
  const [userWhatsappEnabled, setUserWhatsappEnabled] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [wipeConfirm, setWipeConfirm] = useState("");

  useEffect(() => {
    if (!data) return;
    setWhatsappEnabled(data.whatsapp_enabled);
    setAccessToken("");
    setPhoneNumberId(data.whatsapp_phone_number_id);
    setDefaultRecipients(data.whatsapp_default_recipients);
    setTestRecipient(data.whatsapp_test_recipient);
    setOutlookMailbox(data.outlook_mailbox);
    setUserPhone(data.user_profile.whatsapp_phone_e164 ?? "");
    setUserWhatsappEnabled(data.user_profile.whatsapp_enabled);
  }, [data]);

  const saveMut = useMutation({
    mutationFn: () =>
      saveSettings({
        whatsapp_enabled: whatsappEnabled,
        whatsapp_access_token: accessToken.trim() || undefined,
        whatsapp_phone_number_id: phoneNumberId,
        whatsapp_default_recipients: defaultRecipients,
        whatsapp_test_recipient: testRecipient,
        outlook_mailbox: outlookMailbox,
        user_profile: {
          whatsapp_phone_e164: userPhone.trim() || null,
          whatsapp_enabled: userWhatsappEnabled,
        },
      }),
    onSuccess: () => {
      setSaveMessage("Einstellungen gespeichert.");
      setAccessToken("");
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
    onError: () => setTestMessage("Test-Anfrage fehlgeschlagen."),
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
          WhatsApp-Benachrichtigungen für mich aktiv
        </label>
      </Card>

      <Card className="space-y-4">
        <h3 className="font-medium text-slate-800">WhatsApp (Meta Cloud API)</h3>
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={whatsappEnabled}
            onChange={(e) => setWhatsappEnabled(e.target.checked)}
          />
          WhatsApp-Versand aktiv
        </label>
        <label className="block text-sm text-slate-600">
          Access Token
          {data?.whatsapp_access_token_set && (
            <span className="ml-2 text-xs text-green-700">(hinterlegt)</span>
          )}
          <Input
            className="mt-1"
            type="password"
            value={accessToken}
            onChange={(e) => setAccessToken(e.target.value)}
            placeholder={
              data?.whatsapp_access_token_set
                ? "Leer lassen = unverändert"
                : "Meta Access Token"
            }
          />
        </label>
        <label className="block text-sm text-slate-600">
          Phone Number ID (nur Ziffern, aus Meta API Setup)
          <Input
            className="mt-1"
            value={phoneNumberId}
            onChange={(e) => setPhoneNumberId(e.target.value)}
            placeholder="123456789012345"
          />
        </label>
        <label className="block text-sm text-slate-600">
          Standard-Empfänger (kommagetrennt, E.164)
          <Input
            className="mt-1"
            value={defaultRecipients}
            onChange={(e) => setDefaultRecipients(e.target.value)}
            placeholder="+491701234567"
          />
        </label>
        <label className="block text-sm text-slate-600">
          Test-Empfänger (hello_world)
          <Input
            className="mt-1"
            value={testRecipient}
            onChange={(e) => setTestRecipient(e.target.value)}
            placeholder="+491701234567"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => testMut.mutate()}
            disabled={testMut.isPending}
          >
            WhatsApp-Verbindung testen
          </Button>
        </div>
        {testMessage && (
          <p
            className={`text-sm ${testMessage.startsWith("Test erfolgreich") ? "text-green-700" : "text-red-600"}`}
          >
            {testMessage}
          </p>
        )}
      </Card>

      <Card className="space-y-4">
        <h3 className="font-medium text-slate-800">Erweitert</h3>
        <label className="block text-sm text-slate-600">
          Outlook-Postfach
          <Input
            className="mt-1"
            value={outlookMailbox}
            onChange={(e) => setOutlookMailbox(e.target.value)}
            placeholder="postfach@firma.de"
          />
        </label>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
          Einstellungen speichern
        </Button>
      </div>
      {saveMessage && <p className="text-sm text-slate-700">{saveMessage}</p>}

      <Card className="space-y-3 border-red-200 bg-red-50">
        <h3 className="font-medium text-red-800">Gefahrenzone</h3>
        <p className="text-sm text-red-700">
          Löscht alle E-Mails, Reviews, Metriken und gespeicherten
          Einstellungen. Login-Benutzer bleiben erhalten.
        </p>
        <Input
          value={wipeConfirm}
          onChange={(e) => setWipeConfirm(e.target.value)}
          placeholder='Tippe "ALLE DATEN LOESCHEN" zur Bestätigung'
        />
        <Button
          variant="danger"
          disabled={wipeConfirm !== "ALLE DATEN LOESCHEN" || wipeMut.isPending}
          onClick={() => wipeMut.mutate()}
        >
          Alle Daten löschen
        </Button>
      </Card>
    </div>
  );
}
