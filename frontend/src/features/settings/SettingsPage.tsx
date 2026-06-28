import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Save, Shield } from "lucide-react";
import { useAuthStore } from "@/features/auth/authStore";
import { fetchMailConnection, testMailConnection } from "@/lib/api/mail";
import { fetchSettings, saveSettings, testWhatsApp, wipeAllData } from "@/lib/api/settings";
import { AutoApproveCard } from "@/features/settings/AutoApproveCard";
import { GdprGuestCard } from "@/features/settings/GdprGuestCard";
import { SettingsDangerZone } from "@/features/settings/SettingsDangerZone";
import { SettingsMailCard } from "@/features/settings/SettingsMailCard";
import { SettingsWhatsAppCard } from "@/features/settings/SettingsWhatsAppCard";
import { SettingsWhatsAppRecipientsCard } from "@/features/settings/SettingsWhatsAppRecipientsCard";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";
import { toast } from "@/shared/feedback/toastStore";

function SectionHeader({ title }: { title: string }) {
  return <h3 className="text-sm font-semibold text-slate-800">{title}</h3>;
}

export function SettingsPage() {
  const isPlatformAdmin = useAuthStore((s) => s.isPlatformAdmin());
  const isAccountAdmin = useAuthStore((s) => s.isAccountAdmin());
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
  const [testMessage, setTestMessage] = useState<string | null>(null);

  const { data: mailData } = useQuery({
    queryKey: ["mail-connection"],
    queryFn: fetchMailConnection,
    enabled: !isPlatformAdmin,
  });

  const mailTestMut = useMutation({
    mutationFn: testMailConnection,
    onSuccess: (res) => {
      if (res.success) {
        toast.success(
          `Postfach-Verbindung OK${res.mailbox_count != null ? ` (${res.mailbox_count} Nachrichten)` : ""}.`
        );
      } else {
        toast.error(`Postfach-Test fehlgeschlagen: ${res.message}`);
      }
    },
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
      toast.success("Einstellungen gespeichert.");
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const testMut = useMutation({
    mutationFn: () => testWhatsApp(testRecipient || undefined),
    meta: { skipGlobalError: true },
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
      toast.success(`Alle Daten gelöscht (${total} Dokumente).`);
      void queryClient.invalidateQueries();
    },
  });

  if (isPlatformAdmin) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Einstellungen</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            Als Plattform-Administrator verwaltest du Mandanten über die{" "}
            <Link to="/admin/overview" className="text-indigo-600 hover:underline">
              Admin-Konsole
            </Link>
            .
          </p>
        </div>
        <Card>
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-100 text-indigo-600">
              <Shield size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">Plattform-Administration</p>
              <p className="text-xs text-slate-500">
                Verbindungstests pro Mandant unter Admin → Diagnose.
              </p>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-10 text-slate-500">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-indigo-500" />
        <span className="text-sm">Einstellungen werden geladen…</span>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Einstellungen</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          Werte aus der <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">.env</code> werden
          automatisch vorausgefüllt. Nach dem Speichern gelten die Einträge dauerhaft in der Datenbank.
        </p>
      </div>

      {/* Profile */}
      <Card>
        <div className="space-y-4">
          <SectionHeader title="Mein Profil (Host)" />
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-600">
              Meine WhatsApp-Nummer (E.164, z. B. +491701234567)
            </label>
            <Input
              value={userPhone}
              onChange={(e) => setUserPhone(e.target.value)}
              placeholder="+491701234567"
            />
          </div>
          <label className="flex cursor-pointer items-center gap-2.5">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 accent-indigo-600"
              checked={userWhatsappEnabled}
              onChange={(e) => setUserWhatsappEnabled(e.target.checked)}
            />
            <span className="text-sm text-slate-700">
              WhatsApp-Benachrichtigungen für mich aktiv
            </span>
          </label>
        </div>
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

      {/* Auto-approve */}
      <AutoApproveCard value={data?.auto_approve} />

      {/* Mail connection */}
      <SettingsMailCard
        mailData={mailData}
        testPending={mailTestMut.isPending}
        onTest={() => mailTestMut.mutate()}
      />

      {/* GDPR guests (account-admin only) */}
      {isAccountAdmin && <GdprGuestCard />}

      {/* Save */}
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={() => saveMut.mutate()} loading={saveMut.isPending}>
          <Save size={15} />
          Einstellungen speichern
        </Button>
      </div>

      <SettingsDangerZone
        onWipe={() => wipeMut.mutateAsync()}
        wipePending={wipeMut.isPending}
      />
    </div>
  );
}
